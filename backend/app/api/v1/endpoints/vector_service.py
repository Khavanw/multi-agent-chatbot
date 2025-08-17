import re
import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile

from pydantic import BaseModel

from qdrant_client import models
from qdrant_client.http.models import CollectionDescription
from app.db.models.structure import (
    DocumentCreate,
    InputData,
    InputDataFromURL,
    InputDataFromFile,
    ProductResponse,
    ProductListResponse,
    ProductSearchFilter,
    BulkInsertRequest,
    DocumentData,
    DocumentQueryParams,
    SearchQuery,
    DeleteRequest,
    FinalResponse,
    DeleteResponse,
    HealthResponse,
    APIResponse,
    InsertionSummary,
)
from app.vector_db.node_parser import CSVNodeParser
from app.embeddings.gemini_embedding import GeminiEmbeddingsModel
from app.llm_loader.gemini_llm import GeminiLLM
from app.data_loader._ingestion import DataIngestion
from app.vector_db.qdrant_vectordb import QdrantVectorDatabase
from qdrant_client.models import (
    PayloadSchemaType,
)
from app.settings import APP_SETTINGS
from app.core import (
    app_state,
    get_app_state,
    get_service,
    is_initialized,
    set_initialized,
    set_service,
    state,
)
from app.startup import initialize_app_services_sync

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

router = APIRouter()


# Global app state
app_state = {
    "vector_db": None,
    "llm": None,
    "embed_model": None,
    "metadata": None,
    "initialized": False,
    "init_lock": asyncio.Lock(),
    "init_attempts": 0,
}

# Global app state
app_state = {}


# Enhanced utility functions
def validate_uuid(document_id: str) -> str:
    try:
        uuid_obj = uuid.UUID(document_id)
        return str(uuid_obj)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid UUID format"
        )


async def check_document_exists(
    vector_db: QdrantVectorDatabase, document_id: str
) -> bool:
    try:
        client = vector_db._create_client()
        points = client.retrieve(
            collection_name=vector_db.collection_name,
            ids=[document_id],
            with_payload=False,
            with_vectors=False,
        )
        return len(points) > 0
    except Exception as e:
        logger.error(f"Error checking document existence: {e}")
        return False


def get_vector_db() -> QdrantVectorDatabase:
    """Get vector database with enhanced error handling"""
    if not is_initialized():
        logger.warning(
            "🔄 Vector database not initialized, attempting initialization..."
        )

        # Debug: Check current settings
        logger.info(f"🔍 Current API key status: {bool(APP_SETTINGS.GEMINI_API_KEY)}")

        try:
            success = initialize_app_services_sync()
            if not success:
                logger.error("❌ Initialization failed completely")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to initialize application services. Please check API keys and configuration.",
                )
        except Exception as init_error:
            logger.error(f"❌ Initialization error: {init_error}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service initialization failed: {str(init_error)}",
            )

    vector_db = get_service("vector_db")
    if vector_db is None:
        logger.error("❌ Vector database service is None after initialization")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector database not available. Please check service configuration.",
        )

    return vector_db


def get_llm() -> GeminiLLM:
    """Get LLM with enhanced error handling"""
    if not is_initialized():
        logger.warning("🔄 LLM not initialized, attempting initialization...")

        try:
            success = initialize_app_services_sync()
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to initialize LLM service.",
                )
        except Exception as init_error:
            logger.error(f"❌ LLM initialization error: {init_error}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"LLM initialization failed: {str(init_error)}",
            )

    llm = get_service("llm")
    if llm is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service not available.",
        )

    return llm


def get_embed_model() -> GeminiEmbeddingsModel:
    """Get embedding model with enhanced error handling"""
    if not is_initialized():
        logger.warning(
            "🔄 Embedding model not initialized, attempting initialization..."
        )

        try:
            success = initialize_app_services_sync()
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Failed to initialize embedding model service.",
                )
        except Exception as init_error:
            logger.error(f"❌ Embedding model initialization error: {init_error}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Embedding model initialization failed: {str(init_error)}",
            )

    embed_model = get_service("embed_model")
    if embed_model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding model service not available.",
        )

    return embed_model


