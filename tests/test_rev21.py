#!/usr/bin/env python3
"""
Test script for Rev21 API
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_rev21_api():
    api_key = os.getenv("REV21_API_KEY")
    if not api_key:
        print("❌ REV21_API_KEY not found in environment")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    url = "https://ai-tools.rev21labs.com/api/v1/ai/prompt"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    
    payload = {
        "prompt": "You are a helpful assistant",
        "content": "What is the capital of France?",
        "expected_output": {
            "answer": "the capital city name"
        }
    }
    
    try:
        print("🔄 Testing Rev21 API...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Response: {result}")
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_orchestrator_prompt():
    """Test the specific prompt format used by the orchestrator"""
    api_key = os.getenv("REV21_API_KEY")
    if not api_key:
        print("❌ REV21_API_KEY not found")
        return False
    
    url = "https://ai-tools.rev21labs.com/api/v1/ai/prompt"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    
    payload = {
        "prompt": "You are an intelligent orchestrator for a data analysis agent.",
        "content": """Question: What are the top 3 actors?
PDF Requested: No
Current Step: 1/10
Tools Available: Yes (2 tools)
Plan Exists: No
SQL Query: No
Has Results: No
Has Insights: No
Has Error: No

AVAILABLE ACTIONS:
- INSPECT_TOOLS: Examine available database tools/tables
- PLAN: Create a step-by-step plan
- EXECUTE: Execute SQL query
- SUMMARIZE: Create a summary
- DONE: Task is complete

What action should be taken next? Respond with just the action name and a brief reason.""",
        "expected_output": {
            "action": "action name like PLAN or EXECUTE",
            "reason": "brief explanation"
        }
    }
    
    try:
        print("🔄 Testing orchestrator prompt...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Response: {result}")
            
            # Try to extract action
            print(f"Full response: {json.dumps(result, indent=2)}")
            
            # Check different possible response formats
            content = result.get("content", "")
            action_field = result.get("action", "")
            reason_field = result.get("reason", "")
            
            print(f"Content field: '{content}'")
            print(f"Action field: '{action_field}'")
            print(f"Reason field: '{reason_field}'")
            
            # Try to extract from content first
            lines = content.split('\n') if content else []
            action = lines[0].strip().upper() if lines else ""
            
            # If no action in content, try direct action field
            if not action and action_field:
                action = action_field.strip().upper()
                
            print(f"Extracted action: '{action}'")
            
            valid_actions = {"INSPECT_TOOLS", "PLAN", "EXECUTE", "REFLECT", "SUMMARIZE", "GENERATE_PDF", "DONE"}
            if action in valid_actions:
                print(f"✅ Valid action: {action}")
            else:
                print(f"❌ Invalid action: {action}")
                # Try to find valid action in full text
                full_text = content.upper()
                for valid_action in valid_actions:
                    if valid_action in full_text:
                        print(f"✅ Found valid action in text: {valid_action}")
                        break
                        
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    print("=== Testing Rev21 API ===")
    test_rev21_api()
    print("\n=== Testing Orchestrator Prompt ===")
    test_orchestrator_prompt()