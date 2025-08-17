import json
import time
import logging
import uuid
import hashlib
import re
from typing import List, Dict, Optional, Tuple, Union, Any
from langchain_core.documents import Document
from qdrant_client import QdrantClient, models
from langchain_qdrant import QdrantVectorStore
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

from .nodes import TextNode
from .base_vectordb import BaseVectorDatabase
from app.embeddings.base_embedding import BaseEmbeddings
from app.settings import APP_SETTINGS

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class QdrantVectorDatabase(BaseVectorDatabase):
    """
    Qdrant vector database implementation with unified interface
    """

    def __init__(
        self,
        embed_model: BaseEmbeddings,  # Now uses unified interface
        collection_name: str,
        documents: List[Document],
        vector_size: int = 768,
        distance_metric: str = "COSINE",
        timeout: int = 10,
    ):
        super().__init__(collection_name, documents, embed_model)
        self.vector_size = vector_size
        self.distance_metric = getattr(models.Distance, distance_metric)
        self.timeout = timeout
        self._client_cache = {}  # Cache clients

    def create_vector_database(self) -> Any:
        """Main method to create vector database"""
        client = self._create_client(read_only=False)
        self._create_collection(client, self.collection_name)
        vector_store = self._initialize_vector_store(client, self.collection_name)
        self._add_documents_if_needed(client, vector_store)
        return vector_store

    def load_vector_database(self, collection_name: Optional[str] = None) -> Any:
        """Load existing vector database"""
        target_collection = collection_name or self.collection_name
        client = self._create_client(read_only=False)

        # Ensure collection exists before loading
        self._create_collection(client, target_collection)
        return self._initialize_vector_store(client, target_collection)

    def _create_client(self, read_only: bool = False) -> QdrantClient:
        """Create Qdrant client with caching"""
        cache_key = f"client_{read_only}"

        if cache_key in self._client_cache:
            return self._client_cache[cache_key]

        try:
            # Select API key based on read_only parameter
            api_key = (
                APP_SETTINGS.QDRANT_SERVICE_API_KEY
                if read_only
                else APP_SETTINGS.QDRANT_SERVICE_API_KEY
            )

            client = QdrantClient(
                url=APP_SETTINGS.QDRANT_URL,
                api_key=api_key,
                timeout=self.timeout,
            )

            # Test connection
            client.get_collections()

            # Cache the client
            self._client_cache[cache_key] = client
            return client

        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Qdrant server at {APP_SETTINGS.QDRANT_ENPOINT}: {str(e)}"
            )

    def _create_collection(
        self, client: QdrantClient, collection_name: Optional[str] = None
    ) -> None:
        """Create collection if it doesn't exist"""
        target_collection = collection_name or self.collection_name

        try:
            if not client.collection_exists(target_collection):
                logger.info(f"Creating new collection: {target_collection}")

                client.create_collection(
                    collection_name=target_collection,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=self.distance_metric,
                    ),
                )
                logger.info(f"✅ Collection {target_collection} created successfully")
            else:
                logger.info(f"Collection {target_collection} already exists")
        except Exception as e:
            logger.error(f"❌ Failed to create collection {target_collection}: {e}")
            raise

    def _initialize_vector_store(
        self, client: QdrantClient, collection_name: Optional[str] = None
    ) -> QdrantVectorStore:
        """Initialize vector store"""
        target_collection = collection_name or self.collection_name

        return QdrantVectorStore(
            client=client,
            collection_name=target_collection,
            embedding=self.embed_model,
        )

    # ----------------- Helpers for JSON-safety -----------------
    @staticmethod
    def make_json_safe(value: Any):
        try:
            json.dumps(value)
            return value
        except Exception:
            return str(value)

    @staticmethod
    def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        out = {}
        for k, v in (metadata or {}).items():
            # convert numpy types etc.
            if isinstance(v, (list, dict)):
                try:
                    json.dumps(v)
                    out[k] = v
                except Exception:
                    out[k] = str(v)
            else:
                out[k] = QdrantVectorDatabase.make_json_safe(v)
        return out

    # ----------------- Add Nodes (consistent nested metadata) -----------------
    def add_nodes(
        self, nodes: List[TextNode], collection_name: Optional[str] = None
    ) -> Tuple[int, int]:
        if not nodes:
            return 0, 0
        target_collection = collection_name or self.collection_name
        client = self._create_client(read_only=False)
        self._create_collection(client, target_collection)

        points = []
        for node in nodes:
            if node.embedding is None:
                logger.warning(f"Node {node.id_} has no embedding, skipping")
                continue

            # validate embedding length and cast to floats
            try:
                emb = list(map(float, node.embedding))
            except Exception:
                logger.warning(
                    f"Node {node.id_} embedding not castable to float list, skipping"
                )
                continue

            if len(emb) != self.vector_size:
                logger.warning(
                    f"Node {node.id_} embedding length {len(emb)} != expected {self.vector_size}, skipping"
                )
                continue

            # prepare payload with nested metadata
            payload = {
                "text": node.text,
                "original_node_id": node.id_,
                "metadata": QdrantVectorDatabase.sanitize_metadata(node.metadata or {}),
            }

            point_id = node.id_
            # ensure point_id is valid uuid-like string; fallback to uuid5 if not
            try:
                if not (
                    isinstance(point_id, str)
                    and len(point_id) == 36
                    and point_id.count("-") == 4
                ):
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, point_id))
            except Exception:
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(uuid.uuid4())))

            points.append(PointStruct(id=point_id, vector=emb, payload=payload))

        try:
            if points:
                client.upsert(collection_name=target_collection, points=points)
            logger.info(
                f"✅ Added {len(points)} nodes to collection '{target_collection}'"
            )
            return len(points), 0
        except Exception as e:
            logger.error(f"❌ Error adding nodes to '{target_collection}': {e}")
            return 0, len(nodes)

    # ----------------- Query (supports filters, unpack both nested/flat payloads) -----------------
    def query(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict] = None,
        collection_name: Optional[str] = None,
    ) -> List[TextNode]:
        target_collection = collection_name or self.collection_name
        client = self._create_client(read_only=True)

        # Build filter if provided
        search_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                try:
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not build filter condition for {key}={value}: {e}"
                    )
            if conditions:
                search_filter = Filter(must=conditions)

        # Search
        results = client.search(
            collection_name=target_collection,
            query_vector=list(map(float, query_embedding)),
            limit=top_k,
            query_filter=search_filter,
            with_payload=True,
        )

        # Convert to TextNodes
        nodes = []
        for result in results:
            payload = result.payload or {}
            text = payload.get("text", "")
            original_node_id = payload.get("original_node_id", str(result.id))

            # Normalize metadata: support nested 'metadata' or flat payload
            if "metadata" in payload and isinstance(payload["metadata"], dict):
                metadata = payload["metadata"].copy()
            else:
                metadata = {
                    k: v
                    for k, v in payload.items()
                    if k not in ("text", "original_node_id")
                }

            # Ensure values JSON-safe
            metadata = QdrantVectorDatabase.sanitize_metadata(metadata)
            metadata["similarity_score"] = float(getattr(result, "score", 0.0))

            node = TextNode(
                id_=original_node_id,
                text=text,
                metadata=metadata,
                embedding=None,  # don't hydrate embedding here
            )
            nodes.append(node)

        logger.info(f"🔍 Retrieved {len(nodes)} nodes from query")
        return nodes

    # ----------------- Document ingestion helpers -----------------
    def add_new_documents(
        self, new_documents: List[Document], collection_name: Optional[str] = None
    ) -> Tuple[List[Document], int]:
        """Add new documents to the collection with unified signature"""
        target_collection = collection_name or self.collection_name

        if not new_documents:
            logger.info("No new documents to add")
            return [], 0

        read_only_client = self._create_client(read_only=True)
        write_client = self._create_client(read_only=False)

        # Ensure collection exists
        self._create_collection(write_client, target_collection)

        vector_store = self._initialize_vector_store(write_client, target_collection)
        existing_doc_keys = self._get_existing_document_keys(
            read_only_client, target_collection
        )

        filtered_documents = self._filter_new_documents(
            existing_doc_keys, new_documents
        )
        duplicate_count = len(new_documents) - len(filtered_documents)

        if filtered_documents:
            logger.info(
                f"Adding {len(filtered_documents)} new documents out of {len(new_documents)} provided"
            )
            self._add_documents_batch(vector_store, filtered_documents)
            return filtered_documents, duplicate_count
        else:
            logger.info("All provided documents already exist in the collection")
            return [], duplicate_count

    # Helper methods remain the same as in original implementation but we ensure nested metadata in prepared docs
    def _generate_document_key(self, document: Document) -> str:
        """Generate consistent document key"""
        title_raw = document.metadata.get("title", "unknown")
        title = re.sub(r"[^a-zA-Z0-9]+", "_", title_raw.lower()).strip("_")

        content_hash = hashlib.md5(document.page_content.encode("utf-8")).hexdigest()[
            :8
        ]
        page = document.metadata.get("page", "")

        if page is not None and str(page).strip():
            page_str = str(page).strip()
            doc_key = f"{title}_{page_str}_{content_hash}"
        else:
            doc_key = f"{title}_{content_hash}"

        return doc_key

    def _generate_point_id(self, document_key: str) -> str:
        """Generate point ID from document key"""
        namespace = uuid.NAMESPACE_DNS
        return str(uuid.uuid5(namespace, document_key))

    def _prepare_document_for_storage(self, document: Document) -> Document:
        """Prepare document for storage by adding metadata and ID.
        Ensure metadata nested under 'metadata' and include original_node_id and text.
        """
        doc_key = self._generate_document_key(document)
        point_id = self._generate_point_id(doc_key)

        prepared_doc = Document(
            page_content=document.page_content,
            metadata={},  # we'll set nested metadata below
        )

        # sanitize original metadata and nest it
        sanitized = QdrantVectorDatabase.sanitize_metadata(document.metadata or {})
        prepared_doc.metadata["metadata"] = sanitized
        prepared_doc.metadata["original_node_id"] = point_id
        # Keep text in metadata as well so vector_store implementations that only rely on metadata still have it
        prepared_doc.metadata["text"] = document.page_content

        prepared_doc.metadata["doc_key"] = doc_key
        prepared_doc.metadata["content_hash"] = hashlib.md5(
            document.page_content.encode("utf-8")
        ).hexdigest()[:8]
        prepared_doc.id = str(point_id)

        return prepared_doc

    def _get_existing_document_keys(
        self, client: QdrantClient, collection_name: str
    ) -> Dict[str, str]:
        """Get mapping of existing document keys to point IDs"""
        try:
            if not client.collection_exists(collection_name):
                logger.warning(f"Collection {collection_name} doesn't exist")
                return {}

            collection_info = client.get_collection(collection_name)
            if collection_info.points_count == 0:
                logger.info(f"Collection {collection_name} is empty")
                return {}

            existing_mapping = {}
            offset = None

            while True:
                result = client.scroll(
                    collection_name=collection_name,
                    limit=1000,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )

                points, next_offset = result

                for point in points:
                    if point.payload:
                        doc_key = None
                        if "doc_key" in point.payload:
                            doc_key = point.payload["doc_key"]
                        elif "metadata" in point.payload and point.payload["metadata"]:
                            metadata = point.payload["metadata"]
                            if "doc_key" in metadata:
                                doc_key = metadata["doc_key"]

                        if doc_key:
                            existing_mapping[doc_key] = point.id

                if next_offset is None:
                    break
                offset = next_offset

            logger.info(f"Retrieved {len(existing_mapping)} existing documents")
            return existing_mapping

        except Exception as e:
            logger.error(f"Error getting existing document keys: {e}")
            return {}

    def _filter_new_documents(
        self, existing_doc_keys: Dict[str, str], documents: List[Document]
    ) -> List[Document]:
        """Filter out documents that already exist in the collection"""
        if not documents:
            return []

        new_documents = []
        duplicate_count = 0

        for doc in documents:
            doc_key = self._generate_document_key(doc)
            if doc_key not in existing_doc_keys:
                new_documents.append(doc)
            else:
                duplicate_count += 1

        logger.info(
            f"Filtered {len(new_documents)} new documents from {len(documents)} total. "
            f"Found {duplicate_count} duplicates."
        )
        return new_documents

    def _add_documents_batch(
        self, vector_store: QdrantVectorStore, documents: List[Document]
    ) -> int:
        """Add documents in batches"""
        batch_size = 100
        inserted_total = 0

        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            prepared_docs = [self._prepare_document_for_storage(doc) for doc in batch]
            point_ids = [doc.id for doc in prepared_docs]

            try:
                # vector_store.add_documents should pick up our prepared_doc.metadata
                vector_store.add_documents(prepared_docs, ids=point_ids)
                inserted_total += len(prepared_docs)
                logger.info(
                    f"Added batch {i // batch_size + 1} with {len(prepared_docs)} documents"
                )
            except Exception as e:
                logger.error(f"Failed to add batch {i // batch_size + 1}: {e}")
                continue

        return inserted_total

    def _add_documents_if_needed(
        self, client: QdrantClient, vector_store: QdrantVectorStore
    ) -> None:
        """Add documents if collection is empty or merge with existing"""
        try:
            collection_info = client.get_collection(self.collection_name)

            if collection_info.points_count == 0:
                if self.documents:
                    logger.info(
                        f"Adding {len(self.documents)} documents to empty collection"
                    )
                    self._add_documents_batch(vector_store, self.documents)
            else:
                logger.info(
                    f"Collection contains {collection_info.points_count} existing points"
                )
                existing_doc_keys = self._get_existing_document_keys(
                    client, self.collection_name
                )
                new_documents = self._filter_new_documents(
                    existing_doc_keys, self.documents
                )

                if new_documents:
                    logger.info(f"Found {len(new_documents)} new documents to add")
                    self._add_documents_batch(vector_store, new_documents)

        except Exception as e:
            logger.error(f"Error checking/adding documents: {e}")
            raise
