import json
import logging
import time
from typing import Type, TypeVar, List, Dict, Any

from pydantic import BaseModel
from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL, TIMEOUT

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Ordered list of fallback models to try when primary is unavailable (503).
# These are tested against the current API key's quota.
MODEL_FALLBACK_CHAIN: List[str] = [
    GEMINI_MODEL,
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-3-flash-preview",
]


class LLMService:
    """
    A service class to interact with the Google Gemini API with structured JSON
    output capabilities. Automatically falls back to alternate models on 503.
    """

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.primary_model = model or GEMINI_MODEL

        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. Real LLM calls will fail.")

        try:
            if self.api_key:
                self.client = genai.Client(api_key=self.api_key)
            else:
                self.client = genai.Client()
        except Exception as e:
            logger.error(f"Failed to initialize GenAI client: {e}")
            self.client = None

    def _is_server_overload(self, e: Exception) -> bool:
        """Returns True if the error is a temporary 503 server overload."""
        return "503" in str(e) or "UNAVAILABLE" in str(e)

    def _is_quota_error(self, e: Exception) -> bool:
        """Returns True if the error is a 429 quota exhaustion."""
        return "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)

    def get_structured_completion(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        temperature: float = 0.2,
    ) -> T:
        """
        Sends messages to the Gemini API and parses the response into response_model.

        Tries each model in MODEL_FALLBACK_CHAIN on 503 UNAVAILABLE.
        Uses exponential backoff on retries within each model.
        """
        if not self.client:
            raise ValueError(
                "GenAI client is not initialized due to missing API key."
            )

        # Build the prompt from message list
        system_instruction = ""
        user_parts: List[str] = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = content
            else:
                user_parts.append(content)
        prompt = "\n\n".join(user_parts)

        # Deduplicate fallback chain while preserving order
        chain = list(dict.fromkeys([self.primary_model] + MODEL_FALLBACK_CHAIN))

        last_error: Exception = RuntimeError("No models available to try.")

        for model in chain:
            max_retries = 2
            backoff = 5.0  # start at 5 s for server overload errors

            for attempt in range(max_retries):
                try:
                    logger.info(
                        f"Calling Gemini model '{model}' (attempt {attempt + 1})..."
                    )
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction or None,
                            response_mime_type="application/json",
                            response_schema=response_model,
                            temperature=temperature,
                        ),
                    )

                    response_text = response.text
                    if not response_text:
                        raise ValueError("Received empty response from Gemini API.")

                    try:
                        return response_model.model_validate_json(response_text)
                    except AttributeError:
                        return response_model.parse_raw(response_text)

                except Exception as e:
                    last_error = e
                    err_str = str(e)[:120]

                    if self._is_quota_error(e):
                        # 429 quota: skip this model entirely, don't retry
                        logger.warning(
                            f"Model '{model}' quota exhausted (429). Skipping."
                        )
                        break

                    if self._is_server_overload(e):
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"Model '{model}' overloaded (503), attempt "
                                f"{attempt + 1}/{max_retries}. "
                                f"Retrying in {backoff:.0f}s..."
                            )
                            time.sleep(backoff)
                            backoff *= 2
                        else:
                            logger.warning(
                                f"Model '{model}' still unavailable after "
                                f"{max_retries} attempts. Trying next model."
                            )
                        continue

                    # Any other error (4xx, parse error): propagate immediately
                    logger.error(
                        f"Non-retryable error from model '{model}': {err_str}"
                    )
                    raise e

        logger.error(f"All models in fallback chain exhausted. Last error: {last_error}")
        raise last_error
