import logging
from typing import Dict, List

from .payment_processer import PaymentProcessor, PaymentWorkflow

logger = logging.getLogger(__name__)


class QdrantProductLoader:
    """Lớp chuyên dụng để load và search sản phẩm từ Qdrant"""

    def __init__(self, vector_db, embed_model):
        self.vector_db = vector_db
        self.embed_model = embed_model
        self.collection_name = "dat_614943"  # Collection name chứa sản phẩm

    def load_products_from_qdrant(self) -> Dict[str, Dict]:
        """Load tất cả sản phẩm từ Qdrant collection"""
        try:
            logger.info(
                f"🔄 Loading products from Qdrant collection: {self.collection_name}"
            )

            client = self.vector_db._create_client()

            # Get all points từ collection với pagination
            all_products = {}
            offset = 0
            limit = 1170

            while True:
                # Scroll through all points in collection
                scroll_result = client.scroll(
                    collection_name=self.collection_name,
                    offset=offset,
                    limit=limit,
                    with_payload=True,
                    with_vectors=False,
                )

                points = scroll_result[0]  # points
                next_offset = scroll_result[1]  # next offset

                if not points:
                    break

                # Process each point
                for point in points:
                    if point.payload:
                        product_id = str(point.id)
                        product_data = {
                            "id": product_id,
                            "title": point.payload.get("product_name", ""),
                            "price": self._parse_price(
                                point.payload.get("product_price", "0")
                            ),
                            "category": point.payload.get("product_category", ""),
                            "url": point.payload.get("product_url", ""),
                            "image_url": point.payload.get("image_url", ""),
                            "price_unit": point.payload.get("product_price_unit", "₫"),
                            "original_payload": point.payload,
                        }

                        all_products[product_id] = product_data

                        # Log first few products for debugging
                        if len(all_products) <= 5:
                            logger.info(
                                f"✅ Loaded from Qdrant: {product_data['title']} - {product_data['price']} {product_data['price_unit']}"
                            )

                # Check if we've reached the end
                if next_offset is None or len(points) < limit:
                    break

                offset = next_offset

            logger.info(f"✅ Loaded {len(all_products)} products from Qdrant")
            return all_products

        except Exception as e:
            logger.error(f"❌ Error loading products from Qdrant: {str(e)}")
            return {}

    def search_products_by_query(self, query: str, limit: int = 5) -> List[Dict]:
        """Search sản phẩm trong Qdrant bằng vector similarity"""
        try:
            logger.info(f"🔍 Searching Qdrant for: '{query}'")

            client = self.vector_db._create_client()

            # Generate embedding cho query
            query_embedding = self.embed_model.embed_query(query)

            # Search với vector similarity
            search_results = client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=limit,
                with_payload=True,
                with_vectors=False,
                score_threshold=0.1,  # Minimum similarity threshold
            )

            # Format results
            formatted_results = []
            for result in search_results:
                if result.payload:
                    product_data = {
                        "id": str(result.id),
                        "title": result.payload.get("product_name", ""),
                        "price": self._parse_price(
                            result.payload.get("product_price", "0")
                        ),
                        "category": result.payload.get("product_category", ""),
                        "url": result.payload.get("product_url", ""),
                        "image_url": result.payload.get("image_url", ""),
                        "price_unit": result.payload.get("product_price_unit", "₫"),
                        "similarity_score": result.score,
                        "original_payload": result.payload,
                    }
                    formatted_results.append(product_data)

                    logger.info(
                        f"📦 Found: {product_data['title']} (score: {result.score:.3f})"
                    )

            logger.info(f"✅ Found {len(formatted_results)} matching products")
            return formatted_results

        except Exception as e:
            logger.error(f"❌ Error searching products in Qdrant: {str(e)}")
            return []

    def _parse_price(self, price_str: str) -> float:
        """Parse price string thành float"""
        try:
            if isinstance(price_str, (int, float)):
                return float(price_str)

            import re

            # Remove all non-digit characters
            price_clean = re.sub(r"[^\d.]", "", str(price_str))
            return float(price_clean) if price_clean else 0.0
        except:
            return 0.0
