from dataclasses import dataclass
from typing import Any, Optional, Iterable, Union, List
import os
import time
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


def build_llm() -> BaseLLM:
    """Factory for LLM instance."""
    backend = os.getenv("LLM_BACKEND", "gemini")
    if backend == "gemini":
        return GeminiLLM()
    # Extendable: support OpenAI, Claude, Ollama, etc.
    return GeminiLLM()


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