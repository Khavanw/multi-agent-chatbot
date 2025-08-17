from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Union
from langchain_core.documents import Document

from .nodes import TextNode
from app.embeddings.base_embedding import BaseEmbeddings  # Unified interface


class BaseVectorDatabase(ABC):
    """Abstract base class for vector database implementations"""

    def __init__(
        self,
        collection_name: str,
        documents: List[Document],
        embed_model: BaseEmbeddings,  # Unified embedding interface
    ):
        self.collection_name = collection_name
        self.documents = documents
        self.embed_model = embed_model
        self.vector_store = None

    @abstractmethod
    def _create_client(self, read_only: bool = False) -> Any:
        """Create and return the vector database client

        Args:
            read_only: Whether to create read-only client
        """
        pass

    @abstractmethod
    def _create_collection(
        self, client: Any, collection_name: Optional[str] = None
    ) -> None:
        """Create collection if it doesn't exist

        Args:
            client: Database client
            collection_name: Name of collection (optional, uses self.collection_name if None)
        """
        pass

    @abstractmethod
    def _initialize_vector_store(
        self, client: Any, collection_name: Optional[str] = None
    ) -> Any:
        """Initialize and return the vector store

        Args:
            client: Database client
            collection_name: Name of collection (optional, uses self.collection_name if None)
        """
        pass

    @abstractmethod
    def _add_documents_if_needed(self, client: Any, vector_store: Any) -> None:
        """Add documents to collection if needed"""
        pass

    @abstractmethod
    def add_nodes(
        self, nodes: List[TextNode], collection_name: Optional[str] = None
    ) -> Tuple[int, int]:
        """Add nodes to vector store

        Args:
            nodes: List of TextNodes to add
            collection_name: Target collection name (optional)

        Returns:
            Tuple of (inserted_count, failed_count)
        """
        pass

    @abstractmethod
    def query(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None,
        collection_name: Optional[str] = None,
    ) -> List[TextNode]:
        """Query vector store

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filters: Optional metadata filters
            collection_name: Collection to query (optional)

        Returns:
            List of TextNodes with similarity scores
        """
        pass

    @abstractmethod
    def create_vector_database(self) -> Any:
        """Create vector database and return vector store"""
        pass

    @abstractmethod
    def load_vector_database(self, collection_name: Optional[str] = None) -> Any:
        """Load existing vector database

        Args:
            collection_name: Collection to load (optional)

        Returns:
            Vector store instance
        """
        pass

    @abstractmethod
    def add_new_documents(
        self, new_documents: List[Document], collection_name: Optional[str] = None
    ) -> Tuple[List[Document], int]:
        """Add new documents to the collection

        Args:
            new_documents: List of new documents
            collection_name: Target collection (optional)

        Returns:
            Tuple of (inserted_documents, duplicate_count)
        """
        pass

    def get_collection_name(self) -> str:
        """Get current collection name"""
        return self.collection_name

    def update_collection_name(self, new_collection_name: str) -> None:
        """Update collection name"""
        self.collection_name = new_collection_name
