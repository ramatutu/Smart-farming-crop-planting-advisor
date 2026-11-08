import os
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentResponse


load_dotenv()


class GeminiClient:

    def __init__(self) -> None:

        api_key: str | None = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("Gemini API key was not found.")

        self.client = genai.Client(api_key=api_key)
    def generate_response(self, prompt: str) -> str:

        response: GenerateContentResponse = self.client.models.generate_content(
            model="gemini-3.7-flash",
            contents=prompt
        )

        return response.text or ""