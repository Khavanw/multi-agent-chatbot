import asyncio
import json
import logging
import traceback
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


from app.data_loader._metadata import MetadataHandler
from app.vector_db.create_order_qdrant import QdrantOrderStorage
from app.services.ordered.user_info_collection import (
    UserInfoCollectionService,
    create_user_info_collection_service,
)
from app.services.ordered.payment_processer import PaymentProcessor, PaymentWorkflow
from app.services.ordered.product_recommend import (
    ProductRecommendationService,
    create_recommendation_service,
)

# ==================== LLAMAINDEX RETRIEVER INTEGRATION ====================
from app.retriever.llamaindex.self_retriever import (
    create_enhanced_query_service,
    ensure_serializable,
    extract_product_info_enhanced_hybrid,
    create_enhanced_fallback_product_info,
    extract_quantity_and_unit_enhanced,
)

from app.api.v1.endpoints.vector_service import (
    get_vector_db,
    get_llm,
    get_embed_model,
    validate_uuid,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== GLOBAL INSTANCES ====================
optimized_query_service_instance = None
auto_order_service_instance = None
order_manager_instance = None
user_info_service_instance = None
qdrant_order_storage_instance = None
recommendation_service_instance = None
payment_processor_instance = None
payment_workflows = {}


def invoke_query_wrapper(
    query_service, query: str, limit: int = None, use_hybrid: bool = True
):
    """
    Wrapper để gọi query_service; trả về list[dict] serializable:
    {page_content, metadata, score, id}
    """
    try:
        if hasattr(query_service, "invoke_query"):
            return query_service.invoke_query(query, limit=limit, use_hybrid=use_hybrid)
        if hasattr(query_service, "hybrid_search"):
            return query_service.hybrid_search(
                query, limit=limit, use_hybrid=use_hybrid
            )
        logger.warning(
            "invoke_query_wrapper: query_service lacks invoke_query & hybrid_search; returning empty list"
        )
        return []
    except Exception as e:
        logger.error(f"invoke_query_wrapper error: {e}")
        return []


def create_optimized_query_service(vector_db, llm, embed_model, metadata_handler):
    """FIXED: Create query service with error handling"""
    try:
        service = create_enhanced_query_service(
            vector_db=vector_db,
            llm=llm,
            embed_model=embed_model,
            metadata_handler=metadata_handler,
        )
        logger.info("✅ Enhanced QueryRetriever service created")
        return service

    except Exception as e:
        logger.error(f"❌ Failed to create Enhanced QueryRetriever service: {e}")
        raise


def get_optimized_query_service():
    """Get FIXED QueryRetriever service instance"""
    global optimized_query_service_instance

    if optimized_query_service_instance is None:
        try:
            logger.info("🔧 Creating FIXED QueryRetriever...")

            vector_db = get_vector_db()
            llm = get_llm()
            embed_model = get_embed_model()
            metadata_handler = MetadataHandler()

            optimized_query_service_instance = create_optimized_query_service(
                vector_db=vector_db,
                llm=llm,
                embed_model=embed_model,
                metadata_handler=metadata_handler,
            )

            logger.info("✅ FIXED QueryRetriever created successfully")

            # Test with serialization check
            try:
                test_results = optimized_query_service_instance.invoke_query("test")
                # Ensure results are serializable
                json.dumps(test_results)
                logger.info(
                    f"✅ FIXED test successful: {len(test_results)} serializable results"
                )
            except Exception as test_error:
                logger.warning(f"⚠️ Test failed: {test_error}")

        except Exception as e:
            logger.error(f"❌ Failed to create FIXED service: {e}")
            raise

    return optimized_query_service_instance


def get_auto_order_service():
    """Get AutoOrderCreationService - simple version"""
    global auto_order_service_instance

    if auto_order_service_instance is None:
        try:
            logger.info("🔧 Creating simple AutoOrderCreationService...")

            # Simple service that just processes results
            class SimpleAutoOrderService:
                def extract_product_from_results(self, content, results):
                    if not results:
                        return create_enhanced_fallback_product_info(
                            content, "No results"
                        )

                    return extract_quantity_and_unit_enhanced(results[0], content)

            auto_order_service_instance = SimpleAutoOrderService()
            logger.info("✅ Simple AutoOrderCreationService created")

        except Exception as e:
            logger.error(f"❌ Failed to create auto service: {e}")
            raise

    return auto_order_service_instance


def get_order_manager():
    """Get or create order manager instance"""
    global order_manager_instance
    if order_manager_instance is None:
        order_manager_instance = object()  # Replace with actual OrderManager()
    return order_manager_instance


def get_qdrant_order_storage() -> QdrantOrderStorage:
    """Get QdrantOrderStorage instance"""
    global qdrant_order_storage_instance

    if qdrant_order_storage_instance is None:
        try:
            logger.info("🔧 Initializing QdrantOrderStorage...")

            vector_db = get_vector_db()
            embed_model = get_embed_model()

            qdrant_order_storage_instance = QdrantOrderStorage(
                vector_db=vector_db, embed_model=embed_model
            )

            logger.info("✅ QdrantOrderStorage initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize QdrantOrderStorage: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Qdrant order storage unavailable: {str(e)}",
            )

    return qdrant_order_storage_instance


def get_payment_processor() -> PaymentProcessor:
    """Get payment processor instance"""
    global payment_processor_instance

    if payment_processor_instance is None:
        payment_processor_instance = PaymentProcessor()
        logger.info("✅ PaymentProcessor initialized successfully")

    return payment_processor_instance


def get_recommendation_service() -> ProductRecommendationService:
    """Get recommendation service instance"""
    global recommendation_service_instance

    if recommendation_service_instance is None:
        try:
            logger.info("🔧 Initializing ProductRecommendationService...")

            vector_db = get_vector_db()
            embed_model = get_embed_model()

            recommendation_service_instance = create_recommendation_service(
                vector_db=vector_db,
                embed_model=embed_model,
            )

            logger.info("✅ ProductRecommendationService initialized successfully")

        except Exception as e:
            logger.error(
                f"❌ Failed to initialize ProductRecommendationService: {str(e)}"
            )
            recommendation_service_instance = None

    return recommendation_service_instance


def get_user_info_service() -> UserInfoCollectionService:
    """Get user info collection service instance"""
    global user_info_service_instance

    if user_info_service_instance is None:
        user_info_service_instance = create_user_info_collection_service()
        logger.info("✅ UserInfoCollectionService initialized successfully")

    return user_info_service_instance


# ==================== NOTIFICATION SYSTEM ====================
class NotificationManager:
    """Notification management system"""

    def __init__(self):
        self.notifications = defaultdict(list)
        self.notification_callbacks = {}

    def add_notification(self, session_id: str, notification: Dict[str, Any]):
        """Add notification for session"""
        notification["id"] = str(uuid.uuid4())
        notification["timestamp"] = datetime.now().isoformat()
        notification["read"] = False

        self.notifications[session_id].append(notification)

        if session_id in self.notification_callbacks:
            try:
                callback = self.notification_callbacks[session_id]
                callback(notification)
            except Exception as e:
                logger.error(f"Error in notification callback: {e}")

        logger.info(
            f"📢 Added notification for session {session_id}: {notification['type']}"
        )

    def get_notifications(
        self, session_id: str, unread_only: bool = False
    ) -> List[Dict]:
        """Get notifications for session"""
        notifications = self.notifications.get(session_id, [])

        if unread_only:
            notifications = [n for n in notifications if not n["read"]]

        return notifications

    def mark_as_read(self, session_id: str, notification_id: str = None):
        """Mark notifications as read"""
        if session_id not in self.notifications:
            return

        if notification_id:
            for notification in self.notifications[session_id]:
                if notification["id"] == notification_id:
                    notification["read"] = True
                    break
        else:
            for notification in self.notifications[session_id]:
                notification["read"] = True

    def register_callback(self, session_id: str, callback):
        """Register callback for real-time notification"""
        self.notification_callbacks[session_id] = callback

    def unregister_callback(self, session_id: str):
        """Unregister callback"""
        if session_id in self.notification_callbacks:
            del self.notification_callbacks[session_id]

    def cleanup_session(self, session_id: str):
        """Cleanup notifications for session"""
        if session_id in self.notifications:
            del self.notifications[session_id]
        self.unregister_callback(session_id)


# Global notification manager
notification_manager = NotificationManager()

# ==================== HELPER FUNCTIONS ====================


def send_order_created_notification(session_id: str, order_data: Dict):
    """Send notification when order is created successfully"""
    notification = {
        "type": "order_created",
        "title": "Đơn hàng đã được tạo thành công! 🎉",
        "message": f"Đơn hàng #{order_data.get('order_id')} đã được tạo thành công",
        "data": {
            "order_id": order_data.get("order_id"),
            "customer_name": order_data.get("customer_name"),
            "customer_phone": order_data.get("customer_phone"),
            "customer_email": order_data.get("customer_email"),
            "customer_address": order_data.get("customer_address"),
            "product_name": order_data.get("product_name"),
            "payment_method": order_data.get("payment_method"),  # ← THÊM VÀO
            "quantity": order_data.get("quantity"),  # ← THÊM VÀO
            "unit": order_data.get("unit"),  # ← THÊM VÀO
            "unit_price": order_data.get("unit_price"),  # ← THÊM VÀO
            "total_amount": order_data.get("total_amount"),
            "status": order_data.get("status", "pending_payment"),
            "image_url": order_data.get("image_url"),  # ← THÊM VÀO
            "product_url": order_data.get("product_url"),  # ← THÊM VÀO
            "created_at": order_data.get("created_at"),  # ← THÊM VÀO
        },
        "priority": "high",
        "category": "order",
    }

    notification_manager.add_notification(session_id, notification)


def send_step_completed_notification(session_id: str, step: str, data: Dict = None):
    """Send notification when step is completed"""
    step_messages = {
        "name_collected": "Đã lưu họ tên thành công ✅",
        "phone_collected": "Đã lưu số điện thoại thành công ✅",
        "email_collected": "Đã lưu email thành công ✅",
        "address_collected": "Đã lưu địa chỉ thành công ✅",
        "info_confirmed": "Thông tin đã được xác nhận ✅",
    }

    notification = {
        "type": "step_completed",
        "title": "Hoàn thành bước",
        "message": step_messages.get(step, f"Đã hoàn thành bước: {step}"),
        "data": data or {},
        "priority": "normal",
        "category": "progress",
    }

    notification_manager.add_notification(session_id, notification)


def send_error_notification(session_id: str, error_type: str, message: str):
    """Send error notification"""
    notification = {
        "type": "error",
        "title": "Có lỗi xảy ra ❌",
        "message": message,
        "data": {"error_type": error_type},
        "priority": "high",
        "category": "error",
    }

    notification_manager.add_notification(session_id, notification)


def create_order_from_product(
    session_id: str, payment_method: str = None, payment_option: str = None
) -> str:
    """Create order directly in Vector DB"""
    logger.info(f"🔍 Creating order in Vector DB for session: {session_id}")

    try:
        session_data = order_sessions.get(session_id)
        if not session_data:
            raise ValueError(f"Session {session_id} not found")

        product_info = session_data.get("product_info", {})
        if "search_results" in product_info and product_info["search_results"]:
            search_results = product_info["search_results"]
            logger.info(
                f"🎯 Using {len(search_results)} search results (pre-sorted by enhanced retriever)"
            )
        user_info_service = get_user_info_service()
        user_session_data = user_info_service.get_session_status(session_id)
        collected_info = user_session_data.get("collected_info", {})

        qdrant_storage = get_qdrant_order_storage()

        # Create user in Vector DB
        user_data = {
            "session_id": session_id,
            "name": collected_info.get("name", ""),
            "phone": collected_info.get("phone", ""),
            "address": collected_info.get("address", ""),
            "email": collected_info.get("email", ""),
        }

        user_id = qdrant_storage.create_user(user_data)
        logger.info(f"✅ User created in Vector DB: {user_id}")

        # Create order in Vector DB
        order_data = {
            "session_id": session_id,
            "user_phone": collected_info.get("phone", ""),
            "total_amount": float(product_info.get("total_amount", 0)),
            "status": "pending_payment",
            "payment_method": payment_method or "pending",
            "payment_option": payment_option or "",
            "notes": f"Đơn hàng tạo từ chat: {product_info.get('original_text', '')}",
            "image_url": product_info.get("image_url", ""),
        }

        order_id = qdrant_storage.create_order(order_data)
        logger.info(f"✅ Order created in Vector DB: {order_id}")

        # Create order items in Vector DB
        item_data = {
            "order_id": order_id,
            "product_name": product_info.get("product_name", "Unknown"),
            "quantity": float(product_info.get("quantity", 1.0)),
            "unit_price": float(product_info.get("unit_price", 0)),
            "total_price": float(product_info.get("total_amount", 0)),
            "image_url": product_info.get("image_url", ""),
            "product_url": product_info.get("product_url", ""),
            "product_category": product_info.get("product_category", "Unknown"),
            "unit": product_info.get("unit", "kg"),
        }

        item_id = qdrant_storage.create_order_item(item_data)
        logger.info(f"✅ Order item created in Vector DB: {item_id}")

        # Update session data
        order_sessions[session_id]["order_data"] = {
            "order_id": order_id,
            "user_id": user_id,
            "item_id": item_id,
            "session_id": session_id,
            "total_amount": product_info.get("total_amount", 0),
            "product_name": product_info.get("product_name", ""),
            "quantity": product_info.get("quantity", 1.0),
            "unit": product_info.get("unit", "kg"),
            "unit_price": product_info.get("unit_price", 0),
            "status": "pending_payment",
            "payment_method": payment_method or "pending",
            "payment_option": payment_option or "",
            "customer_name": collected_info.get("name", ""),
            "customer_phone": collected_info.get("phone", ""),
            "customer_email": collected_info.get("email", ""),
            "customer_address": collected_info.get("address", ""),
            "image_url": product_info.get("image_url", ""),
            "product_url": product_info.get("product_url", ""),
            "product_category": product_info.get("product_category", ""),
            "storage_type": "vector_db",
            "created_at": datetime.now().isoformat(),
        }

        send_order_created_notification(
            session_id, order_sessions[session_id]["order_data"]
        )

        logger.info(f"🎉 Order created successfully in Vector DB: {order_id}")
        return order_id

    except Exception as e:
        logger.error(f"❌ create_order_from_product failed: {str(e)}")
        import traceback

        logger.error(f"❌ Full traceback:\n{traceback.format_exc()}")
        raise Exception(f"Lỗi khi tạo đơn hàng trong Vector DB: {str(e)}")


async def generate_recommendations_for_session(session_id: str):
    """Generate recommendations for session via HTTP API call"""
    try:
        logger.info(f"🎯 Generating recommendations for session: {session_id}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"http://localhost:8000/api/v1/recommendations/session/{session_id}/auto",
                params={"limit": 6, "include_history": False},
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(
                    f"✅ Generated {result.get('total_found', 0)} recommendations for session {session_id}"
                )
                return result
            else:
                logger.error(
                    f"❌ Recommendation API failed: {response.status_code} - {response.content}"
                )
                return {
                    "success": False,
                    "error": f"API call failed with status {response.status_code}",
                }

    except httpx.TimeoutException:
        logger.error(f"⏰ Timeout calling recommendation API for session: {session_id}")
        return {"success": False, "error": "Recommendation service timeout"}

    except httpx.RequestError as e:
        logger.error(f"🌐 Network error calling recommendation API: {str(e)}")
        return {"success": False, "error": "Network error"}

    except Exception as e:
        logger.error(f"❌ Error generating recommendations: {str(e)}")
        return {"success": False, "error": str(e)}


# ==================== SESSION STORAGE ====================
order_sessions = {}


# ==================== PYDANTIC MODELS ====================
class OrderRequest(BaseModel):
    content: str = Field(
        ...,
        description="Mô tả đơn hàng (VD: 'mua 2 kg đùi gà')",
        min_length=1,
        max_length=500,
    )


# session_id: Optional[str] = Field(None, description="Session ID (tự tạo nếu không có)")


class UserInfoRequest(BaseModel):
    # session_id: str = Field(..., description="Session ID")
    content: str = Field(..., description="Thông tin user nhập vào")


class OrderResponse(BaseModel):
    success: bool
    message: str
    type: str
    session_id: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class NotificationResponse(BaseModel):
    notifications: List[Dict[str, Any]]
    total: int
    unread: int


class PaymentRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    content: str = Field(..., description="Lựa chọn phương thức thanh toán")


def get_or_create_session_id(request_headers=None) -> str:
    """
    Get session_id from various sources or create new one
    Priority: Header > Cookie > New UUID
    """
    # Method 1: From X-Session-ID header
    if request_headers:
        session_id = request_headers.get("x-session-id") or request_headers.get(
            "X-Session-ID"
        )
        if session_id and session_id.strip():
            logger.info(f"📋 Using session_id from header: {session_id}")
            return session_id.strip()

    # Method 2: Generate new UUID
    new_session_id = str(uuid.uuid4())
    logger.info(f"🆕 Generated new session_id: {new_session_id}")
    return new_session_id


def find_active_session_for_continue(request_headers=None) -> Optional[str]:
    """
    Find active session for continue operation
    Returns None if no session found
    """
    # Method 1: From header
    if request_headers:
        session_id = request_headers.get("x-session-id") or request_headers.get(
            "X-Session-ID"
        )
        if session_id and session_id.strip():
            session_id = session_id.strip()
            if session_id in order_sessions:
                logger.info(f"✅ Found active session from header: {session_id}")
                return session_id
            else:
                logger.warning(
                    f"⚠️ Session from header not found in active sessions: {session_id}"
                )

    # Method 2: Find most recent active session (fallback)
    if order_sessions:
        # Get most recently updated session
        latest_session = max(
            order_sessions.items(),
            key=lambda x: x[1].get("last_activity", x[1].get("created_at", "")),
        )
        logger.info(f"🔍 Using most recent active session: {latest_session[0]}")
        return latest_session[0]

    return None


# ==================== API ENDPOINTS ====================
@router.post("/create", response_model=OrderResponse)
async def initiate_order_unified(request: OrderRequest, http_request: Request):
    """FIXED: Initiate order creation with auto session management"""
    try:
        logger.info(f"🚀 Initiating FIXED order: {request.content}")

        get_optimized_query_service()  # Ensure services are initialized
        user_info_service = get_user_info_service()

        # Auto-generate session_id (no input required)
        session_id = get_or_create_session_id(http_request.headers)

        logger.info("🔍 STEP 1: About to call FIXED unified extraction")

        # Use the FIXED extraction function
        query_service = get_optimized_query_service()
        auto_service = get_auto_order_service()

        # FIXED: Use serializable version
        product_info = extract_product_info_enhanced_hybrid(
            request.content,
            query_service,
            auto_service,
            use_hybrid=True,  # ← ENABLE HYBRID SEARCH
        )
        logger.info("🔍 STEP 2: FIXED extraction completed")
        logger.info(f"🔍 Result: {product_info.get('product_name', 'N/A')}")

        # ENSURE product_info is fully serializable
        serializable_product_info = ensure_serializable(product_info)

        # Save order session info
        order_sessions[session_id] = {
            "session_id": session_id,
            "product_info": serializable_product_info,
            "created_at": datetime.now().isoformat(),  # Make datetime serializable
            "last_activity": datetime.now().isoformat(),
        }

        # Initialize user info collection session
        collection_result = user_info_service.init_collection_session(
            session_id, serializable_product_info
        )

        logger.info(
            f"📦 FIXED Product extracted: {serializable_product_info['product_name']} - {serializable_product_info['quantity']} {serializable_product_info['unit']}"
        )

        # ENSURE response data is serializable
        response_data = {
            "product_info": serializable_product_info,
            "next_step": "Cung cấp họ tên",
            "state": collection_result["state"],
            "search_method": "unified_llamaindex_fixed_serializable",
            "unified_llamaindex_enabled": True,
            "session_management": "auto_generated",  # Indicate auto session management
        }

        return OrderResponse(
            success=collection_result["success"],
            message=f"{collection_result['message']}",
            type=collection_result["type"],
            session_id=session_id,
            data=response_data,
        )

    except Exception as e:
        logger.error(f"❌ Error in FIXED order initiation: {str(e)}")
        logger.error(f"❌ Traceback:\n{traceback.format_exc()}")

        # Generate fallback session_id for error response
        fallback_session_id = str(uuid.uuid4())

        # Return error response that's definitely serializable
        return OrderResponse(
            success=False,
            message=f"Lỗi xử lý đơn hàng: {str(e)}",
            type="error",
            session_id=fallback_session_id,
            data={
                "error": str(e),
                "error_type": "serialization_or_processing_error",
                "fallback_used": True,
                "session_management": "auto_generated",
            },
        )


@router.post("/continue", response_model=OrderResponse)
async def continue_order(request: UserInfoRequest, http_request: Request):
    """Continue order process - with auto session detection"""
    try:
        content = request.content.strip()

        # Auto-detect session_id (no input required)
        session_id = find_active_session_for_continue(http_request.headers)

        if not session_id:
            logger.error("❌ No active session found")
            return OrderResponse(
                success=False,
                message="❌ **Không tìm thấy phiên làm việc nào đang hoạt động**\n\nVui lòng:\n\n1️⃣ **Bắt đầu đơn hàng mới** bằng cách gọi `/create`\n2️⃣ **Hoặc** cung cấp Session ID trong header `X-Session-ID`\n\n💡 _Mỗi đơn hàng cần một phiên làm việc để theo dõi tiến trình._",
                type="no_active_session",
                session_id="",
                data={
                    "error": "no_active_session",
                    "suggested_action": "create_new_order",
                    "available_sessions": (
                        list(order_sessions.keys()) if order_sessions else []
                    ),
                },
            )

        # Check session exists
        if session_id not in order_sessions:
            logger.error(f"❌ Session NOT found: {session_id}")
            return OrderResponse(
                success=False,
                message=f"❌ **Phiên làm việc đã hết hạn hoặc không tồn tại**\n\nSession ID: `{session_id}`\n\nVui lòng bắt đầu đơn hàng mới.",
                type="session_not_found",
                session_id=session_id,
                data={"expired_session_id": session_id},
            )

        # Update last activity
        order_sessions[session_id]["last_activity"] = datetime.now().isoformat()
        logger.info(f"✅ Processing session: {session_id}")

        # Handle payment workflow (highest priority)
        if session_id in payment_workflows:
            logger.info("💳 Processing payment workflow...")

            try:
                payment_workflow = payment_workflows[session_id]
                product_info = order_sessions[session_id]["product_info"]
                order_amount = float(product_info.get("total_amount", 0))

                payment_result = payment_workflow.process_user_input(
                    content, order_amount
                )

                logger.info(
                    f"🔍 Payment result: success={payment_result.get('success')}"
                )

                if payment_result.get("success"):
                    next_step = payment_result.get("next_step", "")
                    payment_method = payment_result.get("payment_method", "")

                    should_create_order = (
                        next_step == "order_confirmation"
                        or next_step == "payment_confirmation"
                        or payment_method == "cod"
                    )

                    if should_create_order:
                        # Create order in database
                        try:
                            logger.info("🏗️ Creating order in database...")

                            payment_data = payment_workflow.get_payment_data()
                            final_payment_method = payment_data.get(
                                "method", payment_method
                            )

                            payment_option_obj = payment_data.get("option")
                            if hasattr(payment_option_obj, "display_name"):
                                final_payment_option = payment_option_obj.display_name
                            elif isinstance(payment_option_obj, dict):
                                final_payment_option = payment_option_obj.get(
                                    "display_name", str(payment_option_obj)
                                )
                            else:
                                final_payment_option = (
                                    str(payment_option_obj)
                                    if payment_option_obj
                                    else final_payment_method.upper()
                                )

                            order_id = create_order_from_product(
                                session_id=session_id,
                                payment_method=final_payment_method,
                                payment_option=final_payment_option,
                            )

                            logger.info(f"✅ Order created successfully: {order_id}")

                            # Generate recommendations in background
                            asyncio.create_task(
                                generate_recommendations_for_session(session_id)
                            )

                            order_data = order_sessions[session_id].get(
                                "order_data", {}
                            )

                            # Cleanup sessions
                            user_info_service = get_user_info_service()
                            user_info_service.cleanup_session(session_id)
                            del payment_workflows[session_id]
                            logger.info("🧹 Cleaned up sessions")

                            # Format currency helper
                            def safe_format_currency(value):
                                try:
                                    if isinstance(value, str):
                                        clean_value = (
                                            value.replace(",", "")
                                            .replace("VND", "")
                                            .replace("₫", "")
                                            .strip()
                                        )
                                        num_value = float(clean_value)
                                    elif isinstance(value, (int, float)):
                                        num_value = float(value)
                                    else:
                                        num_value = 0.0
                                    return f"{num_value:,.0f}"
                                except (ValueError, TypeError):
                                    return "0"

                            # Success response
                            success_message = f"""🎉 **ĐƠN HÀNG ĐÃ ĐƯỢC TẠO THÀNH CÔNG!**

📋 **Mã đơn hàng:** {order_id}
🔑 **Session ID:** `{session_id}`

👤 **Thông tin khách hàng:**
• Họ tên: {order_data.get('customer_name', '')}
• Điện thoại: {order_data.get('customer_phone', '')}
• Email: {order_data.get('customer_email', '')}
• Địa chỉ: {order_data.get('customer_address', '')}

🛒 **Thông tin sản phẩm:**
• Sản phẩm: {order_data.get('product_name', '')}
• Số lượng: {order_data.get('quantity', '')} {order_data.get('unit', '')}
• Tổng tiền: {safe_format_currency(order_data.get('total_amount', '0'))} VND

💳 **Phương thức thanh toán:** {final_payment_option}

📞 **Chúng tôi sẽ liên hệ xác nhận và giao hàng trong thời gian sớm nhất!**

_Cảm ơn bạn đã tin tưởng và mua hàng! 🙏_

🚀 **Unified LlamaIndex Enhanced Search** được sử dụng để tìm sản phẩm tốt nhất cho bạn!"""

                            return OrderResponse(
                                success=True,
                                message=success_message,
                                type="order_completed",
                                session_id=session_id,
                                data={
                                    "order_id": order_id,
                                    "order_data": order_data,
                                    "payment_method": final_payment_method,
                                    "payment_option": final_payment_option,
                                    "workflow_completed": True,
                                    "unified_llamaindex_powered": True,
                                    "search_method": product_info.get(
                                        "extraction_method", "unified_llamaindex_v2"
                                    ),
                                    "session_management": "auto_detected",
                                },
                            )

                        except Exception as order_error:
                            logger.error(
                                f"❌ Error creating order after payment: {str(order_error)}"
                            )
                            send_error_notification(
                                session_id, "order_creation_error", str(order_error)
                            )

                            return OrderResponse(
                                success=False,
                                message=f"❌ Thanh toán đã được xử lý nhưng không thể tạo đơn hàng.\n\nLỗi: {str(order_error)}\n\n📞 Vui lòng liên hệ hỗ trợ để được giải quyết.",
                                type="order_creation_failed",
                                session_id=session_id,
                                data={"error": str(order_error)},
                            )

                    else:
                        # Still in payment process
                        logger.info("💳 Still in payment process...")

                        # Determine payment type for UI
                        if (
                            payment_workflow.current_step
                            == "waiting_for_payment_method"
                        ):
                            payment_type = "payment_selection"
                        else:
                            payment_type = "payment_confirmation"

                        return OrderResponse(
                            success=payment_result.get("success", True),
                            message=payment_result.get(
                                "message", "Đang xử lý thanh toán..."
                            ),
                            type=payment_type,
                            session_id=session_id,
                            data={
                                "current_state": getattr(
                                    payment_workflow, "current_step", "unknown"
                                ),
                                "payment_method": payment_method,
                                "next_step": next_step,
                                "requires_confirmation": next_step
                                == "payment_confirmation",
                                "session_management": "auto_detected",
                            },
                        )

                else:
                    # Payment failed
                    logger.warning("⚠️ Payment processing failed")

                    return OrderResponse(
                        success=False,
                        message=payment_result.get(
                            "message",
                            "❌ Có lỗi trong quá trình thanh toán. Vui lòng thử lại.",
                        ),
                        type="payment_error",
                        session_id=session_id,
                        data={
                            "error": "payment_processing_failed",
                            "can_retry": True,
                            "session_management": "auto_detected",
                        },
                    )

            except Exception as payment_error:
                logger.error(f"❌ Payment workflow error: {str(payment_error)}")
                import traceback

                logger.error(f"❌ Payment traceback:\n{traceback.format_exc()}")

                return OrderResponse(
                    success=False,
                    message=f"❌ Lỗi xử lý thanh toán: {str(payment_error)}\n\n🔄 Vui lòng thử lại hoặc chọn phương thức thanh toán khác.",
                    type="payment_system_error",
                    session_id=session_id,
                    data={"error": str(payment_error)},
                )

        # Handle user info collection workflow
        logger.info("👤 Processing user info collection...")

        user_info_service = get_user_info_service()

        # Check if user info collection session exists
        session_status = user_info_service.get_session_status(session_id)
        if not session_status["exists"]:
            logger.info("🔄 Recreating user info session...")
            # Recreate session from order info
            product_info = order_sessions[session_id]["product_info"]
            collection_result = user_info_service.init_collection_session(
                session_id, product_info
            )

            return OrderResponse(
                success=collection_result["success"],
                message=collection_result["message"],
                type=collection_result["type"],
                session_id=session_id,
                data={
                    "state": collection_result["state"],
                    "session_management": "auto_detected",
                },
            )

        # Process user response
        result = user_info_service.process_user_response(session_id, content)

        # Send notifications for completed steps
        if result.get("success") and result.get("type") in [
            "asking_phone",  # Đã thu thập tên → chuyển hỏi điện thoại
            "asking_address",  # Đã thu thập điện thoại → chuyển hỏi địa chỉ
            "asking_email",  # Đã thu thập địa chỉ → chuyển hỏi email
            "confirming_info",
        ]:
            step_mapping = {
                "asking_phone": "name_collected",
                "asking_address": "phone_collected",
                "asking_email": "address_collected",
                "confirming_info": "emai_collected",
            }
            step = step_mapping.get(result.get("type"))
            if step:
                send_step_completed_notification(session_id, step)

        # Handle transition from info collection to payment
        if result.get("type") == "info_confirmed":
            try:
                logger.info("✅ Info confirmed, starting payment process...")
                send_step_completed_notification(session_id, "info_confirmed")

                # Get order amount
                product_info = order_sessions[session_id]["product_info"]
                order_amount = float(product_info.get("total_amount", 0))

                # Initialize payment workflow
                payment_processor = get_payment_processor()
                payment_workflow = PaymentWorkflow(payment_processor)
                payment_workflows[session_id] = payment_workflow

                # Start payment process
                payment_message = payment_workflow.start_payment_process(order_amount)

                logger.info("💳 Payment workflow initialized successfully")

                # Enhanced message with Unified LlamaIndex info
                enhanced_message = f"""✅ **Thông tin đã xác nhận thành công!**

🚀 **Sản phẩm được tìm kiếm bằng Unified LlamaIndex AI** để đảm bảo độ chính xác cao nhất!

{payment_message}"""

                return OrderResponse(
                    success=True,
                    message=enhanced_message,
                    type="payment_selection",
                    session_id=session_id,
                    data={
                        "state": "selecting_payment_method",
                        "order_amount": order_amount,
                        "next_step": "Chọn phương thức thanh toán",
                        "payment_workflow_started": True,
                        "unified_llamaindex_search_used": True,
                        "search_method": product_info.get(
                            "extraction_method", "unified_llamaindex_v2"
                        ),
                        "session_management": "auto_detected",
                    },
                )

            except Exception as payment_init_error:
                logger.error(f"❌ Error initiating payment: {str(payment_init_error)}")
                send_error_notification(
                    session_id, "payment_init_error", str(payment_init_error)
                )

                return OrderResponse(
                    success=False,
                    message=f"❌ Thông tin đã được xác nhận nhưng không thể khởi tạo thanh toán.\n\nLỗi: {str(payment_init_error)}\n\n🔄 Vui lòng thử lại.",
                    type="payment_init_failed",
                    session_id=session_id,
                    data={"error": str(payment_init_error)},
                )

        # Regular case - return user info collection result
        logger.info(f"📝 Regular info collection response: {result.get('type')}")

        return OrderResponse(
            success=result.get("success", True),
            message=result.get("message", "Đã xử lý thành công"),
            type=result.get("type", "info_collection"),
            session_id=session_id,
            data={**result.get("data", {}), "session_management": "auto_detected"},
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"❌ Fatal error in continue_order: {str(e)}")
        import traceback

        logger.error(f"❌ Full traceback:\n{traceback.format_exc()}")

        # Try to get session_id for error notification
        session_id_for_error = ""
        try:
            session_id_for_error = (
                find_active_session_for_continue(http_request.headers) or ""
            )
            if session_id_for_error:
                send_error_notification(session_id_for_error, "system_error", str(e))
        except:
            pass  # Don't let notification errors crash the response

        # Ensure we always return a valid response
        return OrderResponse(
            success=False,
            message=f"❌ **Lỗi hệ thống không mong muốn**\n\nChi tiết: {str(e)}\n\n🔄 Vui lòng thử lại hoặc bắt đầu lại từ đầu.\n\n📞 Nếu lỗi vẫn tiếp tục, vui lòng liên hệ hỗ trợ.",
            type="system_error",
            session_id=session_id_for_error,
            data={
                "error_details": str(e),
                "timestamp": datetime.now().isoformat(),
                "can_retry": True,
                "suggested_action": "restart_order",
                "session_management": "auto_detected",
            },
        )


# ==================== DEBUG AND STATUS ENDPOINTS ====================


@router.get("/debug/unified-status")
async def debug_unified_status():
    """Debug endpoint to check Unified LlamaIndex integration status"""
    try:
        status_info = {
            "unified_llamaindex_integration": True,
            "services": {},
            "test_results": {},
        }

        # Test QueryRetriever
        try:
            query_service = get_optimized_query_service()
            status_info["services"]["query_service"] = {
                "status": "initialized",
                "type": type(query_service).__name__,
                "collection_name": getattr(query_service, "collection_name", "unknown"),
            }

            # Test search
            test_results = query_service.invoke_query("thịt gà")
            status_info["test_results"]["search_test"] = {
                "success": True,
                "results_count": len(test_results),
                "top_result": test_results[0].page_content if test_results else None,
            }

        except Exception as e:
            status_info["services"]["query_service"] = {
                "status": "failed",
                "error": str(e),
            }

        # Test AutoOrderService
        try:
            auto_service = get_auto_order_service()
            status_info["services"]["auto_order_service"] = {
                "status": "initialized",
                "type": type(auto_service).__name__,
            }
        except Exception as e:
            status_info["services"]["auto_order_service"] = {
                "status": "failed",
                "error": str(e),
            }

        # Test unified product extraction
        try:
            query_service = get_optimized_query_service()
            auto_service = get_auto_order_service()
            test_product = extract_product_info_enhanced_hybrid(
                "mua 1 kg thịt gà", query_service, auto_service
            )

            status_info["test_results"]["unified_product_extraction"] = {
                "success": True,
                "product_name": test_product.get("product_name"),
                "extraction_method": test_product.get("extraction_method"),
            }
        except Exception as e:
            status_info["test_results"]["unified_product_extraction"] = {
                "success": False,
                "error": str(e),
            }

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "status_info": status_info,
                "unified_integration_complete": all(
                    service.get("status") == "initialized"
                    for service in status_info["services"].values()
                ),
                "unified_llamaindex_benefits": [
                    "Single unified extraction function eliminates code duplication",
                    "Consistent search method across all endpoints",
                    "Improved error handling and fallback mechanisms",
                    "Enhanced Vietnamese language support",
                    "Better semantic search with hybrid ranking",
                ],
            },
        )

    except Exception as e:
        logger.error(f"❌ Unified status check failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            },
        )


