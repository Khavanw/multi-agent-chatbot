import logging
import traceback
from typing import Any, Dict, List, Tuple
import re
import json
from datetime import datetime

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class QueryRetriever:
    """
    Enhanced QueryRetriever với hybrid search strategy từ /documents/search
    Kết hợp keyword search + semantic search để độ chính xác cao hơn
    """

    def __init__(
        self,
        llm,
        vectordb,
        metadata_handler,
        embed_model,
        collection_name="dat614943",
        top_k=10,
    ):
        self.llm = llm
        self.vector_store = vectordb
        self.embed_model = embed_model
        self.metadata_handler = metadata_handler
        self.collection_name = collection_name
        self.top_k = top_k

        # Create Qdrant client
        self.client = self.vector_store._create_client()

        # Initialize with error handling
        self._initialize_with_error_handling()

    def _initialize_with_error_handling(self):
        """Khởi tạo với xử lý lỗi"""
        try:
            client = self.vector_store._create_client(read_only=True)
            collection_exists = client.collection_exists(self.collection_name)

            if not collection_exists:
                raise Exception(f"Collection {self.collection_name} không tồn tại")

            logger.info(
                f"✅ Enhanced QueryRetriever initialized for collection: {self.collection_name}"
            )

        except Exception as e:
            logger.error(f"❌ Enhanced QueryRetriever initialization warning: {e}")

    def invoke_query(
        self, query: str, collection_name: str = None, use_hybrid: bool = True
    ) -> List[Dict[str, Any]]:
        """
        ENHANCED: Execute hybrid search với keyword + semantic search
        """
        try:
            target_collection = collection_name or self.collection_name
            logger.info(
                f"🔍 ENHANCED hybrid search: '{query}' on collection: {target_collection}"
            )

            if target_collection != self.collection_name:
                self.collection_name = target_collection

            if use_hybrid:
                return self._hybrid_search_enhanced(query, target_collection)
            else:
                return self._direct_semantic_search(query, target_collection)

        except Exception as e:
            logger.error(f"❌ Enhanced query methods failed: {e}")
            return []

    def _hybrid_search_enhanced(
        self, query: str, collection_name: str
    ) -> List[Dict[str, Any]]:
        """
        ENHANCED: Hybrid search strategy từ /documents/search
        """
        try:
            logger.info(f"🎯 Starting ENHANCED hybrid search for: '{query}'")

            client = self.vector_store._create_client(read_only=True)
            normalized_query = query.lower().strip()
            query_keywords = normalized_query.split()

            # STEP 1: KEYWORD SEARCH PHASE (ưu tiên cao nhất)
            logger.info("🎯 Phase 1: Keyword search...")

            # Scroll through collection để keyword matching
            scroll_result = client.scroll(
                collection_name=collection_name,
                with_payload=True,
                with_vectors=False,
                limit=3000,  # Tăng limit để tìm nhiều hơn
            )

            exact_matches = []
            partial_matches = []
            token_matches = []

            for point in scroll_result[0]:
                payload = point.payload
                metadata = payload.get("metadata", {})

                # Extract product info
                product_name = metadata.get("product_name", "").lower()
                product_category = metadata.get("product_category", "").lower()
                text_content = payload.get("text", "").lower()

                # 1. EXACT PHRASE MATCHING (highest priority)
                if (
                    normalized_query in product_name
                    or normalized_query in text_content
                    or normalized_query in product_category
                ):
                    exact_matches.append(
                        {
                            "point": point,
                            "score": 1.0,
                            "match_type": "exact_phrase",
                            "product_name": metadata.get("product_name", "Unknown"),
                        }
                    )

                # 2. PARTIAL KEYWORD MATCHING
                else:
                    all_text = f"{product_name} {product_category} {text_content}"
                    keyword_count = sum(
                        1 for keyword in query_keywords if keyword in all_text
                    )

                    if keyword_count > 0:
                        relevance_score = keyword_count / len(query_keywords)

                        if relevance_score >= 0.5:  # High threshold cho partial
                            partial_matches.append(
                                {
                                    "point": point,
                                    "score": relevance_score
                                    + 0.1,  # Boost partial matches
                                    "match_type": "partial_keywords",
                                    "keyword_matches": keyword_count,
                                    "product_name": metadata.get(
                                        "product_name", "Unknown"
                                    ),
                                }
                            )
                        elif (
                            relevance_score >= 0.3
                        ):  # Medium threshold cho token matching
                            # 3. TOKEN-BASED MATCHING (sử dụng product_name_tokens nếu có)
                            tokens = metadata.get("product_name_tokens", [])
                            if tokens:
                                token_overlap = len(set(query_keywords) & set(tokens))
                                if token_overlap > 0:
                                    token_score = token_overlap / len(query_keywords)
                                    token_matches.append(
                                        {
                                            "point": point,
                                            "score": token_score,
                                            "match_type": "token_overlap",
                                            "token_matches": token_overlap,
                                            "product_name": metadata.get(
                                                "product_name", "Unknown"
                                            ),
                                        }
                                    )

            # Combine và sort keyword results
            keyword_results = exact_matches + partial_matches + token_matches
            keyword_results.sort(
                key=lambda x: (x["score"], x["match_type"] == "exact_phrase"),
                reverse=True,
            )

            logger.info(
                f"📊 Keyword phase: {len(exact_matches)} exact, "
                f"{len(partial_matches)} partial, {len(token_matches)} token matches"
            )

            # STEP 2: SEMANTIC SEARCH nếu cần thêm kết quả
            final_results = keyword_results[: self.top_k]

            if len(final_results) < self.top_k:
                logger.info("🧠 Phase 2: Adding semantic search...")

                query_embedding = self.embed_model.embed_query(query)

                semantic_results = client.search(
                    collection_name=collection_name,
                    query_vector=query_embedding,
                    limit=self.top_k * 2,
                    with_payload=True,
                    with_vectors=False,
                    score_threshold=0.2,  # Reasonable threshold
                )

                # Tránh trùng lặp với keyword results
                existing_ids = {str(result["point"].id) for result in keyword_results}

                for result in semantic_results:
                    if (
                        str(result.id) not in existing_ids
                        and len(final_results) < self.top_k
                    ):
                        metadata = result.payload.get("metadata", {})
                        final_results.append(
                            {
                                "point": result,
                                "score": result.score,
                                "match_type": "semantic",
                                "product_name": metadata.get("product_name", "Unknown"),
                            }
                        )

                logger.info(f"🔄 Added semantic results, total: {len(final_results)}")

            # STEP 3: Convert to serializable format
            serializable_results = []
            for i, result_item in enumerate(final_results[: self.top_k]):
                point = result_item["point"]

                if hasattr(point, "payload") and point.payload:
                    product_name = self._extract_product_name_flexible(point.payload)

                    if product_name and product_name != "Unknown Product":
                        result_dict = {
                            "page_content": product_name,
                            "metadata": self._clean_metadata_serializable(
                                point.payload
                            ),
                            "score": float(result_item["score"]),
                            "match_type": result_item["match_type"],
                            "id": str(point.id),
                            "rank": i + 1,
                        }

                        serializable_results.append(result_dict)

            logger.info(
                f"✅ ENHANCED hybrid search: {len(serializable_results)} results"
            )
            return serializable_results

        except Exception as e:
            logger.error(f"❌ Enhanced hybrid search failed: {e}")
            logger.error(f"❌ Traceback:\n{traceback.format_exc()}")
            return self._direct_semantic_search(query, collection_name)

    def _direct_semantic_search(
        self, query: str, collection_name: str
    ) -> List[Dict[str, Any]]:
        """
        Fallback: Pure semantic search
        """
        try:
            logger.info(f"🧠 Semantic search fallback for: '{query}'")

            query_embedding = self.embed_model.embed_query(query)
            client = self.vector_store._create_client(read_only=True)

            search_results = client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=self.top_k,
                with_payload=True,
                with_vectors=False,
                score_threshold=0.1,
            )

            # Convert to serializable format
            serializable_results = []
            for i, hit in enumerate(search_results):
                if hit.payload:
                    product_name = self._extract_product_name_flexible(hit.payload)

                    if product_name:
                        result_dict = {
                            "page_content": product_name,
                            "metadata": self._clean_metadata_serializable(hit.payload),
                            "score": float(hit.score),
                            "match_type": "semantic_fallback",
                            "id": str(hit.id),
                            "rank": i + 1,
                        }

                        serializable_results.append(result_dict)

            logger.info(f"✅ Semantic fallback: {len(serializable_results)} results")
            return serializable_results

        except Exception as e:
            logger.error(f"❌ Semantic search failed: {e}")
            return []

    def _extract_product_name_flexible(self, payload: dict) -> str:
        """Extract product name from payload - ENHANCED"""
        try:
            # Priority 1: nested metadata
            if isinstance(payload, dict):
                meta = (
                    payload.get("metadata")
                    if isinstance(payload.get("metadata"), dict)
                    else payload
                )

                # Thử nhiều field names
                for key in ("product_name", "name", "title", "product_title"):
                    if meta and key in meta and meta[key]:
                        name = str(meta[key]).strip()
                        if len(name) > 2:  # Valid name
                            return name

            # Priority 2: parse from text field với better regex
            text = payload.get("text") if isinstance(payload.get("text"), str) else None
            if text:
                # Pattern 1: "product_name: value"
                patterns = [
                    r"product_name[:\-]\s*([^|;,\n]+)",
                    r"tên sản phẩm[:\-]\s*([^|;,\n]+)",
                    r"^([^:|\n]+)(?:\s*:|\s*\|)",  # First part before : or |
                ]

                for pattern in patterns:
                    m = re.search(pattern, text, flags=re.IGNORECASE)
                    if m:
                        name = m.group(1).strip()
                        if 3 <= len(name) <= 100:  # Reasonable length
                            return name

                # Fallback: first meaningful line
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                for line in lines[:3]:
                    if (
                        5 <= len(line) <= 100
                        and not line.startswith("http")
                        and not line.isdigit()
                        and ":" not in line[:10]
                    ):  # Not metadata line
                        return line

        except Exception as e:
            logger.warning(f"⚠️ Product name extraction failed: {e}")

        return "Unknown Product"

    def _clean_metadata_serializable(self, payload: dict) -> dict:
        """Clean metadata và return serializable data - ENHANCED"""
        metadata = {}

        # Enhanced field mapping
        field_mapping = {
            "product_name": ["product_name", "name", "title", "product_title"],
            "product_price": ["product_price", "price", "cost", "gia"],
            "product_category": ["product_category", "category", "type", "danh_muc"],
            "product_url": ["product_url", "url", "link", "product_link"],
            "image_url": ["image_url", "img_url", "photo_url", "image"],
            "product_price_unit": [
                "product_price_unit",
                "unit",
                "price_unit",
                "don_vi",
            ],
            "description": ["description", "desc", "mo_ta"],
            "availability": ["availability", "in_stock", "co_san"],
        }

        # Extract with enhanced conversion
        source_data = payload.get("metadata", {}) or payload

        for target_field, possible_keys in field_mapping.items():
            for key in possible_keys:
                if key in source_data and source_data[key] is not None:
                    value = source_data[key]

                    # Special processing for price
                    if target_field == "product_price":
                        try:
                            if isinstance(value, str):
                                # Remove currency symbols and non-digits
                                clean_price = re.sub(r"[^\d.]", "", value)
                                metadata[target_field] = (
                                    float(clean_price) if clean_price else 0.0
                                )
                            else:
                                metadata[target_field] = float(value)
                        except (ValueError, TypeError):
                            metadata[target_field] = 0.0

                    # Special processing for boolean fields
                    elif target_field == "availability":
                        if isinstance(value, str):
                            metadata[target_field] = value.lower() not in [
                                "false",
                                "0",
                                "no",
                                "không",
                            ]
                        else:
                            metadata[target_field] = bool(value)

                    else:
                        # Standard string conversion
                        metadata[target_field] = str(value).strip() if value else ""

                    break

        # Set enhanced defaults
        defaults = {
            "product_name": "Unknown Product",
            "product_price": 0.0,
            "product_category": "Thực phẩm",
            "product_price_unit": "/ kg",
            "product_url": "",
            "image_url": "",
            "description": "",
            "availability": True,
        }

        for key, default_value in defaults.items():
            metadata.setdefault(key, default_value)

        return metadata


