from langchain_openai import AzureOpenAIEmbeddings

from app.settings import APP_SETTINGS


class AzureOpenAIEmbeddingModel:
    def __init__(self):
        pass

    def init_model(self):
        return AzureOpenAIEmbeddings(
            azure_endpoint=APP_SETTINGS.AZURE_OPENAI_ENDPOINT_EMBEDDING,
            azure_deployment=APP_SETTINGS.AZURE_OPENAI_DEPLOYMENT,
            api_key=APP_SETTINGS.AZURE_OPENAI_KEY,
        )