def send_order_created_notification_enhanced(session_id: str, order_data: Dict):
    """Enhanced version with better formatting and error handling"""

    # Helper function to safely format currency
    def safe_format_currency(value):
        try:
            if isinstance(value, str):
                clean_value = (
                    value.replace(",", "").replace("VND", "").replace("₫", "").strip()
                )
                num_value = float(clean_value)
            elif isinstance(value, (int, float)):
                num_value = float(value)
            else:
                num_value = 0.0
            return f"{num_value:,.0f} VND"
        except (ValueError, TypeError):
            return "0 VND"

    # Helper function to safely get value
    def safe_get(key, default=""):
        return order_data.get(key, default) or default

    # Format detailed message
    detailed_message = f"""📋 **Chi tiết đơn hàng:**
• Mã đơn: #{safe_get('order_id')}
• Khách hàng: {safe_get('customer_name')}
• Sản phẩm: {safe_get('product_name')} 
• Số lượng: {safe_get('quantity', '1')} {safe_get('unit', 'kg')}
• Tổng tiền: {safe_format_currency(safe_get('total_amount', 0))}
• Thanh toán: {safe_get('payment_method', 'Chưa xác định')}
• Trạng thái: {safe_get('status', 'pending_payment')}"""

    notification = {
        "type": "order_created",
        "title": "Đơn hàng đã được tạo thành công! 🎉",
        "message": detailed_message,  # ← SỬ DỤNG MESSAGE CHI TIẾT
        "data": {
            "order_id": safe_get("order_id"),
            "customer_name": safe_get("customer_name"),
            "customer_phone": safe_get("customer_phone"),
            "customer_email": safe_get("customer_email"),
            "customer_address": safe_get("customer_address"),
            "product_name": safe_get("product_name"),
            "payment_method": safe_get("payment_method"),
            "quantity": safe_get("quantity"),
            "unit": safe_get("unit"),
            "unit_price": safe_get("unit_price"),
            "total_amount": safe_get("total_amount"),
            "status": safe_get("status", "pending_payment"),
            "image_url": safe_get("image_url"),
            "product_url": safe_get("product_url"),
            "product_category": safe_get("product_category"),
            "created_at": safe_get("created_at"),
            "formatted_total": safe_format_currency(
                safe_get("total_amount", 0)
            ),  # ← THÊM FORMATTED VERSION
        },
        "priority": "high",
        "category": "order",
        "actions": [  # ← THÊM CÁC ACTION CÓ THỂ THỰC HIỆN
            {"id": "view_order", "label": "Xem chi tiết", "type": "view"},
            {"id": "track_order", "label": "Theo dõi đơn hàng", "type": "track"},
        ],
    }

    try:
        notification_manager.add_notification(session_id, notification)
        logger.info(f"✅ Enhanced order notification sent for session: {session_id}")
    except Exception as e:
        logger.error(f"❌ Failed to send order notification: {str(e)}")
        # Fallback to basic notification
        basic_notification = {
            "type": "order_created",
            "title": "Đơn hàng đã được tạo! 🎉",
            "message": f"Đơn hàng #{safe_get('order_id')} đã được tạo thành công",
            "data": {"order_id": safe_get("order_id")},
            "priority": "high",
            "category": "order",
        }
        notification_manager.add_notification(session_id, basic_notification)