# ==================== ENHANCED FACTORY FUNCTIONS ====================
def ensure_serializable(data: Any) -> Any:
    """
    Ensure data is JSON serializable by converting problematic types
    """
    try:
        if data is None:
            return None

        elif isinstance(data, (str, int, float, bool)):
            return data

        elif isinstance(data, datetime):
            return data.isoformat()

        elif isinstance(data, dict):
            return {str(k): ensure_serializable(v) for k, v in data.items()}

        elif isinstance(data, (list, tuple)):
            return [ensure_serializable(item) for item in data]

        elif isinstance(data, set):
            return [ensure_serializable(item) for item in data]

        elif hasattr(data, "__dict__"):
            # Handle objects with attributes
            return ensure_serializable(data.__dict__)

        elif hasattr(data, "to_dict"):
            # Handle objects with to_dict method
            return ensure_serializable(data.to_dict())

        elif hasattr(data, "_asdict"):
            # Handle namedtuples
            return ensure_serializable(data._asdict())

        else:
            # Convert to string as last resort
            try:
                # Test if it's already serializable
                json.dumps(data)
                return data
            except (TypeError, ValueError):
                return str(data)

    except Exception as e:
        logger.warning(f"⚠️ Serialization warning for {type(data)}: {e}")
        return str(data)


