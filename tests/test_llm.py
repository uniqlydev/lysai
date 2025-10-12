# tests/test_llm.py
import os
from core.llm_client import GeminiLLM

def main():
    print("=== AutoAnalyst LLM Test ===")
    
    # Check if API key is set
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in environment variables.")
        print("Please create a .env file with your Gemini API key:")
        print("GEMINI_API_KEY=your_actual_api_key_here")
        return
    
    # Try different model names that are more likely to work
    models_to_try = ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash-latest", "gemini-pro"]
    
    llm = None
    working_model = None
    
    for model in models_to_try:
        try:
            print(f"Trying model: {model}")
            llm = GeminiLLM(model=model)
            # Test with a simple prompt to see if the model works
            test_response = llm.generate("Hi")
            working_model = model
            print(f"✅ Successfully connected to model: {model}\n")
            break
        except Exception as e:
            print(f"❌ Model {model} failed: {str(e)[:100]}...")
            continue
    
    if not working_model:
        print("❌ Could not connect to any Gemini model. Please check your API key and try again.")
        return
        
    print(f"Using model: {working_model}")
    print(f"API key configured: {'✓' if api_key else '✗'}\n")

    # Use default prompt for automated testing
    prompt = "Hello! Can you explain what you are in one sentence?"
    print(f"Test prompt: {prompt}")
    print("Generating response...\n")

    try:
        response = llm.generate(prompt)
        print("✅ Response:")
        print("-" * 40)
        print(response.text)
        print("-" * 40)
    except Exception as e:
        print(f"❌ Error while generating content: {e}")
        if "404" in str(e):
            print("Hint: Check if the model name is correct. Try 'gemini-1.5-flash' or 'gemini-1.5-pro'")

if __name__ == "__main__":
    main()