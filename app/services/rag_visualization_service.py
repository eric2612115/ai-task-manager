import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.models.conversation_models import RagReference
from app.services.conversation_service import conversation_service
from app.core.utils import serialize_mongodb_doc

logger = logging.getLogger(__name__)

class RagVisualizationService:
    """RAG结果可视化服务"""
    
    async def prepare_visualization_data(self, references: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        准备RAG检索结果的可视化数据
        
        Args:
            references: RAG检索引用列表
            
        Returns:
            处理后的可视化数据
        """
        try:
            if not references:
                return {
                    "sources": [],
                    "summary": {
                        "total_sources": 0,
                        "code_sources": 0,
                        "doc_sources": 0,
                        "avg_score": 0
                    },
                    "file_types": {}
                }
            
            # 基础数据统计
            total_sources = len(references)
            code_sources = sum(1 for ref in references if ref.get("type") == "code")
            doc_sources = sum(1 for ref in references if ref.get("type") == "doc")
            
            # 计算平均相关性得分
            if total_sources > 0:
                avg_score = sum(ref.get("score", 0) for ref in references) / total_sources
            else:
                avg_score = 0
            
            # 文件类型统计
            file_types = {}
            for ref in references:
                language = ref.get("language")
                if language:
                    if language not in file_types:
                        file_types[language] = 0
                    file_types[language] += 1
                elif ref.get("type") == "doc":
                    if "documentation" not in file_types:
                        file_types["documentation"] = 0
                    file_types["documentation"] += 1
            
            # 处理引用源，添加高亮和摘要信息
            processed_sources = []
            for idx, ref in enumerate(references):
                source = {
                    "id": idx,
                    "file_id": ref.get("file_id"),
                    "file_path": ref.get("file_path"),
                    "file_name": ref.get("file_name"),
                    "content": ref.get("content"),
                    "score": ref.get("score", 0),
                    "language": ref.get("language"),
                    "type": ref.get("type"),
                    "metadata": ref.get("metadata", {}),
                }
                
                # 尝试提取和高亮相关部分
                if len(source["content"]) > 200:
                    source["preview"] = source["content"][:200] + "..."
                else:
                    source["preview"] = source["content"]
                
                processed_sources.append(source)
            
            # 按相关性得分排序
            processed_sources.sort(key=lambda x: x["score"], reverse=True)
            
            return {
                "sources": processed_sources,
                "summary": {
                    "total_sources": total_sources,
                    "code_sources": code_sources,
                    "doc_sources": doc_sources,
                    "avg_score": round(avg_score, 4)
                },
                "file_types": file_types
            }
        
        except Exception as e:
            logger.error(f"Error preparing RAG visualization data: {str(e)}")
            raise
    
    async def attach_visualization_to_message(self, message_id: str, visualization_data: Dict[str, Any]) -> bool:
        """
        将可视化数据附加到消息的元数据中
        
        Args:
            message_id: 消息ID
            visualization_data: 可视化数据
            
        Returns:
            是否成功附加
        """
        try:
            # 更新消息元数据，添加可视化数据
            message = await conversation_service.get_message(message_id)
            if not message:
                logger.error(f"Message {message_id} not found")
                return False
            
            # 获取现有元数据
            metadata = message.get("metadata", {})
            
            # 添加可视化数据
            metadata["rag_visualization"] = visualization_data
            metadata["visualization_generated_at"] = datetime.utcnow().isoformat()
            
            # 更新消息
            await conversation_service.update_message(
                message_id=message_id,
                update_data={"metadata": metadata}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error attaching visualization data to message {message_id}: {str(e)}")
            return False
    
    async def get_message_visualization(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        获取消息的RAG可视化数据
        
        Args:
            message_id: 消息ID
            
        Returns:
            RAG可视化数据，如果不存在则返回None
        """
        try:
            message = await conversation_service.get_message(message_id)
            if not message:
                logger.error(f"Message {message_id} not found")
                return None
            
            # 从元数据获取可视化数据
            metadata = message.get("metadata", {})
            visualization = metadata.get("rag_visualization")
            
            if not visualization:
                # 如果没有现成的可视化数据，但有引用源，则生成可视化数据
                references = message.get("references", [])
                if references:
                    visualization = await self.prepare_visualization_data(references)
                    
                    # 保存生成的可视化数据
                    await self.attach_visualization_to_message(message_id, visualization)
            
            return visualization
            
        except Exception as e:
            logger.error(f"Error getting visualization data for message {message_id}: {str(e)}")
            return None
    
    async def highlight_context_matches(self, query: str, context: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        高亮查询与内容的匹配部分
        
        Args:
            query: 用户查询
            context: 检索到的内容
            language: 代码语言(如果是代码)
            
        Returns:
            包含高亮信息的数据
        """
        try:
            # 简单分词处理
            query_terms = [term.lower() for term in query.split() if len(term) > 2]
            
            # 找出相关行
            lines = context.split("\n")
            matches = []
            
            for i, line in enumerate(lines):
                line_lower = line.lower()
                matched_terms = [term for term in query_terms if term in line_lower]
                
                if matched_terms:
                    matches.append({
                        "line": i + 1,  # 1-based line number
                        "content": line,
                        "matched_terms": matched_terms
                    })
            
            # 如果没有精确匹配的行，返回整个上下文
            if not matches:
                return {
                    "matched_lines": [],
                    "context": context,
                    "has_highlights": False
                }
            
            # 确保返回足够的上下文
            context_lines = []
            for match in matches:
                line_num = match["line"]
                
                # 获取匹配行前后的上下文
                start_line = max(1, line_num - 2)
                end_line = min(len(lines), line_num + 2)
                
                for i in range(start_line, end_line + 1):
                    context_lines.append({
                        "line": i,
                        "content": lines[i - 1],
                        "is_match": i == line_num
                    })
            
            # 去除重复行
            unique_context_lines = []
            seen_lines = set()
            
            for line in context_lines:
                if line["line"] not in seen_lines:
                    unique_context_lines.append(line)
                    seen_lines.add(line["line"])
            
            # 按行号排序
            unique_context_lines.sort(key=lambda x: x["line"])
            
            return {
                "matched_lines": matches,
                "context_lines": unique_context_lines,
                "has_highlights": True,
                "language": language
            }
            
        except Exception as e:
            logger.error(f"Error highlighting context matches: {str(e)}")
            return {
                "context": context,
                "has_highlights": False
            }

# 全局RAG可视化服务实例
rag_visualization_service = RagVisualizationService() 