def extract_product_info_enhanced_hybrid(
    content: str, query_service: QueryRetriever, auto_service, use_hybrid: bool = True
) -> Dict[str, Any]:
    """
    ENHANCED: Product extraction với hybrid search
    """
    try:
        logger.info(f"🔍 ENHANCED HYBRID Extraction: '{content}'")

        # Step 1: Enhanced hybrid search
        search_results = query_service.invoke_query(content, use_hybrid=use_hybrid)

        if not search_results:
            logger.warning("⚠️ No search results, using fallback")
            return create_enhanced_fallback_product_info(content, "No search results")

        logger.info(f"📊 Enhanced search results: {len(search_results)}")

        # Log match type distribution
        match_types = {}
        for result in search_results[:5]:
            match_type = result.get("match_type", "unknown")
            match_types[match_type] = match_types.get(match_type, 0) + 1
        logger.info(f"🎯 Match distribution: {match_types}")

        # Step 2: Extract from best result
        try:
            if hasattr(auto_service, "extract_product_from_results"):
                extracted_info = auto_service.extract_product_from_results(
                    content, search_results
                )
            else:
                best_result = search_results[0]
                extracted_info = extract_from_best_result_enhanced(best_result, content)
        except Exception as extraction_error:
            logger.warning(f"⚠️ Auto service extraction failed: {extraction_error}")
            best_result = search_results[0] if search_results else {}
            extracted_info = extract_from_best_result_enhanced(best_result, content)

        # Step 3: Add enhanced metadata
        extracted_info.update(
            {
                "original_text": content,
                "extraction_method": "enhanced_hybrid_search",
                "search_strategy": "hybrid" if use_hybrid else "semantic",
                "results_count": len(search_results),
                "vector_search_used": True,
                "match_type": (
                    search_results[0].get("match_type", "unknown")
                    if search_results
                    else "none"
                ),
                "search_confidence": (
                    search_results[0].get("score", 0) if search_results else 0
                ),
                "debug_info": {
                    "top_matches": [
                        {
                            "rank": r.get("rank", i + 1),
                            "product_name": r.get("page_content", "N/A"),
                            "score": r.get("score", 0),
                            "match_type": r.get("match_type", "unknown"),
                        }
                        for i, r in enumerate(search_results[:3])
                    ],
                    "match_distribution": match_types,
                },
            }
        )

        logger.info(
            f"✅ ENHANCED Extraction completed: {extracted_info['product_name']} "
            f"(confidence: {extracted_info.get('search_confidence', 0):.3f}, "
            f"method: {extracted_info.get('match_type', 'unknown')})"
        )

        return extracted_info

    except Exception as e:
        logger.error(f"❌ Enhanced extraction failed: {str(e)}")
        logger.error(f"❌ Traceback:\n{traceback.format_exc()}")
        return create_enhanced_fallback_product_info(content, str(e))


