from dataclasses import dataclass
from typing import Any, Optional, Iterable, Union, List
import os
import time
import json
import requests
import dotenv

dotenv.load_dotenv()


@dataclass
class LLMResponse:
    text: str
    raw: Any = None


class BaseEmbeddings:
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

class BaseLLM:
    def generate(
        self,
        prompt: Union[str, Iterable[Any]],
        *,
        system_instruction: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.3,
        max_retries: int = 3,
        **kwargs,
    ) -> LLMResponse:
        raise NotImplementedError


class GeminiLLM(BaseLLM):
    """
    Thin wrapper for the official `google-genai` SDK.
    Supports structured responses and retry logic.
    """

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        from google import genai
        self._genai = genai
        self._client = genai.Client(api_key=api_key or os.getenv("GEMINI_API_KEY"))
        self._model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

    def generate(
        self,
        prompt: Union[str, Iterable[Any]],
        *,
        system_instruction: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.3,
        max_retries: int = 3,
        **kwargs,
    ) -> LLMResponse:
        generation_config = {"temperature": temperature}
        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        for attempt in range(max_retries):
            try:
                # Prepare the contents - if system_instruction is provided, include it
                contents = prompt
                if system_instruction:
                    # Prepend system instruction to the prompt
                    if isinstance(prompt, str):
                        contents = f"System: {system_instruction}\n\nUser: {prompt}"
                    else:
                        # For more complex content structures, we'll handle it simply for now
                        contents = prompt
                
                resp = self._client.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=generation_config,
                    **kwargs,
                )
                text = getattr(resp, "text", "") or ""
                return LLMResponse(text=text, raw=resp)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.8 * (2 ** attempt))


class OllamaLLM(BaseLLM):
    """
    Ollama local LLM wrapper for local inference.
    """

    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None):
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        # Use provided URL, environment variable, or auto-discover
        if base_url:
            self.base_url = base_url
        elif os.getenv("OLLAMA_BASE_URL"):
            self.base_url = os.getenv("OLLAMA_BASE_URL")
        else:
            self.base_url = self._find_ollama_url()
    
    def _is_docker_environment(self) -> bool:
        """Check if we're running in a Docker/containerized environment."""
        # Check for common Docker environment indicators
        return (
            os.path.exists("/.dockerenv") or  # Standard Docker indicator
            os.environ.get("DOCKER_CONTAINER") == "true" or  # Custom indicator
            "microsoft" in os.uname().release.lower()  # WSL environment
        )
    
    def _find_ollama_url(self) -> str:
        """Try to find the correct Ollama URL by testing different possibilities."""
        # Since both app and Docker are in WSL, try localhost first
        possible_urls = [
            "http://localhost:11434",  # Docker port mapping in WSL
            "http://127.0.0.1:11434",  # Explicit localhost
        ]
        
        for url in possible_urls:
            try:
                response = requests.get(f"{url}/api/version", timeout=5)
                if response.status_code == 200:
                    print(f"Found Ollama at: {url}")
                    return url
            except Exception as e:
                print(f"Failed to connect to {url}: {str(e)[:100]}...")
                continue
        
        print("Warning: Could not connect to Ollama service, using default URL")
        return "http://localhost:11434"
        
    def generate(
        self,
        prompt: Union[str, Iterable[Any]],
        *,
        system_instruction: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.3,
        max_retries: int = 3,
        **kwargs,
    ) -> LLMResponse:
        # Prepare the prompt content
        if isinstance(prompt, str):
            content = prompt
        else:
            content = str(prompt)
        
        # Add system instruction if provided
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": content})
        
        # Prepare request payload
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        # Add JSON mode instruction if requested
        if json_mode:
            payload["format"] = "json"
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=60
                )
                response.raise_for_status()
                
                result = response.json()
                text = result.get("message", {}).get("content", "")
                
                return LLMResponse(text=text, raw=result)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.8 * (2 ** attempt))


