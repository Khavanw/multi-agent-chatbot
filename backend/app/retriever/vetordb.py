from typing import List
from langchain_qdrant import FastEmbedSparse, QdrantVectorStore, RetrievalMode
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, SparseVectorParams, VectorParams

from app.settings import APP_SETTINGS
from app.embeddings import AzureOpenAIEmbeddingModel


class QdrantVectordb:
    def __init__(self):
        self.sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")
        self.embeddings = AzureOpenAIEmbeddingModel().init_model()
        self._client = None
        self._qdrant_store = None
        self._initialized = False  # Flag để kiểm tra trạng thái khởi tạo

    def _create_client(self) -> QdrantClient:
        """Create and initialize Qdrant client and collection if not already initialized."""
        if self._initialized:
            return self._client

        self._client = QdrantClient(
            url=APP_SETTINGS.QDRANT_URL,
            api_key=APP_SETTINGS.QDRANT_SERVICE_API_KEY,
        )

        # Chỉ tạo collection nếu chưa tồn tại
        if "chat_collection" not in [
            c.name for c in self._client.get_collections().collections
        ]:
            self._client.create_collection(
                collection_name="chat_collection",
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
                sparse_vectors_config={
                    "sparse": SparseVectorParams(
                        index=models.SparseIndexParams(on_disk=False)
                    )
                },
            )
        self._initialized = True
        return self._client

    def _get_qdrant_store(self) -> QdrantVectorStore:
        """Initialize and cache Qdrant vector store."""
        if not self._qdrant_store:
            self._qdrant_store = QdrantVectorStore(
                client=self._create_client(),
                collection_name="chat_collection",
                embedding=self.embeddings,
                sparse_embedding=self.sparse_embeddings,
                retrieval_mode=RetrievalMode.HYBRID,
                sparse_vector_name="sparse",
            )
        return self._qdrant_store

    def add_documents(self, documents: List[str], ids: List[str]) -> None:
        """Add a list of documents with IDs to Qdrant."""
        if not documents or not ids or len(documents) != len(ids):
            raise ValueError(
                "Documents and IDs must be non-empty and have equal length"
            )
        self._get_qdrant_store().add_documents(documents, ids)

    def vector_store(self, top_k: int = 5):
        """Search similar documents from query."""
        retriever = self._get_qdrant_store().as_retriever(search_kwargs={"k": top_k})
        return retriever

    def retriever(self, query: str, top_k: int = 4) -> List[str]:
        """Search similar documents from query."""
        retriever = self._get_qdrant_store().as_retriever(search_kwargs={"k": top_k})
        results = retriever.invoke(query)
        return results

    def get_all_documents(self, limit: int = 100, offset: int = 0) -> List[str]:
        """Return all stored documents in the collection with pagination."""
        client = self._create_client()
        search_result = client.scroll(
            collection_name="chat_collection",
            limit=limit,
            offset=offset,
            with_payload=True,
        )
        return [point.payload.get("content", "") for point in search_result[0]]
