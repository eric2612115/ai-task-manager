# RAG系统环境变量示例

在您的`.env`文件中添加以下配置：

```
# ChromaDB 配置
CHROMA_PERSIST_DIR="./chroma_db"
CHROMA_COLLECTION_CODE="code_embeddings"
CHROMA_COLLECTION_DOCS="doc_embeddings"

# 模型配置
CODEBERT_MODEL="microsoft/codebert-base"
SENTENCE_TRANSFORMER_MODEL="all-MiniLM-L6-v2"

# LLM 配置
LLM_PROVIDER="openai"  # openai, anthropic, google
OPENAI_API_KEY="your-openai-api-key"
ANTHROPIC_API_KEY="your-anthropic-api-key"
GOOGLE_API_KEY="your-google-api-key"
```

请根据您要使用的LLM提供商填写相应的API密钥。 