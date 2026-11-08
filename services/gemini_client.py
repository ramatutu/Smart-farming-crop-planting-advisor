import logging
import os
from typing import Any, cast
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai._gaos.types.interactions.interaction import Interaction


_ = load_dotenv()

log = logging.getLogger(__name__)

# Free-tier quota is counted PER MODEL (about 20 requests/day each), so when
# one model is used up the client moves on to the next one in this list.
# Put GEMINI_MODEL=<model name> in .env to choose which model is tried first.
DEFAULT_MODEL: str = "gemini-3.8-flash"
FALLBACK_MODELS: list[str] = [
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
]
REQUEST_TIMEOUT_SECONDS: int = 30

# Newer Gemini models "think" before answering and that thinking counts toward
# this limit, so a small number (we had 500) cuts the visible answer short.
MAX_OUTPUT_TOKENS: int = 3000

CUT_OFF_NOTE: str = "\n\n*(The answer was cut off. Click the button again to retry.)*"

QUOTA_WORDS: list[str] = [
    "429", "too many requests", "resource_exhausted", "quota", "rate limit",
]

QUOTA_MESSAGE: str = (
    "Gemini API quota has been reached. "
    "Please try again when your quota resets."
)


class GeminiClient:

    def __init__(self) -> None:

        api_key: str | None = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("Gemini API key was not found.")

        self.client: genai.Client = genai.Client(api_key=api_key)

        first: str = (os.getenv("GEMINI_MODEL") or DEFAULT_MODEL).strip()
        self.models: list[str] = [first] + [
            m for m in [DEFAULT_MODEL] + FALLBACK_MODELS if m != first
        ]

        # Models whose quota ran out during this session (skipped next time)
        self.exhausted_models: set[str] = set()
        self.active_model: str | None = None

        # True only when EVERY model has run out of quota
        self.rate_limited: bool = False

        # Real technical error from the latest failed request, shown by the
        # app in a "technical details" box so problems can be diagnosed.
        self.last_error: str | None = None

    @staticmethod
    def _is_quota_error(error: Exception) -> bool:
        message: str = str(error).lower()
        return any(word in message for word in QUOTA_WORDS)

    def _via_generate_content(self, model: str, prompt: str) -> str:
        """Standard endpoint. Fails fast, including a clear 429 on quota."""
        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=MAX_OUTPUT_TOKENS,
                http_options=types.HttpOptions(
                    timeout=REQUEST_TIMEOUT_SECONDS * 1000   # milliseconds
                ),
            ),
        )
        text: str = response.text or ""
        if text and self._was_cut_off(response):
            text += CUT_OFF_NOTE
        return text

    @staticmethod
    def _was_cut_off(response: Any) -> bool:
        try:
            reason = response.candidates[0].finish_reason
            return str(reason).upper().endswith("MAX_TOKENS")
        except Exception:
            return False

    def _via_interactions(self, model: str, prompt: str) -> str:
        """Original Interactions API method, kept as a fallback."""
        interaction: Interaction = cast(
            Interaction,
            cast(Any, self.client.interactions).create(
                model=model,
                input=prompt,
                timeout=REQUEST_TIMEOUT_SECONDS,
                generation_config={
                    "thinking_level": "low",
                    "max_output_tokens": MAX_OUTPUT_TOKENS
                }
            ),
        )
        return interaction.output_text or ""

    def generate_response(self, prompt: str) -> str:

        if self.rate_limited:
            return QUOTA_MESSAGE

        self.last_error = None
        errors: list[str] = []

        try:
            for model in self.models:
                if model in self.exhausted_models:
                    continue

                # 1) standard request
                try:
                    text: str = self._via_generate_content(model, prompt)
                    if text:
                        self.active_model = model
                        self.last_error = None
                        return text
                    errors.append(f"{model}: empty response")
                    continue
                except Exception as error:
                    errors.append(f"{model} generate_content: {type(error).__name__}: {error}")
                    log.warning("Gemini request failed (%s): %s", model, error)

                    if self._is_quota_error(error):
                        # This model is used up: try the next model.
                        self.exhausted_models.add(model)
                        continue

                # 2) non-quota failure: try the Interactions API once
                try:
                    text = self._via_interactions(model, prompt)
                    if text:
                        self.active_model = model
                        self.last_error = None
                        return text
                except Exception as error:
                    errors.append(f"{model} interactions: {type(error).__name__}: {error}")
                    log.warning("Gemini interactions failed (%s): %s", model, error)
                    if self._is_quota_error(error):
                        self.exhausted_models.add(model)
                        continue

                # A real (non-quota) failure: another model won't help.
                break

        except KeyboardInterrupt:
            self.rate_limited = True

            return (
                "Gemini request was interrupted. "
                "The AI service may be experiencing rate limits."
            )

        self.last_error = " | ".join(errors) or None

        if all(m in self.exhausted_models for m in self.models):
            self.rate_limited = True
            return QUOTA_MESSAGE

        if errors and all("empty response" in e for e in errors):
            return "Gemini returned an empty response."

        return (
            "Sorry, the AI planting advisor is temporarily "
            "unavailable. Please try again later."
        )