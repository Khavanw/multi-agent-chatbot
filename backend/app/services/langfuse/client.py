from app.settings import APP_SETTINGS
from langfuse import Langfuse


class LangfuseClient:
    def __init__(self):
        self._client = Langfuse(
            public_key=APP_SETTINGS.LANGFUSE_PUBLIC_KEY,
            secret_key=APP_SETTINGS.LANGFUSE_SECRET_KEY,
            host=APP_SETTINGS.LANGFUSE_HOST,
        )

    def get_prompt(self, name: str, label: str = "latest"):
        prompt = self._client.get_prompt(name, label=label)
        return prompt.prompt
