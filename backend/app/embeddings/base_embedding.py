from abc import ABC, abstractmethod
from langchain_core.embeddings import Embeddings
from typing import List


class BaseEmbeddings(Embeddings, ABC):
    """Abstract base class for embeddings implementations"""

    def __init__(self, **kwargs):
        super().__init__()
        # Không tự động gọi _initialize_embeddings ở đây
        # Để subclass tự quyết định khi nào khởi tạo

    @abstractmethod
    def _initialize_embeddings(self, **kwargs):
        """Initialize the specific embeddings implementation - có thể return None nếu không cần"""
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents - must be implemented by subclass"""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query - must be implemented by subclass"""
        pass

    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings - must be implemented by subclass"""
        pass

    @abstractmethod
    def get_text_embedding(self, text: str) -> List[float]:
        """Get embedding for single text"""
        pass

    @abstractmethod
    def get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts"""
        pass
