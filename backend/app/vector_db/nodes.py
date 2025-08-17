from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import uuid
import logging

logger = logging.getLogger(__name__)


@dataclass
class TextNode:
    """
    Represents a text chunk node compatible with LlamaIndex Node structure.

    THAY ĐỔI CHÍNH:
    1. Thêm compatibility methods với LlamaIndex
    2. Cải thiện embedding handling
    3. Thêm node relationships support
    4. Better serialization support
    """

    id_: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    # LlamaIndex compatibility fields
    excluded_embed_metadata_keys: List[str] = field(default_factory=list)
    excluded_llm_metadata_keys: List[str] = field(default_factory=list)
    relationships: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize node after creation"""
        if not self.id_:
            self.id_ = str(uuid.uuid4())

        # Set default excluded keys for embedding (URLs, IDs, etc.)
        if not self.excluded_embed_metadata_keys:
            self.excluded_embed_metadata_keys = [
                "product_url",
                "image_url",
                "source",
                "row_index",
                "node_type",
                "_original_payload_keys",
                "_search_debug",
            ]

        # Set default excluded keys for LLM (technical metadata)
        if not self.excluded_llm_metadata_keys:
            self.excluded_llm_metadata_keys = [
                "product_url",
                "image_url",
                "source",
                "row_index",
                "_original_payload_keys",
                "_search_debug",
            ]

    def get_content(self, metadata_mode: str = "all") -> str:
        """
        Get node content with optional metadata inclusion

        Args:
            metadata_mode: "none", "embed", or "all"
        """
        if metadata_mode == "none":
            return self.text

        elif metadata_mode == "embed":
            # Include only embedding-relevant metadata
            key_metadata = {}
            for k, v in self.metadata.items():
                if k not in self.excluded_embed_metadata_keys and v:
                    key_metadata[k] = v

            if key_metadata:
                metadata_str = " ".join([f"{k}: {v}" for k, v in key_metadata.items()])
                return f"{metadata_str} {self.text}"
            return self.text

        else:  # "all" - for LLM context
            relevant_metadata = {}
            for k, v in self.metadata.items():
                if k not in self.excluded_llm_metadata_keys and v:
                    relevant_metadata[k] = v

            if relevant_metadata:
                metadata_str = " ".join(
                    [f"{k}: {v}" for k, v in relevant_metadata.items()]
                )
                return f"{metadata_str} {self.text}"
            return self.text

    def get_metadata_str(self, mode: str = "all") -> str:
        """Get formatted metadata string"""
        if mode == "embed":
            relevant_keys = [
                k
                for k in self.metadata.keys()
                if k not in self.excluded_embed_metadata_keys
            ]
        else:
            relevant_keys = [
                k
                for k in self.metadata.keys()
                if k not in self.excluded_llm_metadata_keys
            ]

        relevant_metadata = {
            k: self.metadata[k] for k in relevant_keys if self.metadata.get(k)
        }
        return " ".join([f"{k}: {v}" for k, v in relevant_metadata.items()])

    def set_content(self, text: str) -> None:
        """Set node content"""
        self.text = text

    def get_node_id(self) -> str:
        """Get node ID - LlamaIndex compatibility"""
        return self.id_

    def get_type(self) -> str:
        """Get node type - LlamaIndex compatibility"""
        return "TextNode"

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary for serialization"""
        return {
            "id_": self.id_,
            "text": self.text,
            "metadata": self.metadata,
            "embedding": self.embedding,
            "excluded_embed_metadata_keys": self.excluded_embed_metadata_keys,
            "excluded_llm_metadata_keys": self.excluded_llm_metadata_keys,
            "relationships": self.relationships,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TextNode":
        """Create node from dictionary"""
        return cls(
            id_=data.get("id_", ""),
            text=data.get("text", ""),
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
            excluded_embed_metadata_keys=data.get("excluded_embed_metadata_keys", []),
            excluded_llm_metadata_keys=data.get("excluded_llm_metadata_keys", []),
            relationships=data.get("relationships", {}),
        )

    def __repr__(self) -> str:
        return f"TextNode(id_={self.id_}, text='{self.text[:50]}...', metadata_keys={list(self.metadata.keys())})"
