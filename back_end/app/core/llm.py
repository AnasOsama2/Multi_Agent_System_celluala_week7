import json
import time
from typing import Any, Dict, List, Optional
from groq import Groq
from app.config import settings
from app.core.logging import app_logger

class GroqLLMClient:
    def __init__(self):
        self._client: Optional[Groq] = None

    @property
    def client(self) -> Groq:
        if self._client is None:
            api_key = settings.effective_groq_key
            if not api_key:
                raise ValueError("Groq API key is missing. Set groq_key or GROQ_API_KEY in .env")
            self._client = Groq(api_key=api_key)
        return self._client

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        trace_id: Optional[str] = None
    ) -> str:
        model = model or settings.llm_model
        temperature = temperature if temperature is not None else settings.llm_temperature
        max_tokens = max_tokens or settings.llm_max_tokens

        response_format = {"type": "json_object"} if json_mode else None

        start_time = time.time()
        for attempt in range(3):
            try:
                completion = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format
                )
                
                content = completion.choices[0].message.content or ""
                usage = completion.usage
                prompt_tokens = usage.prompt_tokens if usage else 0
                completion_tokens = usage.completion_tokens if usage else 0

                app_logger.log_llm_response(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    answer_snippet=content,
                    trace_id=trace_id
                )
                return content
            except Exception as e:
                app_logger.log_state(
                    event=f"Groq API error on attempt {attempt+1}: {str(e)}",
                    step="llm_generation",
                    level="warning",
                    trace_id=trace_id
                )
                if attempt == 2:
                    raise e
                time.sleep(1.0 * (attempt + 1))
        return ""

    def generate_json(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.0,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        raw = self.generate(
            messages=messages,
            model=model,
            temperature=temperature,
            json_mode=True,
            trace_id=trace_id
        )
        try:
            return json.loads(raw)
        except Exception:
            # Fallback cleanup in case of markdown fences
            clean = raw.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            return json.loads(clean.strip())


llm_client = GroqLLMClient()
