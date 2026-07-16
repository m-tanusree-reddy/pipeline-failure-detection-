"""
LLM Service — Gemini API with Dynamic Model Discovery

Automatically discovers available text-generation models at startup,
ranks them (Flash first, then Pro), and tries them in order on each
request. Handles transient 503 errors with backoff and skips quota/
fatal errors immediately.
"""
import logging
import time
from typing import Type, TypeVar, List, Dict, Any

from pydantic import BaseModel
from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# ── Model Filtering ───────────────────────────────────────────────
# Model name substrings that identify non-text-generation models.
# These are excluded from the discovered candidate list.
_EXCLUDE_KEYWORDS: List[str] = [
    "embedding", "imagen", "veo", "tts", "audio", "live",
    "translate", "robotics", "research", "computer-use",
    "aqa", "lyria", "antigravity", "nano", "image",
]

# Ranking preference: index 0 = highest priority.
# Flash models are preferred for structured output (faster, cheaper).
_RANK_KEYWORDS: List[str] = ["flash", "pro"]


def _model_score(name: str) -> int:
    """Lower = higher priority. flash=0, pro=1, other=2."""
    for i, kw in enumerate(_RANK_KEYWORDS):
        if kw in name.lower():
            return i
    return len(_RANK_KEYWORDS)


def _is_candidate(model_obj: Any) -> bool:
    """
    Returns True if the model object represents a usable text-generation
    model that supports generateContent.
    """
    name: str = model_obj.name.replace("models/", "")

    # Must be a Gemini model
    if not name.startswith("gemini"):
        return False

    # Exclude specialised non-text models
    if any(kw in name.lower() for kw in _EXCLUDE_KEYWORDS):
        return False

    # If the SDK exposes supported_generation_methods, respect it
    methods = getattr(model_obj, "supported_generation_methods", None) or []
    if methods and "generateContent" not in methods:
        return False

    return True


# ── LLMService ────────────────────────────────────────────────────
class LLMService:
    """
    Wraps the Google Gemini API with:
      • Dynamic model discovery at startup
      • Flash-first ranking
      • Per-model retry with exponential backoff on 503
      • Immediate skip on 429 quota or fatal 4xx errors
    """

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.preferred_model: str = model or GEMINI_MODEL

        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set. LLM calls will fail.")

        self.client: genai.Client | None = None
        try:
            self.client = genai.Client(api_key=self.api_key) if self.api_key else genai.Client()
        except Exception as e:
            logger.error(f"Failed to initialise GenAI client: {e}")

        # Discover and rank models once at startup
        self._model_chain: List[str] = self._discover_models()

    # ── Model Discovery ───────────────────────────────────────────

    def _discover_models(self) -> List[str]:
        """
        Calls client.models.list(), filters to compatible text-generation
        models, then sorts them: preferred model first, then Flash > Pro.
        """
        if not self.client:
            logger.warning("Client not initialised; skipping model discovery.")
            return [self.preferred_model] if self.preferred_model else []

        try:
            raw_models = list(self.client.models.list())
        except Exception as e:
            logger.warning(f"Model discovery failed ({e}). Using preferred model only.")
            return [self.preferred_model] if self.preferred_model else []

        candidates: List[str] = [
            m.name.replace("models/", "")
            for m in raw_models
            if _is_candidate(m)
        ]

        # Sort: preferred_model always first, then by flash/pro ranking
        def sort_key(name: str) -> tuple:
            return (0 if name == self.preferred_model else 1, _model_score(name))

        candidates.sort(key=sort_key)

        logger.info(f"Discovered {len(candidates)} compatible model(s).")
        logger.info(f"Selected model order (first 8): {candidates[:8]}")
        return candidates

    # ── Error Helpers ─────────────────────────────────────────────

    @staticmethod
    def _is_overload(e: Exception) -> bool:
        """503 UNAVAILABLE — temporary, worth retrying."""
        s = str(e)
        return "503" in s or "UNAVAILABLE" in s

    @staticmethod
    def _is_quota(e: Exception) -> bool:
        """429 RESOURCE_EXHAUSTED — skip model immediately."""
        s = str(e)
        return "429" in s or "RESOURCE_EXHAUSTED" in s

    @staticmethod
    def _is_fatal(e: Exception) -> bool:
        """400/401/403/404 — configuration errors, no point retrying."""
        s = str(e)
        return any(code in s for code in ("400 ", "401 ", "403 ", "404 "))

    # ── Core Completion ───────────────────────────────────────────

    def get_structured_completion(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        temperature: float = 0.2,
    ) -> T:
        """
        Sends messages to the Gemini API and parses the response into
        response_model using structured JSON output.

        Tries each model in _model_chain in order:
          • 503  → retry up to 2 times with exponential backoff, then next model
          • 429  → skip to next model immediately
          • 4xx  → skip to next model immediately
          • Other→ skip to next model immediately
        """
        if not self.client:
            raise ValueError("GenAI client not initialised (missing API key?).")

        if not self._model_chain:
            raise RuntimeError(
                "No compatible Gemini models discovered. "
                "Check your API key and network access."
            )

        # Build prompt from message list
        system_instruction = ""
        user_parts: List[str] = []
        for msg in messages:
            if msg.get("role") == "system":
                system_instruction = msg.get("content", "")
            else:
                user_parts.append(msg.get("content", ""))
        prompt = "\n\n".join(user_parts)

        last_error: Exception = RuntimeError("All models exhausted.")

        for model in self._model_chain:
            max_retries = 2
            backoff = 5.0  # seconds — longer than default for 503 overload

            for attempt in range(max_retries):
                try:
                    logger.info(
                        f"Calling model '{model}' "
                        f"(attempt {attempt + 1}/{max_retries})..."
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

                    text = response.text
                    if not text:
                        raise ValueError("Received empty response from Gemini API.")

                    logger.info(f"✓ Model '{model}' returned a valid response.")
                    try:
                        return response_model.model_validate_json(text)
                    except AttributeError:
                        return response_model.parse_raw(text)  # pydantic v1 compat

                except Exception as e:
                    last_error = e
                    short = str(e)[:120]

                    if self._is_fatal(e):
                        logger.warning(
                            f"✗ Model '{model}' — fatal error (skipping): {short}"
                        )
                        break  # try next model

                    if self._is_quota(e):
                        logger.warning(
                            f"✗ Model '{model}' — quota exhausted (skipping): {short}"
                        )
                        break  # try next model

                    if self._is_overload(e):
                        if attempt < max_retries - 1:
                            logger.warning(
                                f"⚠ Model '{model}' overloaded (503), "
                                f"attempt {attempt + 1}/{max_retries}. "
                                f"Retrying in {backoff:.0f}s..."
                            )
                            time.sleep(backoff)
                            backoff *= 2
                            continue  # retry same model
                        else:
                            logger.warning(
                                f"✗ Model '{model}' still unavailable after "
                                f"{max_retries} attempts. Trying next model."
                            )
                            break  # try next model

                    # Unknown / unexpected error
                    logger.warning(
                        f"✗ Model '{model}' — unexpected error (skipping): {short}"
                    )
                    break  # try next model

        logger.error(f"All models in chain exhausted. Last error: {last_error}")
        raise last_error