def process_data_ingestion(
    source_type: str,
    data: Optional[List[Dict]] = None,
    url: Optional[str] = None,
    file_path: Optional[str] = None,
) -> List[Any]:
    """
    Process data ingestion based on source type with better error handling
    """
    try:
        logger.info(f"🔄 Processing data ingestion from {source_type}")

        if source_type == "data":
            if not data:
                raise ValueError("Data is required for 'data' source type")
            logger.info(f"📊 Processing {len(data)} data records")
            ingestion = DataIngestion(data=data)
            documents = ingestion.reFormat()

        elif source_type == "url":
            if not url:
                raise ValueError("URL is required for 'url' source type")
            logger.info(f"🌐 Processing URL: {url}")
            ingestion = DataIngestion(url_path=url)
            documents = ingestion.process_data_direct()

        elif source_type == "file":
            if not file_path:
                raise ValueError("File path is required for 'file' source type")
            logger.info(f"📁 Processing file: {file_path}")
            ingestion = DataIngestion(file_path=file_path)
            documents = ingestion.process_data_direct()

        else:
            raise ValueError(f"Unsupported source type: {source_type}")

        if not documents:
            raise ValueError("No documents were generated from the provided data")

        logger.info(f"✅ Generated {len(documents)} documents from {source_type}")
        return documents

    except Exception as e:
        logger.error(f"❌ Error in data ingestion: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data ingestion failed: {str(e)}",
        )


async def ensure_indexes(client, collection_name: str):
    """
    Ensure necessary indexes exist for filtering
    """
    try:
        # Tạo index cho product_category
        client.create_payload_index(
            collection_name=collection_name,
            field_name="product_category",
            field_type=PayloadSchemaType.KEYWORD,
        )
        logger.info(f"Created index for product_category in {collection_name}")
    except Exception as e:
        logger.warning(f"Index for product_category might already exist: {e}")

    try:
        # Tạo index cho product_price
        client.create_payload_index(
            collection_name=collection_name,
            field_name="product_price",
            field_type=PayloadSchemaType.FLOAT,
        )
        logger.info(f"Created index for product_price in {collection_name}")
    except Exception as e:
        logger.warning(f"Index for product_price might already exist: {e}")


import re
import logging

logger = logging.getLogger(__name__)


def extract_product_info_from_content(content: str) -> dict:
    """
    Extract product information from page_content string
    """
    product_info = {
        "product_name": "",
        "product_category": "",
        "product_price": 0.0,
        "product_price_unit": "",
        "product_url": "",
        "image_url": "",
    }

    try:
        # Parse content string theo format: "Sản phẩm: ... Loại: ... Giá: ... product_url: ... image_url: ..."
        name_match = re.search(r"Sản phẩm:\s*([^|]+?)(?=\s*\||\s+Loại:|$)", content)
        if name_match:
            product_info["product_name"] = name_match.group(1).strip()

        # Extract category
        category_match = re.search(r"Loại:\s*([^|]+?)(?=\s*\||\s+Giá:|$)", content)
        if category_match:
            product_info["product_category"] = category_match.group(1).strip()

        # Extract price - improved pattern to handle different formats
        # Try multiple patterns for price extraction
        price_patterns = [
            r"product_price:\s*([0-9,]+(?:\.[0-9]+)?)",  # From metadata format
            r"Giá:\s*([0-9,]+(?:\.[0-9]+)?)",  # From content format
            r"price:\s*([0-9,]+(?:\.[0-9]+)?)",  # Alternative format
        ]

        price_found = False
        for pattern in price_patterns:
            price_match = re.search(pattern, content)
            if price_match:
                try:
                    # Remove commas and convert to float
                    price_str = price_match.group(1).replace(",", "")
                    price_value = float(price_str)

                    # If price seems too small (like 109), multiply by 1000
                    # This assumes prices under 1000 are in thousands
                    if price_value < 1000 and price_value > 0:
                        price_value *= 1000

                    product_info["product_price"] = price_value
                    price_found = True
                    break
                except ValueError:
                    continue

        # Extract price unit - try multiple patterns
        unit_patterns = [
            r'product_price_unit["\']:\s*["\']([^"\']+)["\']',  # From metadata JSON format
            r"Giá:\s*[0-9,]+(?:\.[0-9]+)?\s*([^|]+?)(?=\s*\||$)",  # After price in content
            r"/\s*([^|]+?)(?=\s*\||\s+product_url:|$)",  # Unit starting with /
        ]

        for pattern in unit_patterns:
            unit_match = re.search(pattern, content)
            if unit_match:
                unit = unit_match.group(1).strip()
                if unit and unit != "":
                    product_info["product_price_unit"] = unit
                    break

        # If no unit found but we see "/ Hộp" pattern, extract it
        if not product_info["product_price_unit"]:
            unit_match = re.search(
                r"/\s*(Hộp|Kg|Gói|Chai|Lon|Túi|Thùng)", content, re.IGNORECASE
            )
            if unit_match:
                product_info["product_price_unit"] = f"/ {unit_match.group(1)}"

        # Extract product URL
        url_patterns = [r"product_url:\s*([^|\s]+)", r"url:\s*([^|\s]+)"]

        for pattern in url_patterns:
            url_match = re.search(pattern, content)
            if url_match:
                product_info["product_url"] = url_match.group(1).strip()
                break

        # Extract image URL
        img_patterns = [r"image_url:\s*([^|\s]+)", r"img_url:\s*([^|\s]+)"]

        for pattern in img_patterns:
            img_match = re.search(pattern, content)
            if img_match:
                product_info["image_url"] = img_match.group(1).strip()
                break

    except Exception as e:
        logger.error(f"Error parsing optimized content: {e}")

    return product_info