# ==================== NOTIFICATION ENDPOINTS ====================
@router.get("/notifications/{session_id}", response_model=NotificationResponse)
async def get_notifications_enhanced(
    session_id: str,
    unread_only: bool = False,
    category: str = Query(
        None, description="Filter by category: order, progress, error"
    ),
    limit: int = Query(50, description="Maximum number of notifications"),
):
    """Enhanced notifications endpoint with filtering"""
    try:
        # Validate session_id
        if not validate_uuid(session_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session ID format",
            )

        # Get all notifications for session
        notifications = notification_manager.get_notifications(session_id, unread_only)

        # Apply category filter if specified
        if category:
            notifications = [n for n in notifications if n.get("category") == category]

        # Sort by timestamp (newest first)
        notifications = sorted(
            notifications, key=lambda x: x.get("timestamp", ""), reverse=True
        )

        # Apply limit
        notifications = notifications[:limit]

        # Calculate statistics
        all_notifications = notification_manager.get_notifications(session_id)
        unread_count = len([n for n in all_notifications if not n.get("read", True)])

        # Group by category for statistics
        category_stats = {}
        for notif in all_notifications:
            cat = notif.get("category", "other")
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "unread": 0}
            category_stats[cat]["total"] += 1
            if not notif.get("read", True):
                category_stats[cat]["unread"] += 1

        response_data = {
            "notifications": notifications,
            "total": len(notifications),
            "unread": unread_count,
            "category_stats": category_stats,
            "filters_applied": {
                "unread_only": unread_only,
                "category": category,
                "limit": limit,
            },
            "session_id": session_id,
        }

        return NotificationResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting enhanced notifications: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notifications: {str(e)}",
        )