def extract_from_best_result_enhanced(best_result, content: str) -> Dict[str, Any]:
    """Extract product info from best result - ENHANCED"""
    try:
        # Handle both dict and object results
        if isinstance(best_result, dict):
            page_content = best_result.get("page_content", "Unknown Product")
            metadata = best_result.get("metadata", {})
            match_type = best_result.get("match_type", "unknown")
            score = best_result.get("score", 0.0)
        else:
            page_content = getattr(best_result, "page_content", "Unknown Product")
            metadata = getattr(best_result, "metadata", {})
            match_type = getattr(best_result, "match_type", "unknown")
            score = getattr(best_result, "score", 0.0)

        # Extract quantity from content với better patterns
        quantity, unit = extract_quantity_and_unit_enhanced(content)

        # Get price info with better handling
        product_price = float(metadata.get("product_price", 50000))
        product_price_unit = metadata.get("product_price_unit", "/ kg")

        # Unit conversion for total calculation
        if unit == "g" and "kg" in product_price_unit:
            calculated_price = product_price * (quantity / 1000)  # Convert g to kg
        elif unit == "kg" and "g" in product_price_unit:
            calculated_price = product_price * (quantity * 1000)  # Convert kg to g
        else:
            calculated_price = product_price * quantity

        return {
            "product_name": str(page_content),
            "quantity": float(quantity),
            "unit": str(unit),
            "unit_price": float(product_price),
            "total_amount": float(calculated_price),
            "product_category": str(metadata.get("product_category", "Thực phẩm")),
            "product_url": str(metadata.get("product_url", "")),
            "image_url": str(metadata.get("image_url", "")),
            "product_price_unit": str(product_price_unit),
            "description": str(metadata.get("description", "")),
            "availability": bool(metadata.get("availability", True)),
            # Enhanced metadata
            "match_type": str(match_type),
            "search_confidence": float(score),
            "unit_conversion_applied": unit != unit.lower()
            or ("kg" in product_price_unit and unit == "g"),
        }

    except Exception as e:
        logger.error(f"❌ Error extracting from enhanced result: {e}")
        return create_enhanced_fallback_product_info(content, str(e))