# API Endpoints
@router.get("/", response_model=APIResponse)
async def root():
    """Root endpoint with API information"""
    return APIResponse(
        status="success",
        message="Enhanced Vector Database API is running",
        data={
            "version": "2.0.0",
            "features": [
                "bulk_insert",
                "url_ingestion",
                "file_upload",
                "csv_processing",
            ],
            "docs": "/docs",
        },
    )


@router.get("/documents/health", response_model=HealthResponse)
async def get_health_status(
    collection_name: Optional[str] = Query(None, description="Collection name"),
    vector_db: QdrantVectorDatabase = Depends(get_vector_db),
):
    """Check vector database health and collection statistics"""
    try:
        client = vector_db._create_client()
        target_collection = collection_name or vector_db.collection_name

        # Ensure collection exists
        vector_db._create_collection(client, target_collection)
        collection_info = client.get_collection(target_collection)

        return HealthResponse(
            status="healthy",
            collection_name=target_collection,
            total_documents=collection_info.points_count,
            vector_size=collection_info.config.params.vectors.size,
            distance_metric=collection_info.config.params.vectors.distance.name,
        )

    except Exception as e:
        logger.error(f"Vector DB health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Vector database unhealthy: {str(e)}",
        )


async def bulk_insert_documents(
    request: BulkInsertRequest, vector_db: QdrantVectorDatabase = Depends(get_vector_db)
):
    """Bulk insert documents from various sources (data, URL, or file)"""
    start_time = time.time()

    try:
        logger.info(f"🔄 Processing bulk insert request from {request.source_type}")
        logger.info(f"Target collection: {request.collection_name}")

        # Process data ingestion based on source type
        documents = process_data_ingestion(
            source_type=request.source_type,
            data=request.data,
            url=request.url,
            file_path=request.file_path,
        )

        if not documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid documents found to insert",
            )

        logger.info(f"📄 Processing {len(documents)} documents")

        # Insert documents into vector database
        inserted_docs, duplicate_count = vector_db.add_new_documents(
            documents, request.collection_name
        )

        processing_time = time.time() - start_time

        summary = InsertionSummary(
            inserted_count=len(inserted_docs),
            duplicate_count=duplicate_count,
            total_processed=len(documents),
            processing_time=round(processing_time, 2),
            source_type=request.source_type,
        )

        logger.info(
            f"✅ Bulk insertion completed: {len(inserted_docs)} inserted, "
            f"{duplicate_count} duplicates, {processing_time:.2f}s"
        )

        return APIResponse(
            status="success",
            message=f"Successfully processed {len(documents)} documents from {request.source_type}",
            data=summary.dict(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in bulk insert: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk insert failed: {str(e)}",
        )


# 1. KIỂM TRA COLLECTION HIỆN TẠI
def debug_collection_status(vector_db: QdrantVectorDatabase, collection_name: str):
    """Debug collection status"""
    try:
        client = vector_db._create_client(read_only=True)

        # Kiểm tra collection có tồn tại không
        if not client.collection_exists(collection_name):
            print(f"❌ Collection '{collection_name}' không tồn tại!")
            return

        # Lấy thông tin collection
        collection_info = client.get_collection(collection_name)
        print(f"📊 Collection Info:")
        print(f"  - Name: {collection_name}")
        print(f"  - Points count: {collection_info.points_count}")
        print(f"  - Vector size: {collection_info.config.params.vectors.size}")
        print(f"  - Distance: {collection_info.config.params.vectors.distance}")

        # Lấy một vài sample points nếu có
        if collection_info.points_count > 0:
            result = client.scroll(
                collection_name=collection_name,
                limit=3,
                with_payload=True,
                with_vectors=False,
            )
            points, _ = result
            print(f"📝 Sample points:")
            for i, point in enumerate(points):
                print(f"  Point {i+1}: ID={point.id}")
                if point.payload:
                    print(f"    Text preview: {point.payload.get('text', '')[:100]}...")
        else:
            print("📪 Collection is empty!")

    except Exception as e:
        print(f"❌ Error checking collection: {e}")


# Fixed version of the upload_csv_file function
@router.post(
    "/documents/upload-csv",
    response_model=APIResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_csv_file(
    file: UploadFile = File(..., description="CSV file to upload"),
    collection_name: str = Query(..., description="Target collection name"),
    vector_db: QdrantVectorDatabase = Depends(get_vector_db),
):
    """Upload and process CSV file with proper price handling"""
    start_time = time.perf_counter()

    # Local fallback sanitizer in case vector_db doesn't expose it
    def _sanitize_metadata(m):
        try:
            return vector_db.sanitize_metadata(m or {})
        except Exception:
            import json

            out = {}
            for k, v in (m or {}).items():
                try:
                    json.dumps(v)
                    out[k] = v
                except Exception:
                    out[k] = str(v)
            return out

    def chunks(lst, n):
        """Yield successive n-sized chunks from list."""
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    def process_price_value(price_value):
        """Process price value to ensure correct format"""
        try:
            if isinstance(price_value, str):
                # Remove any commas or other formatting
                price_value = price_value.replace(",", "").replace(" ", "")
                price_float = float(price_value)
            else:
                price_float = float(price_value)

            # If price seems too small (like 109), multiply by 1000
            # This assumes prices under 1000 are in thousands (VND)
            if 0 < price_float < 1000:
                price_float *= 1000
                logger.info(f"Price adjusted from {price_value} to {price_float}")

            return price_float
        except (ValueError, TypeError):
            logger.warning(f"Could not process price value: {price_value}")
            return 0.0

    try:
        logger.info(f"=== Starting CSV upload to collection: {collection_name} ===")

        # Validate file
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only CSV files are supported",
            )

        # Read and decode content
        content = await file.read()
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file uploaded"
            )

        try:
            csv_string = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                csv_string = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                csv_string = content.decode("latin-1")

        # Parse CSV using your node parser
        node_parser = CSVNodeParser()
        raw_nodes = node_parser.parse_csv_content(csv_string, file.filename)

        logger.info(f"📊 Parsed {len(raw_nodes)} raw nodes from CSV: {file.filename}")

        if not raw_nodes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid data found in CSV file",
            )

        # Transform nodes with proper price handling
        from app.vector_db.nodes import TextNode as LocalTextNode
        import uuid as _uuid

        formatted_nodes: List[LocalTextNode] = []
        for i, node in enumerate(raw_nodes):
            meta_src = getattr(node, "metadata", {}) or {}

            product_category = meta_src.get("product_category", "")
            product_name = meta_src.get("product_name", "")
            raw_price = meta_src.get("product_price", 0)
            product_price_unit = meta_src.get("product_price_unit", "")
            product_url = meta_src.get("product_url", "")
            image_url = meta_src.get("image_url", "")

            # IMPORTANT: Process price properly
            processed_price = process_price_value(raw_price)

            # Log first few price conversions for debugging
            if i < 3:
                logger.info(
                    f"Row {i}: Raw price: {raw_price} -> Processed: {processed_price}"
                )

            # Create page_content with processed price
            page_content = (
                f"product_category: {product_category} | "
                f"product_name: {product_name} | "
                f"product_price: {processed_price} | "  # Use processed price
                f"product_price_unit: {product_price_unit} | "
                f"product_url: {product_url} | "
                f"image_url: {image_url}"
            )

            node_id = str(_uuid.uuid4())

            # Store both original and processed price in metadata
            meta = {
                "source": file.filename,
                "row": i,
                "product_name": product_name,
                "product_price": processed_price,  # Use processed price
                "product_price_original": raw_price,  # Keep original for reference
                "product_category": product_category,
                "product_url": product_url,
                "image_url": image_url,
                "product_price_unit": product_price_unit,
            }
            meta = _sanitize_metadata(meta)

            formatted_node = LocalTextNode(
                id_=node_id, text=page_content, metadata=meta, embedding=None
            )
            formatted_nodes.append(formatted_node)

        nodes = formatted_nodes
        total_nodes = len(nodes)
        logger.info(f"✨ Formatted {total_nodes} nodes with proper price handling")

        # Ensure collection exists
        client = vector_db._create_client(read_only=False)
        vector_db._create_collection(client, collection_name)

        # Ensure indexes
        try:
            await ensure_indexes(client, collection_name)
        except Exception as e:
            logger.warning(f"Could not ensure indexes: {e}")

        # Generate embeddings
        texts = [n.get_content(metadata_mode="embed") for n in nodes]
        embeddings = vector_db.embed_model.get_text_embeddings(texts)

        # Attach embeddings & validate
        valid_nodes = []
        for node, emb in zip(nodes, embeddings):
            try:
                emb_list = list(map(float, emb))
            except Exception:
                logger.warning(
                    f"Embedding for node {node.id_} cannot be cast to float list; skipping"
                )
                continue
            if len(emb_list) != vector_db.vector_size:
                logger.warning(
                    f"Embedding dim for node {node.id_} is {len(emb_list)}; expected {vector_db.vector_size}; skipping"
                )
                continue
            node.embedding = emb_list
            valid_nodes.append(node)

        if not valid_nodes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid nodes with embeddings to insert",
            )

        # Batching + progress logging (keep the same batching logic)
        batch_size = 200
        total_valid = len(valid_nodes)
        processed = 0
        inserted_total = 0
        duplicate_total = 0
        batch_index = 0
        start_upsert = time.perf_counter()

        logger.info(
            f"🔁 Starting upsert in batches: total={total_valid}, batch_size={batch_size}"
        )

        for batch in chunks(valid_nodes, batch_size):
            batch_index += 1
            batch_start = time.perf_counter()
            try:
                if hasattr(vector_db, "add_nodes_async"):
                    res = await vector_db.add_nodes_async(batch, collection_name)
                else:
                    res = vector_db.add_nodes(batch, collection_name)

                if isinstance(res, tuple) or isinstance(res, list):
                    ins_cnt, dup_cnt = res
                else:
                    ins_cnt, dup_cnt = (res, 0)
                inserted_total += int(ins_cnt)
                duplicate_total += int(dup_cnt)

            except Exception as e:
                logger.warning(
                    f"Batch upsert failed (batch {batch_index}): {e}; falling back to client.upsert"
                )
                # Fallback logic stays the same
                from qdrant_client.models import PointStruct

                points = []
                for n in batch:
                    points.append(
                        PointStruct(
                            id=n.id_,
                            vector=n.embedding,
                            payload={
                                "text": n.text,
                                "original_node_id": n.id_,
                                "metadata": _sanitize_metadata(n.metadata),
                            },
                        )
                    )
                try:
                    client.upsert(collection_name=collection_name, points=points)
                    inserted_total += len(points)
                except Exception as e2:
                    logger.error(
                        f"Fallback upsert failed for batch {batch_index}: {e2}"
                    )

            batch_end = time.perf_counter()
            processed += len(batch)

            # Progress logging
            elapsed = batch_end - start_upsert
            avg_per_item = elapsed / processed if processed else 0.0
            remaining = total_valid - processed
            eta_seconds = remaining * avg_per_item
            eta_str = (
                f"{int(eta_seconds)}s"
                if eta_seconds < 3600
                else f"{int(eta_seconds//60)}m{int(eta_seconds%60)}s"
            )

            logger.info(
                f"Batch {batch_index}: processed {processed}/{total_valid} "
                f"(+{len(batch)}). Batch time: {batch_end - batch_start:.2f}s. "
                f"Elapsed: {elapsed:.2f}s. Avg/item: {avg_per_item:.4f}s. ETA: {eta_str}."
            )

        total_time = time.perf_counter() - start_time
        logger.info(
            f"✅ Upload finished: inserted_total={inserted_total}, duplicate_total={duplicate_total}, "
            f"processed={total_valid}, total_time={total_time:.2f}s"
        )

        return APIResponse(
            status="success",
            message=f"Successfully processed and indexed {inserted_total} nodes from {file.filename}",
            data={
                "inserted_count": inserted_total,
                "duplicate_count": duplicate_total,
                "total_processed": total_valid,
                "collection_name": collection_name,
                "processing_time_seconds": round(total_time, 2),
                "filename": file.filename,
                "price_processing": "Applied automatic price conversion for values < 1000",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing CSV upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process CSV file: {str(e)}",
        )


@router.post(
    "/documents", response_model=APIResponse, status_code=status.HTTP_201_CREATED
)
async def insert_documents(
    docs: InputData, vector_db: QdrantVectorDatabase = Depends(get_vector_db)
):
    """Insert documents from direct data input (legacy endpoint)"""
    try:
        logger.info(f"Processing legacy documents insertion request")

        documents = DataIngestion(data=docs.data).reFormat()

        if not documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid documents found to insert",
            )

        inserted_docs, duplicate_count = vector_db.add_new_documents(
            documents, docs.collection_name
        )

        logger.info(
            f"Legacy insertion summary: {len(inserted_docs)} inserted, {duplicate_count} duplicates"
        )

        return APIResponse(
            status="success",
            message=f"Successfully inserted {len(inserted_docs)} documents",
            data={
                "inserted_count": len(inserted_docs),
                "duplicate_count": duplicate_count,
                "documents": inserted_docs,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inserting documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to insert documents: {str(e)}",
        )


@router.get("/documents", response_model=List[str])
async def get_list_document_ids(
    params: DocumentQueryParams = Depends(),
    vector_db: QdrantVectorDatabase = Depends(get_vector_db),
):
    """Retrieve a list of all document IDs in the collection"""
    try:
        client = vector_db._create_client()
        scroll_result = client.scroll(
            collection_name=params.collection_name or vector_db.collection_name,
            with_vectors=False,
            with_payload=False,
            limit=params.limit,
        )

        document_ids = [str(point.id) for point in scroll_result[0]]
        return document_ids

    except Exception as e:
        logger.error(f"Error retrieving document IDs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document IDs: {str(e)}",
        )


# Thêm vào file router của bạn (thay thế endpoint search hiện tại)


@router.post("/documents/search", response_model=FinalResponse)
async def search_documents(
    search_query: SearchQuery,
    use_hybrid: bool = Query(
        True, description="Use hybrid search (keyword + semantic)"
    ),
    vector_db: QdrantVectorDatabase = Depends(get_vector_db),
):
    """
    Tìm kiếm documents với hybrid search (improved version)
    """
    try:
        logger.info(
            f"🔍 Document search: '{search_query.query}' limit: {search_query.limit}"
        )

        client = vector_db._create_client()
        normalized_query = search_query.query.lower().strip()
        query_keywords = normalized_query.split()

        document_results = []

        if use_hybrid:
            # STEP 1: Keyword search trước (giống smart-search)
            logger.info("🎯 Starting keyword search phase...")

            scroll_result = client.scroll(
                collection_name=search_query.collection_name,
                with_payload=True,
                with_vectors=False,
                limit=5000,  # Lấy nhiều để filter
            )

            exact_matches = []
            partial_matches = []

            for point in scroll_result[0]:
                payload = point.payload
                metadata = payload.get("metadata", {})
                product_name = metadata.get("product_name", "").lower()
                text_content = payload.get("text", "").lower()

                # Exact phrase matching
                if normalized_query in product_name or normalized_query in text_content:
                    exact_matches.append(
                        {"point": point, "score": 1.0, "match_type": "exact_phrase"}
                    )
                else:
                    # Partial keyword matching
                    keyword_count = sum(
                        1
                        for keyword in query_keywords
                        if keyword in product_name or keyword in text_content
                    )
                    if keyword_count > 0:
                        relevance_score = keyword_count / len(query_keywords)
                        if (
                            relevance_score >= 0.3
                        ):  # Thấp hơn smart-search để lấy nhiều kết quả hơn
                            partial_matches.append(
                                {
                                    "point": point,
                                    "score": relevance_score,
                                    "match_type": "partial_keywords",
                                    "keyword_matches": keyword_count,
                                }
                            )

            # Combine keyword results
            keyword_results = exact_matches + partial_matches
            keyword_results.sort(key=lambda x: x["score"], reverse=True)

            logger.info(
                f"📊 Keyword search found: {len(exact_matches)} exact, {len(partial_matches)} partial"
            )

            # STEP 2: Semantic search nếu cần thêm kết quả
            if len(keyword_results) < search_query.limit:
                logger.info("🧠 Adding semantic search results...")

                embed_model = get_embed_model()
                query_embedding = embed_model.get_text_embeddings([search_query.query])[
                    0
                ]

                semantic_results = client.search(
                    collection_name=search_query.collection_name,
                    query_vector=query_embedding,
                    limit=search_query.limit * 2,  # Lấy thêm để filter trùng lặp
                    with_payload=True,
                    with_vectors=False,
                    score_threshold=0.1,  # Threshold rất thấp
                )

                # Tránh trùng lặp với keyword results
                existing_ids = {result["point"].id for result in keyword_results}

                for result in semantic_results:
                    if (
                        str(result.id) not in existing_ids
                        and len(keyword_results) < search_query.limit * 1.5
                    ):
                        keyword_results.append(
                            {
                                "point": result,
                                "score": result.score,
                                "match_type": "semantic",
                            }
                        )

                logger.info(
                    f"🔄 Total results after semantic boost: {len(keyword_results)}"
                )

            # Convert to final format
            for result_item in keyword_results[: search_query.limit]:
                point = result_item["point"]
                payload = point.payload
                document_results.append(
                    DocumentData(
                        content=payload.get("text", ""),
                        metadata=payload.get("metadata", {}),
                    )
                )

        else:
            # Pure semantic search (original logic)
            embed_model = get_embed_model()
            query_embedding = embed_model.get_text_embeddings([search_query.query])[0]

            search_results = client.search(
                collection_name=search_query.collection_name,
                query_vector=query_embedding,
                limit=search_query.limit,
                with_payload=True,
                with_vectors=False,
                score_threshold=0.1,  # Giảm threshold xuống
            )

            for result in search_results:
                payload = result.payload
                document_results.append(
                    DocumentData(
                        content=payload.get("text", ""),
                        metadata=payload.get("metadata", {}),
                    )
                )

        logger.info(f"✅ Final results: {len(document_results)} documents")

        return FinalResponse(
            result=document_results,
            total=len(document_results),
            limit=search_query.limit,
            query=search_query.query,
        )

    except Exception as e:
        logger.error(f"❌ Document search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document search failed: {str(e)}",
        )


# Endpoint để kiểm tra database có chứa keyword không


# Data validation and preview endpoints
@router.post("/data/validate", response_model=APIResponse)
async def validate_data_source(request: BulkInsertRequest):
    """
    Validate data source without inserting into database
    """
    try:
        logger.info(f"Validating data source: {request.source_type}")

        # Process data ingestion
        documents = process_data_ingestion(
            source_type=request.source_type,
            data=request.data,
            url=request.url,
            file_path=request.file_path,
        )

        if not documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid documents found in the data source",
            )

        # Extract sample data for preview
        sample_doc = documents[0] if documents else None
        sample_content = sample_doc.page_content[:200] + "..." if sample_doc else ""
        sample_metadata = sample_doc.metadata if sample_doc else {}

        return APIResponse(
            status="success",
            message=f"Data source validation successful",
            data={
                "total_documents": len(documents),
                "source_type": request.source_type,
                "sample_content": sample_content,
                "sample_metadata": sample_metadata,
                "validation_status": "passed",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating data source: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Data source validation failed: {str(e)}",
        )


# Collection management endpoints (keeping existing ones)
@router.get("/collections", response_model=List[str])
async def get_list_collection(vector_db: QdrantVectorDatabase = Depends(get_vector_db)):
    """Retrieve a list of all collection names in Qdrant"""
    try:
        client = vector_db._create_client()
        collections_info = client.get_collections()
        collection_names = [
            collection.name
            for collection in collections_info.collections
            if isinstance(collection, CollectionDescription)
        ]
        return collection_names
    except Exception as e:
        logger.error(f"Error retrieving collections list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve collections: {str(e)}",
        )


class CreateCollectionRequest(BaseModel):
    collection_name: str
    vector_size: int = 1536
    distance: str = "Cosine"


@router.post("/collections", status_code=status.HTTP_201_CREATED)
async def create_collection(
    request: CreateCollectionRequest,
    vector_db: QdrantVectorDatabase = Depends(get_vector_db),
):
    """Create a new collection in Qdrant"""
    try:
        client = vector_db._create_client()
        distance_enum = getattr(models.Distance, request.distance.upper())

        client.create_collection(
            collection_name=request.collection_name,
            vectors_config=models.VectorParams(
                size=request.vector_size,
                distance=distance_enum,
            ),
        )

        return {
            "message": f"Collection '{request.collection_name}' created successfully"
        }

    except Exception as e:
        logger.error(f"Error creating collection '{request.collection_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create collection: {str(e)}",
        )


@router.get("/collections/list", response_model=APIResponse)
async def list_collections(vector_db: QdrantVectorDatabase = Depends(get_vector_db)):
    """List all collections"""
    try:
        client = vector_db._create_client()
        collections = client.get_collections()

        collection_info = []
        for collection in collections.collections:
            try:
                info = client.get_collection(collection.name)
                collection_info.append(
                    {
                        "name": collection.name,
                        "points_count": info.points_count,
                        "vector_size": info.config.params.vectors.size,
                        "distance": info.config.params.vectors.distance.name,
                    }
                )
            except Exception as e:
                logger.warning(
                    f"Could not get info for collection {collection.name}: {e}"
                )
                collection_info.append(
                    {
                        "name": collection.name,
                        "points_count": "unknown",
                        "vector_size": "unknown",
                        "distance": "unknown",
                    }
                )

        return APIResponse(
            status="success",
            message=f"Found {len(collection_info)} collections",
            data={"collections": collection_info},
        )

    except Exception as e:
        logger.error(f"❌ Error listing collections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collections: {str(e)}",
        )


@router.delete("/collections/{collection_name}", response_model=APIResponse)
async def delete_collection(
    collection_name: str,
    confirm: bool = Query(False, description="Confirm deletion"),
    vector_db: QdrantVectorDatabase = Depends(get_vector_db),
):
    """Delete a collection"""
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must set confirm=true to delete collection",
        )

    try:
        client = vector_db._create_client()

        # Check if collection exists
        try:
            collection_info = client.get_collection(collection_name)
            points_count = collection_info.points_count
        except:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found",
            )

        # Delete collection
        client.delete_collection(collection_name)

        logger.info(
            f"🗑️ Deleted collection '{collection_name}' with {points_count} points"
        )

        return APIResponse(
            status="success",
            message=f"Successfully deleted collection '{collection_name}' with {points_count} points",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete collection: {str(e)}",
        )


