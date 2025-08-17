from langchain_core.vectorstores import InMemoryVectorStore

from app.embeddings import AzureOpenAIEmbeddingModel
from app.data_loader import DataIngestion
from app.settings import APP_SETTINGS


class InMemoryRetriever:
    def __init__(self):
        self.doc_splits = DataIngestion(csv_file=APP_SETTINGS.file_path).process_csv()
        self.embeddings = AzureOpenAIEmbeddingModel().init_model()
        self._vectorstore = None

    def vector_store(self, top_k: int = 5, score_threshold: float = None):
        try:
            if not self._vectorstore:
                self._vectorstore = InMemoryVectorStore.from_documents(
                    documents=self.doc_splits, embedding=self.embeddings
                )
            search_kwargs = {"k": top_k}
            if score_threshold is not None:
                search_kwargs["score_threshold"] = score_threshold
            return self._vectorstore.as_retriever(search_kwargs=search_kwargs)
        except Exception as e:
            raise RuntimeError(f"Failed to create vector store: {str(e)}")
