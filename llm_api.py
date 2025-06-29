# An abstraction layer for interacting with different Large Language Model APIs.

import os
import google.generativeai as genai
from openai import OpenAI
import config
from rich.console import Console

console = Console()

class LLM_API:
    """Base class for LLM API interactions."""
    def __init__(self, model_name: str):
        self.model_name = model_name

    def generate_content(self, history: list) -> str:
        """
        Generates content based on the provided history.
        This method should be implemented by subclasses.
        """
        raise NotImplementedError

    def correct_json(self, malformed_json: str) -> str:
        """
        Attempts to correct a malformed JSON string.
        This method should be implemented by subclasses for specific API calls.
        """
        raise NotImplementedError


class GeminiAPI(LLM_API):
    """Handles interactions with the Google Gemini API."""
    def __init__(self, model_name: str, api_key: str):
        super().__init__(model_name)
        if not api_key:
            raise ValueError("Google API key is not set. Please set the GOOGLE_API_KEY environment variable.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def generate_content(self, history: list) -> str:
        """Calls the Gemini API to generate content."""
        response = self.model.generate_content(history)
        return response.text

    def correct_json(self, malformed_json: str) -> str:
        """Uses the Gemini API to correct JSON."""
        prompt = f"The following text is a malformed JSON. Please correct it and only return the valid JSON object. Do not add any explanatory text or markdown formatting.\n\nMalformed JSON:\n```json\n{malformed_json}\n```\n\nCorrected JSON:"
        response = self.model.generate_content(prompt)
        return response.text


class OpenAIAPI(LLM_API):
    """Handles interactions with the OpenAI API."""
    def __init__(self, model_name: str, api_key: str):
        super().__init__(model_name)
        if not api_key:
            raise ValueError("OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable.")
        self.client = OpenAI(api_key=api_key)

    def _translate_history(self, history: list) -> list:
        """Translates the history from Gemini format to OpenAI format."""
        translated_history = []
        for message in history:
            if message["role"] == "user" and "Begin!" in message["parts"][0]:
                 translated_history.append({"role": "system", "content": message["parts"][0]})
                 if len(message["parts"]) > 1:
                    translated_history.append({"role": "user", "content": "\n".join(message["parts"][1:])})
            else:
                 translated_history.append({
                    "role": "assistant" if message["role"] == "model" else "user",
                    "content": "\n".join(part for part in message["parts"])
                })
        return translated_history

    def generate_content(self, history: list) -> str:
        """Translates the history and calls the OpenAI API to generate content."""
        translated_history = self._translate_history(history)
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=translated_history,
            temperature=0.7,
        )
        return response.choices[0].message.content

    def correct_json(self, malformed_json: str) -> str:
        """Uses the OpenAI API to correct JSON."""
        system_prompt = "You are a JSON correction utility. You will receive a potentially malformed JSON string and your only task is to return a valid JSON object. Do not include any text before or after the JSON object, and do not use markdown code blocks."
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": malformed_json}
            ],
            temperature=0.0, # Be deterministic for correction
        )
        return response.choices[0].message.content


class OpenRouterAPI(OpenAIAPI):
    """Handles interactions with the OpenRouter API."""
    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        if not api_key:
            raise ValueError("OpenRouter API key is not set. Please set the OPENROUTER_API_KEY environment variable.")
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/your-repo",
                "X-Title": "AI Coding Agent",
            },
        )


def get_llm_api(provider: str) -> LLM_API:
    """Factory function for the main reasoning LLM."""
    console.print(f"[bold]Using Main API Provider: {provider}[/bold]")
    if provider == "google":
        return GeminiAPI(model_name=config.GEMINI_REASONING_MODEL_NAME, api_key=config.GOOGLE_API_KEY)
    elif provider == "openai":
        return OpenAIAPI(model_name=config.OPENAI_REASONING_MODEL_NAME, api_key=config.OPENAI_API_KEY)
    elif provider == "openrouter":
        return OpenRouterAPI(model_name=config.OPENROUTER_REASONING_MODEL_NAME, api_key=config.OPENROUTER_API_KEY)
    else:
        raise ValueError(f"Unsupported API provider: {provider}")

def get_corrector_api(provider: str) -> LLM_API:
    """Factory function for the JSON corrector LLM."""
    console.print(f"[bold]Using Corrector API Provider: {provider}[/bold]")
    if provider == "google":
        return GeminiAPI(model_name=config.GEMINI_CORRECTOR_MODEL_NAME, api_key=config.GOOGLE_API_KEY)
    elif provider == "openai":
        return OpenAIAPI(model_name=config.OPENAI_CORRECTOR_MODEL_NAME, api_key=config.OPENAI_API_KEY)
    elif provider == "openrouter":
        return OpenRouterAPI(model_name=config.OPENROUTER_CORRECTOR_MODEL_NAME, api_key=config.OPENROUTER_API_KEY)
    else:
        raise ValueError(f"Unsupported Corrector API provider: {provider}")