def extract_quantity_and_unit_enhanced(content: str) -> Tuple[float, str]:
    """Extract quantity and unit from content - ENHANCED"""
    try:
        # Enhanced patterns với Vietnamese support
        quantity_patterns = [
            # Standard patterns
            r"(\d+(?:[.,]\d+)?)\s*(kg|kí|ký|kilogram|kilo)",
            r"(\d+(?:[.,]\d+)?)\s*(g|gram|gam|gr)",
            r"(\d+(?:[.,]\d+)?)\s*(cái|con|quả|trái|chiếc|hộp|khay|gói)",
            r"(\d+(?:[.,]\d+)?)\s*(lít|lit|l|ml|mililit)",
            # Vietnamese quantity words
            r"(một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười)\s*(kg|kí|ký|g|gram|cái|con|quả)",
            # Fractional patterns
            r"(\d+[.,]\d+)\s*(kg|g|cái|lít)",
            # Range patterns (take first number)
            r"(\d+)[-–]\d+\s*(kg|g|cái)",
        ]

        # Vietnamese number mapping
        viet_numbers = {
            "một": 1,
            "hai": 2,
            "ba": 3,
            "bốn": 4,
            "năm": 5,
            "sáu": 6,
            "bảy": 7,
            "tám": 8,
            "chín": 9,
            "mười": 10,
        }

        content_lower = content.lower().replace(",", ".")  # Normalize decimal separator

        for pattern in quantity_patterns:
            match = re.search(pattern, content_lower)
            if match:
                quantity_str = match.group(1)
                unit_raw = match.group(2)

                # Convert Vietnamese numbers
                if quantity_str in viet_numbers:
                    quantity = float(viet_numbers[quantity_str])
                else:
                    try:
                        quantity = float(quantity_str)
                    except ValueError:
                        continue

                # Enhanced unit normalization
                unit_map = {
                    "kg": "kg",
                    "kí": "kg",
                    "ký": "kg",
                    "kilogram": "kg",
                    "kilo": "kg",
                    "g": "g",
                    "gram": "g",
                    "gam": "g",
                    "gr": "g",
                    "cái": "cái",
                    "con": "cái",
                    "quả": "cái",
                    "trái": "cái",
                    "chiếc": "cái",
                    "hộp": "hộp",
                    "khay": "khay",
                    "gói": "gói",
                    "lít": "lít",
                    "lit": "lít",
                    "l": "lít",
                    "ml": "ml",
                    "mililit": "ml",
                }

                unit = unit_map.get(unit_raw, unit_raw)

                # Validate reasonable quantities
                if unit == "kg" and quantity > 50:  # Too much kg
                    quantity = quantity / 1000  # Might be in grams
                elif unit == "g" and quantity > 10000:  # Too much grams
                    continue  # Skip unreasonable

                return quantity, unit

        # Fallback: look for standalone numbers
        numbers = re.findall(r"\b(\d+(?:[.,]\d+)?)\b", content_lower)
        if numbers:
            try:
                quantity = float(numbers[0].replace(",", "."))
                if 0.1 <= quantity <= 20:  # Reasonable range for food
                    return quantity, "kg"
            except ValueError:
                pass

        # Default
        return 1.0, "kg"

    except Exception as e:
        logger.warning(f"⚠️ Enhanced quantity extraction failed: {e}")
        return 1.0, "kg"


