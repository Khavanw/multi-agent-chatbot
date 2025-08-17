import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class QdrantOrderStorage:
    """
    Hệ thống lưu trữ đơn hàng trên Qdrant
    Thay thế SQL Server Database với 3 collections:
    - users_collection: Thông tin khách hàng
    - orders_collection: Đơn hàng
    - order_items_collection: Chi tiết sản phẩm trong đơn hàng
    """

    def __init__(self, vector_db, embed_model):
        self.vector_db = vector_db
        self.embed_model = embed_model
        self.client = vector_db._create_client()

        # Tên các collections
        self.users_collection = "users_storage"
        self.orders_collection = "orders_storage"
        self.order_items_collection = "order_items_storage"

        # Khởi tạo collections
        self._initialize_collections()

    def _initialize_collections(self):
        """Khởi tạo các collections nếu chưa tồn tại"""
        try:
            logger.info("🔧 Initializing Qdrant collections for order storage...")

            collections_to_create = [
                {
                    "name": self.users_collection,
                    "description": "Store user information",
                },
                {
                    "name": self.orders_collection,
                    "description": "Store order information",
                },
                {
                    "name": self.order_items_collection,
                    "description": "Store order items details",
                },
            ]

            for collection_info in collections_to_create:
                collection_name = collection_info["name"]

                try:
                    # Kiểm tra collection đã tồn tại chưa
                    collection_info_response = self.client.get_collection(
                        collection_name
                    )
                    logger.info(f"✅ Collection '{collection_name}' already exists")

                except Exception:
                    # Collection chưa tồn tại, tạo mới
                    logger.info(f"🔄 Creating collection '{collection_name}'...")

                    from qdrant_client.models import Distance, VectorParams

                    self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=768, distance=Distance.COSINE  # OpenAI embedding size
                        ),
                    )
                    logger.info(f"✅ Created collection '{collection_name}'")

            logger.info("✅ All Qdrant storage collections initialized successfully")

        except Exception as e:
            logger.error(f"❌ Error initializing Qdrant collections: {str(e)}")
            raise

    def create_user(self, user_data: Dict[str, Any]) -> str:
        """
        Tạo user mới trong Qdrant
        Tương đương INSERT INTO users
        """
        try:
            user_id = user_data.get("id") or str(uuid.uuid4())
            session_id = user_data.get("session_id")
            name = user_data.get("name", "")
            phone = user_data.get("phone", "")
            email = user_data.get("email", "")
            address = user_data.get("address", "")

            # Tạo embedding từ thông tin user để có thể search
            search_text = f"{name} {phone} {email} {address}".strip()
            embedding = self.embed_model.embed_query(search_text)

            # Payload chứa tất cả thông tin user
            payload = {
                "id": user_id,
                "session_id": session_id,
                "name": name,
                "phone": phone,
                "email": email,
                "address": address,
                "gmail": email,  # Tương ứng field gmail trong DB
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "record_type": "user",
                "search_text": search_text,
            }

            from qdrant_client.models import PointStruct

            point = PointStruct(id=user_id, vector=embedding, payload=payload)

            self.client.upsert(collection_name=self.users_collection, points=[point])

            logger.info(f"✅ Created user in Qdrant: {name} ({user_id})")
            return user_id

        except Exception as e:
            logger.error(f"❌ Error creating user in Qdrant: {str(e)}")
            raise

    def get_user_by_session_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Lấy user theo session_id
        Tương đương SELECT * FROM users WHERE session_id = ?
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="session_id", match=MatchValue(value=session_id)
                    ),
                    FieldCondition(key="record_type", match=MatchValue(value="user")),
                ]
            )

            results = self.client.scroll(
                collection_name=self.users_collection,
                scroll_filter=filter_condition,
                limit=1,
                with_payload=True,
            )

            if results and results[0]:
                point = results[0][0]
                logger.info(f"✅ Found user for session: {session_id}")
                return point.payload
            else:
                logger.info(f"👤 No user found for session: {session_id}")
                return None

        except Exception as e:
            logger.error(f"❌ Error getting user by session_id: {str(e)}")
            return None

    def create_order(self, order_data: Dict[str, Any]) -> str:
        """
        Tạo đơn hàng mới trong Qdrant
        Tương đương INSERT INTO orders
        """
        try:
            order_id = order_data.get("order_id") or str(uuid.uuid4())
            session_id = order_data.get("session_id")
            user_phone = order_data.get("user_phone", "")
            total_amount = order_data.get("total_amount", 0.0)
            status = order_data.get("status", "pending_payment")
            payment_method = order_data.get("payment_method", "")
            payment_option = order_data.get("payment_option", "")
            notes = order_data.get("notes", "")
            image_url = order_data.get("image_url", "")

            # Tạo embedding từ thông tin order
            search_text = f"order {order_id} {user_phone} {status} {payment_method} {notes}".strip()
            embedding = self.embed_model.embed_query(search_text)

            # Payload chứa tất cả thông tin order
            payload = {
                "id": order_id,
                "order_id": order_id,
                "session_id": session_id,
                "user_phone": user_phone,
                "total_amount": float(total_amount),
                "status": status,
                "payment_method": payment_method,
                "payment_option": payment_option,
                "notes": notes,
                "image_url": image_url,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "record_type": "order",
                "search_text": search_text,
            }

            from qdrant_client.models import PointStruct

            point = PointStruct(id=order_id, vector=embedding, payload=payload)

            self.client.upsert(collection_name=self.orders_collection, points=[point])

            logger.info(
                f"✅ Created order in Qdrant: {order_id} - {total_amount:,.0f} VND"
            )
            return order_id

        except Exception as e:
            logger.error(f"❌ Error creating order in Qdrant: {str(e)}")
            raise

    def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Lấy đơn hàng theo order_id
        Tương đương SELECT * FROM orders WHERE order_id = ?
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            filter_condition = Filter(
                must=[
                    FieldCondition(key="order_id", match=MatchValue(value=order_id)),
                    FieldCondition(key="record_type", match=MatchValue(value="order")),
                ]
            )

            results = self.client.scroll(
                collection_name=self.orders_collection,
                scroll_filter=filter_condition,
                limit=1,
                with_payload=True,
            )

            if results and results[0]:
                point = results[0][0]
                logger.info(f"✅ Found order: {order_id}")
                return point.payload
            else:
                logger.info(f"📦 No order found: {order_id}")
                return None

        except Exception as e:
            logger.error(f"❌ Error getting order by id: {str(e)}")
            return None

    def create_order_item(self, item_data: Dict[str, Any]) -> str:
        """
        Tạo order item mới trong Qdrant
        Tương đương INSERT INTO order_items
        """
        try:
            item_id = str(uuid.uuid4())
            order_id = item_data.get("order_id")
            product_name = item_data.get("product_name", "")
            quantity = item_data.get("quantity", 1.0)
            unit_price = item_data.get("unit_price", 0.0)
            total_price = item_data.get("total_price", 0.0)
            image_url = item_data.get("image_url", "")
            product_url = item_data.get("product_url", "")
            product_category = item_data.get("product_category", "")
            unit = item_data.get("unit", "kg")

            # Tạo embedding từ thông tin sản phẩm
            search_text = f"{product_name} {product_category} {unit}".strip()
            embedding = self.embed_model.embed_query(search_text)

            # Payload chứa tất cả thông tin order item
            payload = {
                "id": item_id,
                "order_id": order_id,
                "product_name": product_name,
                "quantity": float(quantity),
                "unit_price": float(unit_price),
                "total_price": float(total_price),
                "product_url": product_url,
                "image_url": image_url,
                "product_category": product_category,
                "unit": unit,
                "created_at": datetime.now().isoformat(),
                "record_type": "order_item",
                "search_text": search_text,
            }

            from qdrant_client.models import PointStruct

            point = PointStruct(id=item_id, vector=embedding, payload=payload)

            self.client.upsert(
                collection_name=self.order_items_collection, points=[point]
            )

            logger.info(
                f"✅ Created order item in Qdrant: {product_name} x{quantity} for order {order_id}"
            )
            return item_id

        except Exception as e:
            logger.error(f"❌ Error creating order item in Qdrant: {str(e)}")
            raise

    def get_order_items_by_order_id(self, order_id: str) -> List[Dict[str, Any]]:
        """
        Lấy tất cả items của một đơn hàng
        Tương đương SELECT * FROM order_items WHERE order_id = ?
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            filter_condition = Filter(
                must=[
                    FieldCondition(key="order_id", match=MatchValue(value=order_id)),
                    FieldCondition(
                        key="record_type", match=MatchValue(value="order_item")
                    ),
                ]
            )

            results = self.client.scroll(
                collection_name=self.order_items_collection,
                scroll_filter=filter_condition,
                limit=100,  # Giả sử không có đơn hàng nào quá 100 items
                with_payload=True,
            )

            items = []
            if results and results[0]:
                for point in results[0]:
                    items.append(point.payload)

            logger.info(f"✅ Found {len(items)} items for order: {order_id}")
            return items

        except Exception as e:
            logger.error(f"❌ Error getting order items: {str(e)}")
            return []

    def update_order_status(self, order_id: str, new_status: str) -> bool:
        """
        Cập nhật trạng thái đơn hàng
        Tương đương UPDATE orders SET status = ? WHERE order_id = ?
        """
        try:
            # Lấy order hiện tại
            order = self.get_order_by_id(order_id)
            if not order:
                logger.error(f"❌ Order not found for update: {order_id}")
                return False

            # Cập nhật payload
            order["status"] = new_status
            order["updated_at"] = datetime.now().isoformat()

            # Tạo lại embedding với thông tin mới
            search_text = f"order {order_id} {order.get('user_phone', '')} {new_status} {order.get('payment_method', '')} {order.get('notes', '')}".strip()
            embedding = self.embed_model.embed_query(search_text)
            order["search_text"] = search_text

            from qdrant_client.models import PointStruct

            point = PointStruct(id=order_id, vector=embedding, payload=order)

            self.client.upsert(collection_name=self.orders_collection, points=[point])

            logger.info(f"✅ Updated order status: {order_id} -> {new_status}")
            return True

        except Exception as e:
            logger.error(f"❌ Error updating order status: {str(e)}")
            return False

    def search_orders_by_user_phone(
        self, phone: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm đơn hàng theo số điện thoại
        Tương đương SELECT * FROM orders WHERE user_phone = ?
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            filter_condition = Filter(
                must=[
                    FieldCondition(key="user_phone", match=MatchValue(value=phone)),
                    FieldCondition(key="record_type", match=MatchValue(value="order")),
                ]
            )

            results = self.client.scroll(
                collection_name=self.orders_collection,
                scroll_filter=filter_condition,
                limit=limit,
                with_payload=True,
            )

            orders = []
            if results and results[0]:
                for point in results[0]:
                    orders.append(point.payload)

            logger.info(f"✅ Found {len(orders)} orders for phone: {phone}")
            return orders

        except Exception as e:
            logger.error(f"❌ Error searching orders by phone: {str(e)}")
            return []

    def get_full_order_details(self, order_id: str) -> Dict[str, Any]:
        """
        Lấy thông tin đầy đủ của đơn hàng bao gồm user và items
        Tương đương JOIN query
        """
        try:
            # Lấy thông tin đơn hàng
            order = self.get_order_by_id(order_id)
            if not order:
                return {"success": False, "message": "Order not found"}

            # Lấy thông tin user
            user = self.get_user_by_session_id(order.get("session_id", ""))

            # Lấy items của đơn hàng
            items = self.get_order_items_by_order_id(order_id)

            result = {
                "success": True,
                "order": order,
                "user": user,
                "items": items,
                "total_items": len(items),
            }

            logger.info(f"✅ Retrieved full order details: {order_id}")
            return result

        except Exception as e:
            logger.error(f"❌ Error getting full order details: {str(e)}")
            return {"success": False, "message": str(e)}

    def cleanup_collections(self):
        """Xóa tất cả collections (chỉ dùng để test)"""
        try:
            collections = [
                self.users_collection,
                self.orders_collection,
                self.order_items_collection,
            ]

            for collection_name in collections:
                try:
                    self.client.delete_collection(collection_name)
                    logger.info(f"🗑️ Deleted collection: {collection_name}")
                except Exception as e:
                    logger.warning(
                        f"⚠️ Could not delete collection {collection_name}: {str(e)}"
                    )

        except Exception as e:
            logger.error(f"❌ Error cleaning up collections: {str(e)}")
