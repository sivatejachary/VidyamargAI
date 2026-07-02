import logging
import time
import httpx
from typing import Dict, Any, List, Optional

logger = logging.getLogger("packages.model-client.client")

class AppAIClient:
    """
    Unified client abstraction for LLM completions.
    Primary provider: Groq API
    """
    def __init__(self, api_key: str, default_model: str = "llama-3.1-70b-versatile", fallback_model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key
        self.default_model = default_model
        self.fallback_model = fallback_model
        self.completions_url = "https://api.groq.com/openai/v1/chat/completions"

    async def get_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        model_override: Optional[str] = None
    ) -> str:
        """
        Sends complete prompt payload to Groq API. Falls back to a smaller model on failure.
        """
        if not self.api_key or str(self.api_key).strip().lower() in ["", "none", "null"]:
            logger.error("Groq API key is missing or unconfigured.")
            return ""

        model = model_override or self.default_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                t0 = time.perf_counter()
                res = await client.post(self.completions_url, headers=headers, json=payload)
                latency_ms = (time.perf_counter() - t0) * 1000
                
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # Track telemetry metrics
                    usage = data.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    logger.info(
                        f"Groq completion successful. Model: {model}. "
                        f"Tokens: In={prompt_tokens}, Out={completion_tokens}. Latency: {latency_ms:.2f}ms"
                    )
                    return content
                else:
                    logger.warning(
                        f"Groq API returned error status {res.status_code}. "
                        f"Details: {res.text[:200]}. Attempting fallback to {self.fallback_model}..."
                    )
            except Exception as e:
                logger.error(f"Groq client connection failed on {model} execution: {e}. Attempting fallback...")

            # Fallback block
            if model != self.fallback_model:
                payload["model"] = self.fallback_model
                try:
                    t0 = time.perf_counter()
                    res = await client.post(self.completions_url, headers=headers, json=payload)
                    latency_ms = (time.perf_counter() - t0) * 1000
                    
                    if res.status_code == 200:
                        data = res.json()
                        content = data["choices"][0]["message"]["content"]
                        usage = data.get("usage", {})
                        logger.info(
                            f"Fallback Groq completion successful. Model: {self.fallback_model}. "
                            f"Tokens: In={usage.get('prompt_tokens', 0)}, Out={usage.get('completion_tokens', 0)}. "
                            f"Latency: {latency_ms:.2f}ms"
                        )
                        return content
                    else:
                        logger.error(f"Fallback Groq API failed. Status: {res.status_code}. Response: {res.text[:200]}")
                except Exception as ex:
                    logger.critical(f"Critical: Fallback Groq client invocation failed: {ex}")

        return ""