def create_enhanced_fallback_product_info(
    content: str, error_msg: str
) -> Dict[str, Any]:
    """Create enhanced fallback product info"""
    quantity, unit = extract_quantity_and_unit_enhanced(content)

    return {
        "product_name": "Sản phẩm không xác định",
        "quantity": quantity,
        "unit": unit,
        "unit_price": 50000.0,
        "total_amount": 50000.0 * quantity,
        "product_category": "Thực phẩm",
        "product_url": "",
        "image_url": "",
        "product_price_unit": "/ kg",
        "description": "",
        "availability": True,
        # Enhanced metadata
        "original_text": content,
        "extraction_method": "enhanced_fallback",
        "error": error_msg,
        "vector_search_used": False,
        "match_type": "fallback",
        "search_confidence": 0.0,
        "unit_conversion_applied": False,
    }


# ==================== FACTORY FUNCTION TO REPLACE ORIGINAL ====================


def create_enhanced_query_service(vector_db, llm, embed_model, metadata_handler):
    """Create enhanced query service"""
    try:
        service = QueryRetriever(
            llm=llm,
            vectordb=vector_db,
            metadata_handler=metadata_handler,
            embed_model=embed_model,
            collection_name="dat614943",
            top_k=10,
        )
        logger.info("✅ Enhanced QueryRetriever service created")
        return service

    except Exception as e:
        logger.error(f"❌ Failed to create Enhanced QueryRetriever service: {e}")
        raise