@router.get("/collections/{collection_name}/info", response_model=APIResponse)
async def get_collection_info(
    collection_name: str, vector_db: QdrantVectorDatabase = Depends(get_vector_db)
):
    """Get detailed information about a collection"""
    try:
        client = vector_db._create_client()

        try:
            collection_info = client.get_collection(collection_name)
        except:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection '{collection_name}' not found",
            )

        # Get sample points
        sample_points = []
        try:
            scroll_result = client.scroll(
                collection_name=collection_name,
                limit=3,
                with_payload=True,
                with_vectors=False,
            )

            for point in scroll_result[0]:
                sample_points.append(
                    {
                        "id": str(point.id),
                        "payload_keys": (
                            list(point.payload.keys()) if point.payload else []
                        ),
                    }
                )
        except Exception as e:
            logger.warning(f"Could not get sample points: {e}")

        info = {
            "name": collection_name,
            "points_count": collection_info.points_count,
            "vector_size": collection_info.config.params.vectors.size,
            "distance": collection_info.config.params.vectors.distance.name,
            "indexed_vectors_count": collection_info.indexed_vectors_count,
            "sample_points": sample_points,
        }

        return APIResponse(
            status="success",
            message=f"Collection '{collection_name}' information",
            data=info,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting collection info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get collection info: {str(e)}",
        )


