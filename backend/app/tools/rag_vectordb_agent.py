from langgraph.prebuilt import create_react_agent

# from app.embeddings import AzureOpenAIEmbeddingModel
from app.llm_loader import AzureLLMFactory
from app.retriever.vetordb import QdrantVectordb
from app.services.langfuse.client import LangfuseClient


class RetrieverVectordb:
    def __init__(self):

        # Initialize embedding model once
        # embedding_model = AzureOpenAIEmbeddingModel().init_model()
        self.llm = AzureLLMFactory().create()
        self.langfuse_client = LangfuseClient()
        self.retriever = QdrantVectordb().vector_store()

    def retriever_data(self, query: str):
        """Search and return information about Mega market."""
        results = self.retriever.invoke(query)
        return results

    def retriever_vectordb(self):
        retriever_vectordb = create_react_agent(
            model=self.llm,
            tools=[self.retriever_data],
            prompt=self.langfuse_client.get_prompt("vectordb_agent"),
            name="retriever_vectordb",
        )
        return retriever_vectordb
