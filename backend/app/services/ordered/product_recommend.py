import difflib
import logging
import re
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

from app.db.models.recommendation import ProductRecommendation, RecommendationRequest

logger = logging.getLogger(__name__)


# ---------------------- Recommendation Service ----------------------
class ProductRecommendationService:
    """Enhanced recommendation service with better diversity and deduplication logic."""

    def __init__(
        self,
        vector_db,
        embed_model,
        connection_string: str,
        query_service=None,
        default_collection: str = "dat_614943",
    ):
        self.vector_db = vector_db
        self.embed_model = embed_model
        self.connection_string = connection_string
        self.query_service = query_service
        self.default_collection = default_collection

        self.config = {
            "similarity_threshold": 0.55,
            "max_price_ratio": 2.0,
            "min_price_ratio": 0.3,
            "diversity_factor": 0.7,
            "default_limit": 6,
            # Enhanced diversity settings
            "product_similarity_threshold": 0.85,  # Lower = more strict deduplication
            "max_same_base_product": 2,  # Maximum same base product variants
            "diversity_boost_factor": 1.2,  # Boost score for diverse products
        }

        # Enhanced complementary mapping with more diverse products
        self.complementary_mapping = {
            # Thịt và gia cầm - nhiều loại gia vị và rau củ đa dạng
            "thịt": [
                "gừng",
                "tỏi",
                "hành lá",
                "cà chua",
                "cà rót",
                "nấm",
                "rau thơm",
                "tiêu",
                "chanh",
            ],
            "thịt gà": [
                "gừng",
                "lá chanh",
                "sả",
                "nấm",
                "cà rót",
                "tiêu",
                "rau răm",
                "tỏi",
            ],
            "thịt heo": [
                "gừng",
                "tỏi",
                "hành lá",
                "dưa chua",
                "cà chua",
                "tiêu",
                "chanh",
            ],
            "thịt bò": [
                "gừng",
                "hành tây",
                "cà rót",
                "nấm",
                "rau muống",
                "tỏi",
                "tiêu",
            ],
            "gà": ["gừng", "lá chanh", "sả", "nấm", "cà rót", "tiêu", "rau răm", "tỏi"],
            "heo": ["gừng", "tỏi", "hành lá", "dưa chua", "cà chua", "tiêu", "chanh"],
            "bò": ["gừng", "hành tây", "cà rót", "nấm", "rau muống", "tỏi", "tiêu"],
            "sườn": ["gừng", "tỏi", "dưa chua", "cà chua", "hành tây", "tiêu"],
            "ức gà": ["gừng", "nấm", "bông cải xanh", "cà rót", "sả", "tiêu"],
            # Cá và hải sản - gia vị khử tanh và rau ăn kèm
            "cá": [
                "gừng",
                "tiêu",
                "chanh",
                "lá chanh",
                "thơm",
                "cà chua",
                "dưa chua",
                "rau thơm",
            ],
            "tôm": [
                "gừng",
                "tiêu",
                "chanh",
                "thơm",
                "cà chua",
                "bầu",
                "đậu bắp",
                "tỏi",
            ],
            "cua": ["gừng", "tiêu", "chanh", "bầu", "cà chua", "hành lá", "rau thơm"],
            "hải sản": [
                "gừng",
                "tiêu",
                "chanh",
                "lá chanh",
                "thơm",
                "cà chua",
                "rau thơm",
            ],
            "tép": ["gừng", "tiêu", "chanh", "thơm", "cà chua", "bầu", "đậu bắp"],
            "mực": ["gừng", "tiêu", "chanh", "thơm", "cà chua", "hành tây", "rau thơm"],
            # Rau củ - protein và gia vị
            "rau muống": ["thịt bò", "tôm", "tỏi", "gừng", "tiêu"],
            "bắp cải": ["thịt heo", "cà rót", "hành tây", "gừng", "tỏi"],
            "cà rót": ["thịt bò", "thịt gà", "cà chua", "hành tây", "gừng", "tỏi"],
            "cà chua": ["thịt", "cá", "tôm", "trứng", "hành tây", "gừng", "tỏi"],
            "khoai tây": ["thịt gà", "thịt heo", "cà rót", "hành tây", "gừng"],
            "hành tây": ["thịt bò", "thịt heo", "cà rót", "cà chua", "gừng", "tỏi"],
            "nấm": ["thịt gà", "thịt bò", "tôm", "cà rót", "gừng", "tỏi"],
            "bông cải xanh": ["thịt bò", "tôm", "nấm", "gừng", "tỏi"],
            # Gia vị và rau thơm
            "gừng": ["thịt", "cá", "tôm", "gà", "rau"],
            "tiêu": ["thịt", "cá", "tôm", "gà", "rau"],
            "chanh": ["cá", "tôm", "thịt", "gà", "rau"],
            "tỏi": ["rau muống", "thịt", "cá", "tôm", "gà"],
            "sả": ["gà", "cá", "tôm", "thịt"],
            "lá chanh": ["cá", "gà", "tôm", "thịt"],
            "rau thơm": ["cá", "tôm", "thịt", "cà chua"],
            "rau răm": ["gà", "cá", "tôm", "thịt"],
            "hành lá": ["cá", "tôm", "thịt", "trứng"],
            # Trái cây
            "thơm": ["tôm", "cá", "thịt heo", "cà chua"],
            "khế chua": ["cá", "tôm", "thịt", "cà chua"],
            "chuối xanh": ["thịt heo", "tôm", "cá"],
            "đu đủ xanh": ["tôm", "cà rót", "cà chua"],
            # Các loại củ quả khác
            "khoai môn": ["thịt heo", "tôm", "cà chua", "gừng"],
            "khoai lang": ["thịt gà", "cà chua", "gừng"],
            "củ cải trắng": ["thịt heo", "tôm", "cà chua", "gừng"],
            "bí đao": ["tôm", "thịt heo", "nấm", "gừng"],
            "bầu": ["tôm", "cua", "thịt heo", "gừng"],
            # Default fallbacks với nhiều sự lựa chọn
            "": [
                "gừng",
                "tiêu",
                "chanh",
                "tỏi",
                "cà chua",
                "hành tây",
                "nấm",
                "rau thơm",
            ],
            "khác": [
                "gừng",
                "tiêu",
                "chanh",
                "tỏi",
                "cà chua",
                "hành tây",
                "nấm",
                "rau thơm",
            ],
        }

        # Product base name mapping for better deduplication
        self.product_base_names = {
            "hành tây": ["hành tây", "onion"],
            "cà chua": ["cà chua", "tomato"],
            "khoai tây": ["khoai tây", "potato"],
            "gừng": ["gừng", "ginger"],
            "tỏi": ["tỏi", "garlic"],
            "nấm": ["nấm", "mushroom"],
            "cà rót": ["cà rót", "eggplant"],
            "rau muống": ["rau muống", "water spinach"],
            "bắp cải": ["bắp cải", "cabbage"],
            "thịt gà": ["thịt gà", "gà", "chicken"],
            "thịt heo": ["thịt heo", "thịt lợn", "pork"],
            "thịt bò": ["thịt bò", "beef"],
            "cá": ["cá", "fish"],
            "tôm": ["tôm", "shrimp"],
            "cua": ["cua", "crab"],
        }

        logger.info(
            "✅ Enhanced ProductRecommendationService initialized with improved diversity logic"
        )

    # ---------------------- Enhanced Diversity Methods ----------------------
    def _extract_product_base_name(self, product_name: str) -> str:
        """Extract base product name for deduplication (e.g., 'Hành tây Hà Lan' -> 'hành tây')"""
        product_lower = product_name.lower()

        # Find the longest matching base name
        best_match = ""
        for base_name, variants in self.product_base_names.items():
            for variant in variants:
                if variant.lower() in product_lower:
                    if len(variant) > len(best_match):
                        best_match = base_name

        # If no specific match, extract first 2-3 words
        if not best_match:
            words = product_lower.split()
            if len(words) >= 2:
                best_match = " ".join(words[:2])
            else:
                best_match = words[0] if words else product_name.lower()

        return best_match

    def _calculate_product_diversity_score(
        self, product_name: str, existing_products: List[str]
    ) -> float:
        """Calculate diversity score - higher is more diverse"""
        if not existing_products:
            return 1.0

        base_name = self._extract_product_base_name(product_name)

        # Count similar base names in existing products
        similar_count = 0
        for existing in existing_products:
            existing_base = self._extract_product_base_name(existing)
            if self._calculate_text_similarity(base_name, existing_base) > 0.7:
                similar_count += 1

        # Higher penalty for more similar products
        diversity_score = 1.0 / (1.0 + similar_count * 0.5)
        return diversity_score

    def _is_product_too_similar(
        self, new_product: str, existing_products: List[str]
    ) -> bool:
        """Check if product is too similar to existing ones"""
        new_base = self._extract_product_base_name(new_product)

        same_base_count = 0
        for existing in existing_products:
            existing_base = self._extract_product_base_name(existing)
            similarity = self._calculate_text_similarity(new_base, existing_base)

            if similarity > self.config["product_similarity_threshold"]:
                same_base_count += 1
                if same_base_count >= self.config["max_same_base_product"]:
                    return True

        return False

    def _enhanced_deduplicate_and_rank(
        self,
        recommendations: List[ProductRecommendation],
        current_product: Dict[str, Any],
        limit: int,
    ) -> List[ProductRecommendation]:
        """Enhanced deduplication with diversity optimization"""
        try:
            current_name = (current_product.get("product_name") or "").lower()

            # Group by base product type
            base_groups = defaultdict(list)
            for r in recommendations:
                base_name = self._extract_product_base_name(r.product_name)
                base_groups[base_name].append(r)

            # Select best from each group first
            diverse_recs = []
            selected_names = []

            # Sort groups by average confidence to prioritize high-quality groups
            sorted_groups = sorted(
                base_groups.items(),
                key=lambda x: sum(r.confidence for r in x[1]) / len(x[1]),
                reverse=True,
            )

            for base_name, group_recs in sorted_groups:
                if len(diverse_recs) >= limit:
                    break

                # Skip if too similar to current product
                if self._calculate_text_similarity(current_name, base_name) > 0.85:
                    continue

                # Sort group by score and take best ones
                group_recs.sort(
                    key=lambda x: (x.confidence, x.similarity_score or 0), reverse=True
                )

                added_from_group = 0
                max_from_group = min(
                    self.config["max_same_base_product"],
                    max(1, limit // len(sorted_groups)),
                )

                for rec in group_recs:
                    if len(diverse_recs) >= limit or added_from_group >= max_from_group:
                        break

                    # Calculate diversity bonus
                    diversity_score = self._calculate_product_diversity_score(
                        rec.product_name, selected_names
                    )

                    # Apply diversity boost to confidence
                    if diversity_score > 0.8:  # High diversity
                        rec.confidence *= self.config["diversity_boost_factor"]

                    diverse_recs.append(rec)
                    selected_names.append(rec.product_name)
                    added_from_group += 1

            # If we still need more products, add remaining with diversity check
            if len(diverse_recs) < limit:
                remaining_recs = []
                for group_recs in base_groups.values():
                    for rec in group_recs:
                        if rec not in diverse_recs:
                            remaining_recs.append(rec)

                remaining_recs.sort(
                    key=lambda x: (x.confidence, x.similarity_score or 0), reverse=True
                )

                for rec in remaining_recs:
                    if len(diverse_recs) >= limit:
                        break

                    if not self._is_product_too_similar(
                        rec.product_name, selected_names
                    ):
                        diverse_recs.append(rec)
                        selected_names.append(rec.product_name)

            # Final ranking with diversity consideration
            def enhanced_score_fn(rec: ProductRecommendation):
                weights = {
                    "similar": 1.0,
                    "category": 0.8,
                    "complementary": 0.9,
                    "history": 0.7,
                    "trending": 0.6,
                }
                base_score = (
                    rec.confidence
                    * weights.get(rec.recommendation_type, 0.5)
                    * (rec.similarity_score or 0.5)
                )

                # Add diversity bonus
                diversity_score = self._calculate_product_diversity_score(
                    rec.product_name, [r.product_name for r in diverse_recs if r != rec]
                )
                return base_score * (1 + diversity_score * 0.2)

            diverse_recs.sort(key=enhanced_score_fn, reverse=True)

            logger.info(
                f"✅ Enhanced deduplication: {len(recommendations)} -> {len(diverse_recs[:limit])}"
            )
            return diverse_recs[:limit]

        except Exception:
            logger.exception("❌ Enhanced deduplication failed, using fallback")
            return self._basic_deduplicate_and_rank(
                recommendations, current_product, limit
            )

    def _basic_deduplicate_and_rank(
        self,
        recommendations: List[ProductRecommendation],
        current_product: Dict[str, Any],
        limit: int,
    ) -> List[ProductRecommendation]:
        """Fallback basic deduplication"""
        try:
            seen = set()
            unique: List[ProductRecommendation] = []
            current_name = (current_product.get("product_name") or "").lower()

            for r in recommendations:
                key = r.product_name.lower()
                if key in seen:
                    continue
                if self._calculate_text_similarity(current_name, key) > 0.85:
                    continue
                seen.add(key)
                unique.append(r)

            def score_fn(rec: ProductRecommendation):
                weights = {
                    "similar": 1.0,
                    "category": 0.8,
                    "complementary": 0.9,
                    "history": 0.7,
                    "trending": 0.6,
                }
                w = weights.get(rec.recommendation_type, 0.5)
                return rec.confidence * w * (rec.similarity_score or 0.5)

            unique.sort(key=score_fn, reverse=True)
            return unique[:limit]
        except Exception:
            logger.exception("❌ Basic deduplication failed")
            return recommendations[:limit]

    # ---------------------- Enhanced Complementary Search ----------------------
    async def _search_enhanced_complementary_products(
        self, current_product_name: str, price_reference: float, limit: int = 3
    ) -> List[ProductRecommendation]:
        """Enhanced complementary search with better diversity"""
        try:
            product_name_lower = current_product_name.lower()
            complementary_terms = []

            # Find matching complementary items
            for key, vals in self.complementary_mapping.items():
                if key and key in product_name_lower:
                    complementary_terms.extend(vals)
                    break

            # Enhanced fallback logic
            if not complementary_terms:
                if any(
                    meat in product_name_lower for meat in ["thịt", "gà", "heo", "bò"]
                ):
                    complementary_terms = [
                        "gừng",
                        "tiêu",
                        "chanh",
                        "tỏi",
                        "sả",
                        "lá chanh",
                    ]
                elif any(
                    seafood in product_name_lower
                    for seafood in ["cá", "tôm", "cua", "hải sản"]
                ):
                    complementary_terms = [
                        "gừng",
                        "tiêu",
                        "chanh",
                        "lá chanh",
                        "rau thơm",
                        "thơm",
                    ]
                elif any(veg in product_name_lower for veg in ["rau", "củ"]):
                    complementary_terms = ["thịt", "cá", "tôm", "gừng", "tỏi"]
                else:
                    complementary_terms = [
                        "gừng",
                        "tiêu",
                        "chanh",
                        "tỏi",
                        "cà chua",
                        "hành tây",
                    ]

            # Remove duplicates and shuffle for variety
            complementary_terms = list(set(complementary_terms))

            recs: List[ProductRecommendation] = []
            max_comp_price = min(price_reference * 0.8, 200000)
            seen_base_names = set()

            # Search for each complementary term with diversity tracking
            for comp in complementary_terms[:6]:  # Search more terms but limit results
                candidates = self._query_vector_db(comp, 8)  # Get more candidates

                for r in candidates:
                    try:
                        meta = self._extract_metadata_safe(r)
                        if not meta:
                            continue
                        name = (meta.get("product_name") or "").strip()
                        price = self._parse_price_safe(meta.get("product_price", 0))

                        if (
                            not name
                            or self._calculate_text_similarity(
                                current_product_name.lower(), name.lower()
                            )
                            > 0.7
                        ):
                            continue

                        if price <= 0 or price > max_comp_price:
                            continue

                        # Check diversity
                        base_name = self._extract_product_base_name(name)
                        if base_name in seen_base_names:
                            continue

                        seen_base_names.add(base_name)
                        sim = float(getattr(r, "score", 0.6))

                        recs.append(
                            ProductRecommendation(
                                product_id=str(uuid.uuid4()),
                                product_name=name,
                                product_price=price,
                                product_price_formatted=self._format_currency(price),
                                product_category=meta.get(
                                    "product_category", "Thực phẩm tươi sống"
                                ),
                                product_url=meta.get("product_url", ""),
                                image_url=meta.get("image_url", ""),
                                similarity_score=sim,
                                recommendation_type="complementary",
                                reason=f"Kết hợp tốt với {current_product_name}",
                                confidence=0.75,
                            )
                        )

                        if (
                            len(recs) >= limit * 2
                        ):  # Get more candidates for diversity selection
                            break
                    except Exception:
                        logger.exception("⚠️ Error processing complementary candidate")
                        continue

                if len(recs) >= limit * 2:
                    break

            # Apply enhanced ranking for diversity
            recs.sort(key=lambda x: (x.confidence, x.similarity_score), reverse=True)
            return recs[:limit]

        except Exception:
            logger.exception("❌ Enhanced complementary search failed")
            return []

    # ---------------------- Updated Main Methods ----------------------
    async def _get_immediate_recommendations(
        self, product_name: str, product_price: float, product_category: str, limit: int
    ) -> List[ProductRecommendation]:
        try:
            logger.info(f"🔍 Enhanced immediate recs for: {product_name}")
            recs: List[ProductRecommendation] = []

            # 1) Similar (vector/hybrid) - get more candidates for diversity
            similar = await self._search_similar_products(
                product_name, product_price, limit=max(6, limit)
            )
            recs.extend(similar)

            # 2) Enhanced complementary
            if len(recs) < limit:
                comp = await self._search_enhanced_complementary_products(
                    product_name, product_price, limit=4
                )
                recs.extend(comp)

            # 3) Category-based
            if len(recs) < limit:
                cat = await self._search_category_products(
                    product_category,
                    product_price,
                    exclude_names=[r.product_name for r in recs],
                    limit=4,
                )
                recs.extend(cat)

            # 4) Trending fallback
            if len(recs) < limit:
                tr = await self._search_trending_products(
                    product_price,
                    exclude_names=[r.product_name for r in recs],
                    limit=limit,
                )
                recs.extend(tr)

            logger.info(f"✅ Enhanced immediate found: {len(recs)}")
            return recs
        except Exception:
            logger.exception("❌ Error in enhanced immediate recommendations")
            return []

    # ---------------------- Public API with Enhanced Logic ----------------------
    async def get_recommendations(
        self, request: RecommendationRequest
    ) -> Dict[str, Any]:
        try:
            logger.info(
                f"🎯 Getting enhanced recommendations for: {request.current_product.get('product_name')}"
            )
            start_time = datetime.now()

            current_name = (request.current_product.get("product_name") or "").strip()
            current_price = float(request.current_product.get("unit_price") or 0)
            current_category = (
                request.current_product.get("product_category") or "Thực phẩm tươi sống"
            ).strip()

            # Primary: immediate recommendations
            immediate = await self._get_immediate_recommendations(
                current_name,
                current_price,
                current_category,
                request.limit * 2,  # Get more for diversity
            )

            # Fallback: history-based
            history_recs: List[ProductRecommendation] = []
            if (
                request.include_history
                and request.customer_info
                and request.customer_info.get("customer_id")
            ):
                history = await self._get_history_recommendations(
                    request.customer_info.get("customer_id"),
                    current_category,
                    current_price,
                    min(4, request.limit // 2),
                )
                history_recs = history

            all_recs = immediate + history_recs

            # Use enhanced deduplication
            final = self._enhanced_deduplicate_and_rank(
                all_recs, request.current_product, request.limit
            )

            processing_time_ms = round(
                (datetime.now() - start_time).total_seconds() * 1000, 2
            )

            response = {
                "success": True,
                "total_found": len(final),
                "recommendations": [r.to_dict() for r in final],
                "strategy": {
                    "primary": "enhanced_immediate",
                    "immediate_count": len(immediate),
                    "history_count": len(history_recs),
                    "diversity_applied": True,
                    "processing_time_ms": processing_time_ms,
                },
                "metadata": {
                    "current_product": {
                        "name": current_name,
                        "price": current_price,
                        "category": current_category,
                    },
                    "customer_segment": self._classify_customer(
                        request.customer_info or {}
                    ),
                    "recommendation_types": list(
                        {r.recommendation_type for r in final}
                    ),
                    "diversity_stats": {
                        "unique_base_products": len(
                            set(
                                self._extract_product_base_name(r.product_name)
                                for r in final
                            )
                        ),
                        "total_candidates": len(all_recs),
                    },
                },
            }

            logger.info(
                f"✅ Enhanced recommendations: {len(final)} diverse products in {processing_time_ms}ms"
            )
            return response

        except Exception:
            logger.exception("❌ Error in enhanced get_recommendations")
            return {"success": False, "error": "internal_error", "recommendations": []}

    # ---------------------- Keep all existing utility methods ----------------------
    def _wrap_query_results(self, results: List[Dict[str, Any]]) -> List[Any]:
        """Convert QueryRetriever dict results to lightweight objects compatible with existing logic."""
        formatted = []
        for r in results:
            obj = type("Doc", (), {})()
            payload = r.get("metadata") if isinstance(r, dict) else {}
            setattr(obj, "payload", payload or {})
            setattr(obj, "score", float(r.get("score", 0.0)))
            setattr(obj, "id", r.get("id", str(uuid.uuid4())))
            setattr(
                obj,
                "page_content",
                r.get("page_content", payload.get("product_name", "")),
            )
            formatted.append(obj)
        return formatted

    def _query_vector_db(self, query: str, limit: int = 10) -> List[Any]:
        """Primary query path: use query_service.invoke_query if present (hybrid)."""
        try:
            # Use enhanced QueryRetriever when available
            if self.query_service:
                results = self.query_service.invoke_query(
                    query, collection_name=self.default_collection, use_hybrid=True
                )
                if not isinstance(results, list):
                    return []
                return self._wrap_query_results(results[:limit])

            # Fallback: try vector_db's native methods (compat)
            if hasattr(self.vector_db, "similarity_search_with_score"):
                try:
                    raw = self.vector_db.similarity_search_with_score(query, k=limit)
                    formatted = []
                    for doc, score in raw:
                        setattr(doc, "score", float(score))
                        formatted.append(doc)
                    return formatted
                except Exception:
                    logger.exception("Fallback similarity_search_with_score failed")
                    return []

            if hasattr(self.vector_db, "similarity_search"):
                try:
                    return self.vector_db.similarity_search(query, k=limit)
                except Exception:
                    logger.exception("Fallback similarity_search failed")
                    return []

            logger.warning("No query path available for vector_db")
            return []
        except Exception:
            logger.exception("❌ Error in _query_vector_db")
            return []

    async def _search_similar_products(
        self, product_name: str, price_reference: float, limit: int = 4
    ) -> List[ProductRecommendation]:
        try:
            # Enhanced queries for better Vietnamese food matching
            queries = [
                product_name,
                f"{product_name} tươi",
                f"{product_name} ngon",
                f"sản phẩm giống {product_name}",
                f"{product_name} chất lượng",
            ]

            all_results = []
            for q in queries:
                results = self._query_vector_db(q, limit + 5)
                if results:
                    all_results.extend(results)
                if len(all_results) >= limit * 3:
                    break

            recs: List[ProductRecommendation] = []
            seen_base_names = set()

            for r in all_results:
                try:
                    meta = self._extract_metadata_safe(r)
                    if not meta:
                        continue
                    name = (
                        meta.get("product_name") or str(meta.get("name") or "")
                    ).strip()
                    price = self._parse_price_safe(meta.get("product_price", 0))
                    if not name or price <= 0:
                        continue

                    # Skip if too similar to original product
                    if (
                        self._calculate_text_similarity(
                            product_name.lower(), name.lower()
                        )
                        > 0.85
                    ):
                        continue

                    # Price filtering
                    if not (
                        price_reference * self.config["min_price_ratio"]
                        <= price
                        <= price_reference * self.config["max_price_ratio"]
                    ):
                        continue

                    # Check diversity
                    base_name = self._extract_product_base_name(name)
                    if base_name in seen_base_names:
                        continue

                    seen_base_names.add(base_name)
                    sim = float(getattr(r, "score", 0.6))

                    recs.append(
                        ProductRecommendation(
                            product_id=str(uuid.uuid4()),
                            product_name=name,
                            product_price=price,
                            product_price_formatted=self._format_currency(price),
                            product_category=meta.get(
                                "product_category", "Thực phẩm tươi sống"
                            ),
                            product_url=meta.get("product_url", ""),
                            image_url=meta.get("image_url", ""),
                            similarity_score=sim,
                            recommendation_type="similar",
                            reason=f"Sản phẩm tương tự {product_name}",
                            confidence=min(0.9, 0.6 + sim * 0.3),
                        )
                    )

                    if len(recs) >= limit:
                        break
                except Exception:
                    logger.exception("⚠️ Error processing similar product candidate")
                    continue

            return recs[:limit]
        except Exception:
            logger.exception("❌ Error in _search_similar_products")
            return []

    async def _search_category_products(
        self,
        category: str,
        price_reference: float,
        exclude_names: List[str],
        limit: int = 3,
    ) -> List[ProductRecommendation]:
        try:
            category_queries = [
                category,
                f"sản phẩm {category}",
                f"{category} tươi ngon",
                (
                    "thực phẩm tươi sống"
                    if category == "Thực phẩm tươi sống"
                    else category
                ),
            ]

            all_results = []
            for q in category_queries:
                results = self._query_vector_db(q, limit + 3)
                if results:
                    all_results.extend(results)
                if len(all_results) >= limit * 2:
                    break

            recs: List[ProductRecommendation] = []
            exclude_lower = [n.lower() for n in exclude_names]
            seen_base_names = set()
            max_price = min(price_reference * 1.5, 500000)

            for r in all_results:
                try:
                    meta = self._extract_metadata_safe(r)
                    if not meta:
                        continue

                    name = (meta.get("product_name") or "").strip()
                    price = self._parse_price_safe(meta.get("product_price", 0))

                    if not name or price <= 0 or price > max_price:
                        continue

                    if name.lower() in exclude_lower:
                        continue

                    # Check diversity
                    base_name = self._extract_product_base_name(name)
                    if base_name in seen_base_names:
                        continue

                    seen_base_names.add(base_name)
                    sim = float(getattr(r, "score", 0.5))

                    recs.append(
                        ProductRecommendation(
                            product_id=str(uuid.uuid4()),
                            product_name=name,
                            product_price=price,
                            product_price_formatted=self._format_currency(price),
                            product_category=meta.get("product_category", category),
                            product_url=meta.get("product_url", ""),
                            image_url=meta.get("image_url", ""),
                            similarity_score=sim,
                            recommendation_type="category",
                            reason=f"Cùng danh mục {category}",
                            confidence=0.7,
                        )
                    )

                    if len(recs) >= limit:
                        break
                except Exception:
                    logger.exception("⚠️ Error processing category candidate")
                    continue

            return recs[:limit]
        except Exception:
            logger.exception("❌ Error in _search_category_products")
            return []

    async def _search_trending_products(
        self, price_reference: float, exclude_names: List[str], limit: int = 2
    ) -> List[ProductRecommendation]:
        try:
            trending_queries = [
                "sản phẩm bán chạy",
                "thực phẩm phổ biến",
                "rau củ tươi ngon",
                "thịt cá tươi",
                "gia vị thiết yếu",
            ]

            all_results = []
            for q in trending_queries:
                results = self._query_vector_db(q, 5)
                if results:
                    all_results.extend(results)

            recs: List[ProductRecommendation] = []
            exclude_lower = [n.lower() for n in exclude_names]
            seen_base_names = set()
            max_price = min(price_reference * 2.0, 300000)

            for r in all_results:
                try:
                    meta = self._extract_metadata_safe(r)
                    if not meta:
                        continue

                    name = (meta.get("product_name") or "").strip()
                    price = self._parse_price_safe(meta.get("product_price", 0))

                    if not name or price <= 0 or price > max_price:
                        continue

                    if name.lower() in exclude_lower:
                        continue

                    # Check diversity
                    base_name = self._extract_product_base_name(name)
                    if base_name in seen_base_names:
                        continue

                    seen_base_names.add(base_name)

                    recs.append(
                        ProductRecommendation(
                            product_id=str(uuid.uuid4()),
                            product_name=name,
                            product_price=price,
                            product_price_formatted=self._format_currency(price),
                            product_category=meta.get(
                                "product_category", "Thực phẩm tươi sống"
                            ),
                            product_url=meta.get("product_url", ""),
                            image_url=meta.get("image_url", ""),
                            similarity_score=0.5,
                            recommendation_type="trending",
                            reason="Sản phẩm được ưa chuộng",
                            confidence=0.6,
                        )
                    )

                    if len(recs) >= limit:
                        break
                except Exception:
                    logger.exception("⚠️ Error processing trending candidate")
                    continue

            return recs[:limit]
        except Exception:
            logger.exception("❌ Error in _search_trending_products")
            return []

    async def _get_history_recommendations(
        self, customer_id: str, category: str, price_reference: float, limit: int = 2
    ) -> List[ProductRecommendation]:
        try:
            # Simulate history-based recommendations
            # In real implementation, this would query customer purchase history
            history_queries = [
                f"lịch sử mua hàng {category}",
                f"khách hàng thường mua {category}",
                "sản phẩm tái mua",
            ]

            all_results = []
            for q in history_queries:
                results = self._query_vector_db(q, 3)
                if results:
                    all_results.extend(results)

            recs: List[ProductRecommendation] = []
            seen_base_names = set()

            for r in all_results:
                try:
                    meta = self._extract_metadata_safe(r)
                    if not meta:
                        continue

                    name = (meta.get("product_name") or "").strip()
                    price = self._parse_price_safe(meta.get("product_price", 0))

                    if not name or price <= 0:
                        continue

                    # Check diversity
                    base_name = self._extract_product_base_name(name)
                    if base_name in seen_base_names:
                        continue

                    seen_base_names.add(base_name)

                    recs.append(
                        ProductRecommendation(
                            product_id=str(uuid.uuid4()),
                            product_name=name,
                            product_price=price,
                            product_price_formatted=self._format_currency(price),
                            product_category=meta.get("product_category", category),
                            product_url=meta.get("product_url", ""),
                            image_url=meta.get("image_url", ""),
                            similarity_score=0.6,
                            recommendation_type="history",
                            reason="Dựa trên lịch sử mua hàng",
                            confidence=0.75,
                        )
                    )

                    if len(recs) >= limit:
                        break
                except Exception:
                    logger.exception("⚠️ Error processing history candidate")
                    continue

            return recs[:limit]
        except Exception:
            logger.exception("❌ Error in _get_history_recommendations")
            return []

    # ---------------------- Utility Methods ----------------------
    def _extract_metadata_safe(self, result: Any) -> Dict[str, Any]:
        """Safely extract metadata from different result formats"""
        try:
            if hasattr(result, "payload") and result.payload:
                return dict(result.payload)
            elif hasattr(result, "metadata") and result.metadata:
                return dict(result.metadata)
            elif isinstance(result, dict):
                return result.get("metadata", {})
            return {}
        except Exception:
            return {}

    def _parse_price_safe(self, price_val: Any) -> float:
        """Safely parse price from various formats"""
        try:
            if isinstance(price_val, (int, float)):
                return float(price_val)
            if isinstance(price_val, str):
                # Remove currency symbols and convert
                cleaned = re.sub(r"[^\d.]", "", price_val.replace(",", ""))
                return float(cleaned) if cleaned else 0.0
            return 0.0
        except Exception:
            return 0.0

    def _format_currency(self, price: float) -> str:
        """Format price as Vietnamese currency"""
        try:
            return f"{int(price):,}đ".replace(",", ".")
        except Exception:
            return "0đ"

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings"""
        try:
            return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        except Exception:
            return 0.0

    def _classify_customer(self, customer_info: Dict[str, Any]) -> str:
        """Classify customer for personalization"""
        try:
            if not customer_info:
                return "new"

            customer_id = customer_info.get("customer_id")
            if not customer_id:
                return "guest"

            # In real implementation, this would analyze purchase history
            return "returning"
        except Exception:
            return "unknown"

    # ---------------------- Factory Functions ----------------------


def create_recommendation_service(
    vector_db,
    embed_model,
    connection_string: str,
    query_service=None,
    default_collection: str = "dat_614943",
) -> ProductRecommendationService:
    """Create enhanced recommendation service instance"""
    return ProductRecommendationService(
        vector_db=vector_db,
        embed_model=embed_model,
        connection_string=connection_string,
        query_service=query_service,
        default_collection=default_collection,
    )


def create_recommendation_request(
    current_product: Dict[str, Any],
    customer_info: Dict[str, Any] = None,
    session_id: str = None,
    limit: int = 6,
    include_history: bool = False,
) -> RecommendationRequest:
    """Create recommendation request"""
    return RecommendationRequest(
        current_product=current_product,
        customer_info=customer_info or {},
        session_id=session_id or str(uuid.uuid4()),
        limit=limit,
        include_history=include_history,
    )