# Product
async def ensure_indexes(client, collection_name: str):
    """
    Ensure necessary indexes exist for filtering
    """
    try:
        # Tạo index cho product_category
        client.create_payload_index(
            collection_name=collection_name,
            field_name="product_category",
            field_type=PayloadSchemaType.KEYWORD,
        )
        logger.info(f"Created index for product_category in {collection_name}")
    except Exception as e:
        logger.warning(f"Index for product_category might already exist: {e}")

    try:
        # Tạo index cho product_price
        client.create_payload_index(
            collection_name=collection_name,
            field_name="product_price",
            field_type=PayloadSchemaType.FLOAT,
        )
        logger.info(f"Created index for product_price in {collection_name}")
    except Exception as e:
        logger.warning(f"Index for product_price might already exist: {e}")


# debug
# Enhanced debug endpoint for checking data
@router.get("/debug/collection/{collection_name}", response_model=APIResponse)
async def debug_collection_data(
    collection_name: str,
    limit: int = Query(5, description="Number of points to sample"),
    vector_db: QdrantVectorDatabase = Depends(get_vector_db),
):
    """
    Debug endpoint to check what's actually in the collection
    """
    try:
        client = vector_db._create_client()

        # Get collection info
        collection_info = client.get_collection(collection_name)
        logger.info(f"Collection info: {collection_info}")

        # Get sample points
        scroll_result = client.scroll(
            collection_name=collection_name,
            with_vectors=False,
            with_payload=True,
            limit=limit,
        )

        sample_data = []
        for point in scroll_result[0]:
            sample_data.append(
                {
                    "id": str(point.id),
                    "payload_keys": list(point.payload.keys()) if point.payload else [],
                    "payload_sample": {
                        k: str(v)[:100] for k, v in (point.payload or {}).items()
                    },
                }
            )

        debug_info = {
            "collection_name": collection_name,
            "total_points": collection_info.points_count,
            "vector_size": collection_info.config.params.vectors.size,
            "distance_metric": collection_info.config.params.vectors.distance.name,
            "sample_points": sample_data,
        }

        return APIResponse(
            status="success",
            message=f"Debug info for collection '{collection_name}'",
            data=debug_info,
        )

    except Exception as e:
        logger.error(f"Error getting debug info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debug failed: {str(e)}",
        )