@router.post("/notifications/{session_id}/mark-read")
async def mark_notifications_read(
    session_id: str, notification_id: Optional[str] = None
):
    """Mark notifications as read"""
    try:
        notification_manager.mark_as_read(session_id, notification_id)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Đã đánh dấu notification(s) đã đọc",
                "session_id": session_id,
                "notification_id": notification_id,
            },
        )

    except Exception as e:
        logger.error(f"❌ Error marking notifications as read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notifications as read: {str(e)}",
        )


# ==================== HEALTH CHECK ====================


@router.get("/health")
async def health_check():
    """Health check with Unified LlamaIndex integration"""
    user_info_service = get_user_info_service()

    # Check Unified LlamaIndex service
    unified_service_status = (
        "initialized" if optimized_query_service_instance else "not_initialized"
    )

    # Check recommendation service
    rec_service_status = (
        "initialized" if recommendation_service_instance else "not_initialized"
    )

    # Statistics
    total_notifications = sum(
        len(notifications)
        for notifications in notification_manager.notifications.values()
    )
    active_webhooks = len(notification_manager.notification_callbacks)

    # Test unified extraction method
    try:
        query_service = get_optimized_query_service()
        auto_service = get_auto_order_service()
        test_result = extract_product_info_enhanced_hybrid(
            "test sản phẩm", query_service, auto_service
        )
        extraction_status = "working"
        extraction_method = test_result.get("extraction_method", "unknown")
    except Exception as e:
        extraction_status = f"error: {str(e)}"
        extraction_method = "failed"

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "order_with_unified_llamaindex",
            "active_order_sessions": len(order_sessions),
            "active_user_info_sessions": (
                len(user_info_service.user_sessions)
                if hasattr(user_info_service, "user_sessions")
                else 0
            ),
            "notification_stats": {
                "total_notifications": total_notifications,
                "sessions_with_notifications": len(notification_manager.notifications),
                "active_webhooks": active_webhooks,
            },
            "services": {
                "unified_llamaindex_query_service": unified_service_status,
                "auto_order_service": (
                    "initialized" if auto_order_service_instance else "not_initialized"
                ),
                "user_info_service": (
                    "initialized" if user_info_service_instance else "not_initialized"
                ),
                "order_manager": (
                    "initialized" if order_manager_instance else "not_initialized"
                ),
                "notification_manager": "initialized",
                "unified_extraction": extraction_status,
                "extraction_method": extraction_method,
                "recommendation_service": rec_service_status,
            },
            "endpoints": [
                "POST /create - Khởi tạo đơn hàng với Unified LlamaIndex",
                "POST /continue - Tiếp tục quy trình",
                "GET /debug/unified-status - Kiểm tra Unified status",
                "GET /notifications/{id} - Lấy notifications",
                "GET /health - Health check với Unified stats",
            ],
            "features": {
                "unified_llamaindex_search": "enabled",
                "semantic_search": "enabled",
                "hybrid_ranking": "enabled",
                "llm_query_understanding": "enabled",
                "auto_service_integration": "enabled",
                "multi_tier_fallback": "enabled",
                "single_extraction_function": "enabled",
            },
        },
    )


