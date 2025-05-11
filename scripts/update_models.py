#!/usr/bin/env python3
import requests
import json

# The list of models to add
ai_model_names = [
    "claude-3.5-haiku",
    "claude-3.5-sonnet",
    "claude-3.7-sonnet",
    "claude-3.7-sonnet-max",
    "cursor-small",
    "deepseek-r1",
    "deepseek-v3.1",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-2.0-flash",
    "gemini-2.0-pro-exp",
    "gemini-2.5-flash-preview-04-17",
    "gemini-2.5-pro-exp-03-25",
    "gemini-2.5-pro-max",
    "gpt-4",
    "gpt-4.1",
    "gpt-4o",
    "grok-3-beta",
    "grok-3-mini-beta",
    "o1",
    "o1-mini",
    "o1-preview",
    "o3",
    "o3-mini",
    "o4-mini"
]

def update_models():
    url = "http://localhost:8000/api/v1/ai/config/supported-providers/update-models?test_mode=true"
    
    # Add test_mode=true query parameter to use test user ID
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer test_token"
    }
    
    payload = {"ai_model_names": ai_model_names}
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        # Check if request was successful
        if response.status_code == 200:
            print("Models updated successfully!")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Exception occurred: {e}")

if __name__ == "__main__":
    update_models() 