@router.get("/debug/status", response_model=APIResponse)
async def get_debug_status():
    """Get detailed status of all components"""
    status_info = {
        "vector_db_available": app_state.get("vector_db") is not None,
        "llm_available": app_state.get("llm") is not None,
        "embed_model_available": app_state.get("embed_model") is not None,
        "metadata_available": app_state.get("metadata") is not None,
    }

    return APIResponse(
        status="success", message="Debug status information", data=status_info
    )


@router.get("/products/debug", response_model=dict)
async def debug_product_data(
    collection_name: Optional[str] = Query(None, description="Collection name"),
    vector_db: QdrantVectorDatabase = Depends(get_vector_db),
):
    """
    Debug endpoint để kiểm tra cấu trúc dữ liệu
    """
    try:
        client = vector_db._create_client()
        collection = collection_name or vector_db.collection_name

        # Lấy 1 point để kiểm tra cấu trúc
        scroll_result = client.scroll(
            collection_name=collection, with_vectors=False, with_payload=True, limit=1
        )

        if scroll_result[0]:
            point = scroll_result[0][0]
            return {
                "point_id": str(point.id),
                "payload_keys": list(point.payload.keys()) if point.payload else [],
                "payload": point.payload,
            }
        else:
            return {"message": "No points found"}

    except Exception as e:
        logger.error(f"Debug error: {e}")
        return {"error": str(e)}