# ==================== QUICK TEST ===================
@router.post("/quick-test-unified")
async def quick_test_unified():
    """Quick test endpoint for Unified API"""
    try:
        # Step 1: Create order with Unified LlamaIndex
        create_request = OrderRequest(content="mua 2 kg đùi gà")
        create_response = await initiate_order_unified(create_request)

        if not create_response.success:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Failed to create order with Unified LlamaIndex",
                    "details": create_response.dict(),
                },
            )

        session_id = create_response.session_id

        # Step 2-6: Auto complete user info steps
        info_steps = [
            ("Đạt", "name"),
            ("0901234567", "phone"),
            ("unified@gmail.com", "email"),
            ("123 Unified Street, District 1, Ho Chi Minh City", "address"),
            ("đúng", "confirm"),
        ]

        responses = {"1_create": create_response.dict()}

        for i, (content, step_name) in enumerate(info_steps, 2):
            request = UserInfoRequest(session_id=session_id, content=content)
            response = await continue_order(request)
            responses[f"{i}_{step_name}"] = response.dict()

            if not response.success and step_name != "confirm":
                break

            # If payment selection started, break to handle separately
            if response.type == "payment_selection":
                break

        # Step 7: Handle payment selection (if reached)
        if session_id in payment_workflows:
            payment_request = UserInfoRequest(session_id=session_id, content="cod")
            payment_response = await continue_order(payment_request)
            responses["7_payment"] = payment_response.dict()

        # Get notifications after completion
        notifications = notification_manager.get_notifications(session_id)

        # Check Unified status
        unified_status = await debug_unified_status()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(
                {
                    "success": True,
                    "message": "Quick test with Unified LlamaIndex completed successfully",
                    "session_id": session_id,
                    "steps": responses,
                    "final_order": responses.get(
                        "7_payment", responses.get("6_confirm", {})
                    ).get("data"),
                    "notifications": {
                        "total": len(notifications),
                        "list": notifications,
                    },
                    "unified_llamaindex_integration": {
                        "enabled": True,
                        "search_method": create_response.data.get(
                            "search_method", "unified_llamaindex_hybrid_search"
                        ),
                        "product_found": create_response.data.get(
                            "product_info", {}
                        ).get("product_name", "N/A"),
                        "extraction_method": create_response.data.get(
                            "product_info", {}
                        ).get("extraction_method", "unified_llamaindex_v2"),
                    },
                    "payment_workflow_used": session_id in payment_workflows,
                    "payment_completed": session_id not in payment_workflows,
                    "unified_status": unified_status.status_code == 200,
                }
            ),
        )

    except Exception as e:
        logger.error(f"❌ Quick Unified test failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "Quick Unified test failed",
                "details": str(e),
            },
        )
