from langchain_openai import AzureChatOpenAI
from app.settings import APP_SETTINGS


class AzureLLMFactory:
    def __init__(self, model: str = "gpt-4.1", temperature: float = 0.0):
        self.model = model
        self.temperature = temperature
        self.endpoint = APP_SETTINGS.AZURE_OPENAI_ENDPOINT
        self.api_key = APP_SETTINGS.AZURE_OPENAI_KEY
        self.api_version = APP_SETTINGS.AZURE_OPENAI_API_VERSION

    def create(self) -> AzureChatOpenAI:
        return AzureChatOpenAI(
            model=self.model,
            temperature=self.temperature,
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
        )


# Usage
llm_factory = AzureLLMFactory()
llm = llm_factory.create()
