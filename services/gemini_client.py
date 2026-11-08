import os
from typing import Any, cast
from dotenv import load_dotenv
from google import genai
from google.genai._gaos.types.interactions.interaction import Interaction


_ = load_dotenv()


class GeminiClient:

    def __init__(self) -> None:

        api_key: str | None = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("Gemini API key was not found.")

        self.client: genai.Client = genai.Client(api_key=api_key)

        # Track when the API quota has been reached
        self.rate_limited: bool = False

    def generate_response(self, prompt: str) -> str:

        if self.rate_limited:
            return (
                "Gemini API quota has been reached. "
                "Please try again when your quota resets."
            )

        try:
            interaction: Interaction = cast(
                Interaction,
                cast(Any, self.client.interactions).create(
                    model="gemini-3.8-flash",
                    input=prompt,
                    timeout=120,
                    generation_config={
                        "thinking_level": "low",
                        "max_output_tokens": 500
                    }
                ),
            )

            if interaction.output_text:
                return interaction.output_text

            return "Gemini returned an empty response."

        except KeyboardInterrupt:
            self.rate_limited = True

            return (
                "Gemini request was interrupted. "
                "The AI service may be experiencing rate limits."
            )

        except Exception as error:

            error_message: str = str(error).lower()

            if any(message in error_message for message in [
                "429",
                "too many requests",
                "resource_exhausted",
                "quota",
                "rate limit"
            ]):

                self.rate_limited = True

                return (
                    "Gemini API quota has been reached. "
                    "Please try again when your quota resets."
                )

            return (
                "Sorry, the AI planting advisor is temporarily "
                "unavailable. Please try again later."
            )