class Rev21LLM(BaseLLM):
    """
    Rev21 API LLM wrapper for fallback functionality.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("REV21_API_KEY")
        self.base_url = "https://ai-tools.rev21labs.com/api/v1/ai/prompt"
        
        if not self.api_key:
            raise ValueError("REV21_API_KEY is required")

    def generate(
        self,
        prompt: Union[str, Iterable[Any]],
        *,
        system_instruction: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.3,
        max_retries: int = 3,
        **kwargs,
    ) -> LLMResponse:
        # Prepare the prompt content
        if isinstance(prompt, str):
            content = prompt
        else:
            content = str(prompt)
        
        # Add system instruction if provided
        if system_instruction:
            content = f"System: {system_instruction}\n\nUser: {content}"
        
        # Prepare expected output format for JSON mode
        expected_output = {}
        if json_mode:
            # For orchestrator and structured responses, define the expected format
            if "action" in content.lower() or "orchestrator" in content.lower():
                expected_output = {
                    "action": "action name like PLAN or EXECUTE",
                    "reason": "brief explanation"
                }
            else:
                expected_output = {"response": "structured JSON response"}
            content += "\n\nRespond with valid JSON only."
        
        payload = {
            "prompt": content,
            "content": content,
            "expected_output": expected_output
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Rev21 API returns structured responses differently based on expected_output
                if json_mode or expected_output:
                    # For structured responses, Rev21 returns fields directly
                    # Convert to JSON string format that our agents expect
                    text = json.dumps(result)
                else:
                    # For simple responses, look for common response fields
                    text = result.get("answer", result.get("content", ""))
                    if not text:
                        # If no standard fields, just use the first value
                        text = str(next(iter(result.values()), ""))
                
                return LLMResponse(text=text, raw=result)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.8 * (2 ** attempt))


class FallbackLLM(BaseLLM):
    """
    LLM wrapper that can use any primary and fallback LLM.
    """
    
    def __init__(self, primary: BaseLLM, fallback: BaseLLM):
        self.primary_llm = primary
        self.fallback_llm = fallback
    
    def generate(
        self,
        prompt: Union[str, Iterable[Any]],
        *,
        system_instruction: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.3,
        max_retries: int = 3,
        **kwargs,
    ) -> LLMResponse:
        # Try primary LLM first
        try:
            return self.primary_llm.generate(
                prompt,
                system_instruction=system_instruction,
                json_mode=json_mode,
                temperature=temperature,
                max_retries=max_retries,
                **kwargs
            )
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if it's a resource exhaustion error or any error if we want to always fallback
            print(f"Primary LLM ({type(self.primary_llm).__name__}) failed: {e}")
            print(f"Trying fallback LLM ({type(self.fallback_llm).__name__})...")
            
            try:
                return self.fallback_llm.generate(
                    prompt,
                    system_instruction=system_instruction,
                    json_mode=json_mode,
                    temperature=temperature,
                    max_retries=max_retries,
                    **kwargs
                )
            except Exception as fallback_error:
                print(f"Fallback LLM also failed: {fallback_error}")
                
                # If both APIs fail with rate limiting, provide a simple fallback
                if ("429" in str(e) or "rate" in str(e).lower() or "quota" in str(e).lower()) and \
                   ("429" in str(fallback_error) or "rate" in str(fallback_error).lower() or "quota" in str(fallback_error).lower()):
                    print("Both APIs are rate limited. Using simple fallback logic...")
                    return self._simple_fallback_response(prompt, system_instruction, json_mode)
                
                raise e  # Raise the original error


    def _simple_fallback_response(self, prompt: str, system_instruction: str = None, json_mode: bool = False) -> LLMResponse:
        """Provide a simple fallback response when both APIs are exhausted"""
        
        # Simple heuristics for common orchestrator decisions
        prompt_lower = str(prompt).lower()
        
        if "what action should be taken next" in prompt_lower:
            # This is an orchestrator prompt
            if "tools available: no" in prompt_lower or "tools available: missing" in prompt_lower:
                response = "INSPECT_TOOLS\nNeed to examine available tools first."
            elif "plan exists: no" in prompt_lower:
                response = "PLAN\nNeed to create a plan to answer the question."
            elif "sql query: no" in prompt_lower and "plan exists: yes" in prompt_lower:
                response = "EXECUTE\nNeed to execute the SQL query to get data."
            elif "has results: yes" in prompt_lower and "has insights: no" in prompt_lower:
                response = "SUMMARIZE\nNeed to generate insights from the results."
            elif "pdf requested: yes" in prompt_lower and "has insights: yes" in prompt_lower:
                response = "GENERATE_PDF\nNeed to create the requested PDF report."
            else:
                response = "DONE\nTask appears to be complete."
                
        elif json_mode and ("plan" in prompt_lower or "sql" in prompt_lower):
            # This is a planner prompt
            response = '''{"plan": ["Analyze the question", "Generate appropriate SQL query", "Execute and return results"], "sql_candidate": "SELECT * FROM actor LIMIT 10;", "rationale": "Simple fallback query due to API limitations"}'''
            
        else:
            # Generic fallback
            response = "I apologize, but I'm currently unable to process this request due to API limitations. Please try again later."
        
        if json_mode and not response.startswith('{'):
            # Wrap in JSON if needed
            response = f'{{"response": "{response}"}}'
            
        return LLMResponse(text=response, raw={"fallback": True})


def build_llm() -> BaseLLM:
    """Factory for LLM instance - prioritizes Rev21 by default, falls back to local Ollama."""
    backend = os.getenv("LLM_BACKEND", "rev21")
    fallback_enabled = os.getenv("LLM_FALLBACK_ENABLED", "true").lower() == "true"
    
    # Check availability of different LLM services
    rev21_available = bool(os.getenv("REV21_API_KEY"))
    gemini_available = bool(os.getenv("GEMINI_API_KEY"))
    
    # Check if .env file exists and has any API keys
    env_file_exists = os.path.exists(".env")
    has_api_keys = rev21_available or gemini_available
    
    # If no .env file or no API keys, use local Ollama as primary
    if not env_file_exists or not has_api_keys:
        print("No API keys found, using local Ollama LLM")
        return OllamaLLM()
    
    if backend == "rev21" and rev21_available:
        primary_llm = Rev21LLM()
        if fallback_enabled:
            if gemini_available:
                fallback_llm = GeminiLLM()
                return FallbackLLM(primary=primary_llm, fallback=fallback_llm)
            else:
                # Use Ollama as fallback if Gemini not available
                fallback_llm = OllamaLLM()
                return FallbackLLM(primary=primary_llm, fallback=fallback_llm)
        return primary_llm
    elif backend == "gemini" and gemini_available:
        primary_llm = GeminiLLM()
        if fallback_enabled:
            if rev21_available:
                fallback_llm = Rev21LLM()
                return FallbackLLM(primary=primary_llm, fallback=fallback_llm)
            else:
                # Use Ollama as fallback if Rev21 not available
                fallback_llm = OllamaLLM()
                return FallbackLLM(primary=primary_llm, fallback=fallback_llm)
        return primary_llm
    elif backend == "ollama":
        return OllamaLLM()
    else:
        # Auto-select based on availability, prefer Rev21
        if rev21_available:
            primary_llm = Rev21LLM()
            if fallback_enabled:
                fallback_llm = GeminiLLM() if gemini_available else OllamaLLM()
                return FallbackLLM(primary=primary_llm, fallback=fallback_llm)
            return primary_llm
        elif gemini_available:
            primary_llm = GeminiLLM()
            if fallback_enabled:
                fallback_llm = OllamaLLM()
                return FallbackLLM(primary=primary_llm, fallback=fallback_llm)
            return primary_llm
        else:
            # Final fallback to local Ollama
            print("No API keys available, using local Ollama LLM")
            return OllamaLLM()


class GeminiEmbeddings(BaseEmbeddings):
    """
    Thin wrapper for the official `google-genai` SDK embeddings.
    """

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        from google import genai
        self._genai = genai
        self._client = genai.Client(api_key=api_key or os.getenv("GEMINI_API_KEY"))
        self._model = model or os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-2.0-embedding-exp")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        resp = self._client.models.embed(
            model=self._model,
            inputs=texts,
        )
        return [embedding.embedding_vector for embedding in resp.embeddings]
    
def build_embedder() -> BaseEmbeddings:
    """Factory for Embeddings instance."""
    backend = os.getenv("EMBEDDING_BACKEND", "gemini")
    if backend == "gemini":
        return GeminiEmbeddings()
    # Extendable: support OpenAI, etc.
    return GeminiEmbeddings()

def get_embedder() -> BaseEmbeddings:
    """Get a singleton Embeddings instance."""
    if not hasattr(get_embedder, "_instance"):
        get_embedder._instance = build_embedder()
    return get_embedder._instance

def get_llm() -> BaseLLM:
    """Get a singleton LLM instance."""
    if not hasattr(get_llm, "_instance"):
        get_llm._instance = build_llm()
    return get_llm._instance