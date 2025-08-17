from fastapi import APIRouter, HTTPException, Query, status, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# Import recommendation service
from app.retriever.llamaindex.self_retriever import create_enhanced_query_service
from app.services.ordered.product_recommend import (
    ProductRecommendationService,
    RecommendationRequest,
    ProductRecommendation,
    create_recommendation_service,
    create_recommendation_request,
)

# Import existing services
from app.api.v1.endpoints.vector_service import get_embed_model, get_vector_db
from app.api.v1.endpoints.ordered import order_sessions, notification_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# ==================== GLOBAL SERVICE INSTANCES ====================

recommendation_service_instance = None


def get_recommendation_service() -> ProductRecommendationService:
    global recommendation_service_instance

    if recommendation_service_instance is None:
        try:
            logger.info("🔧 Initializing ProductRecommendationService...")

            # vector/embed
            vector_db = get_vector_db()
            embed_model = get_embed_model()

            # try to create QueryRetriever
            query_service = None
            if create_enhanced_query_service:
                try:
                    # metadata_handler / llm optional - pass None if not available
                    query_service = create_enhanced_query_service(
                        vector_db=vector_db,
                        llm=None,
                        embed_model=embed_model,
                        metadata_handler=None,
                    )
                    logger.info(
                        "✅ QueryRetriever created and will be used by recommendation service"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Unable to create QueryRetriever: {e}")
                    query_service = None

            # If query_service is still None, try to ensure vector_db has _create_client
            if query_service is None:
                if hasattr(vector_db, "_create_client"):
                    try:
                        client = vector_db._create_client(read_only=True)
                        logger.info(
                            "ℹ️ Vector DB client available via wrapper._create_client()"
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ vector_db._create_client() failed: {e}")
                else:
                    logger.warning(
                        "⚠️ vector_db wrapper does not provide _create_client(); hybrid search won't work until you provide QueryRetriever or a proper vector_db wrapper"
                    )

            # connection string: set to None if you moved history to Qdrant
            connection_string = None

            recommendation_service_instance = create_recommendation_service(
                vector_db=vector_db,
                embed_model=embed_model,
                connection_string=connection_string,
                query_service=query_service,
                default_collection="dat_614943",
            )

            logger.info("✅ ProductRecommendationService initialized successfully")

        except Exception as e:
            logger.error(
                f"❌ Failed to initialize ProductRecommendationService: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Recommendation service unavailable: {str(e)}",
            )

    return recommendation_service_instance


# ==================== PYDANTIC MODELS ====================


class ProductInfo(BaseModel):
    """Product information model"""

    product_name: str = Field(..., description="Tên sản phẩm")
    unit_price: float = Field(..., description="Giá đơn vị")
    product_category: str = Field(
        default="Thực phẩm tươi sống", description="Danh mục sản phẩm"
    )
    quantity: Optional[float] = Field(1.0, description="Số lượng")
    unit: Optional[str] = Field("kg", description="Đơn vị")


class CustomerInfo(BaseModel):
    """Customer information model"""

    customer_id: Optional[str] = Field(None, description="Mã khách hàng")
    customer_name: Optional[str] = Field(None, description="Tên khách hàng")
    customer_phone: Optional[str] = Field(None, description="Số điện thoại")
    customer_email: Optional[str] = Field(None, description="Email")


class RecommendationRequestModel(BaseModel):
    """Request model for recommendations"""

    current_product: ProductInfo = Field(..., description="Thông tin sản phẩm hiện tại")
    customer_info: Optional[CustomerInfo] = Field(
        None, description="Thông tin khách hàng"
    )
    session_id: Optional[str] = Field(None, description="Session ID")
    limit: int = Field(6, description="Số lượng gợi ý tối đa", ge=1, le=20)
    include_history: bool = Field(
        False, description="Có sử dụng lịch sử mua hàng không"
    )


class SessionRecommendationRequest(BaseModel):
    """Request model for session-based recommendations"""

    session_id: str = Field(..., description="Session ID từ order")
    limit: int = Field(6, description="Số lượng gợi ý tối đa", ge=1, le=20)
    include_history: bool = Field(
        False, description="Có sử dụng lịch sử mua hàng không"
    )


class RecommendationResponse(BaseModel):
    """Response model for recommendations"""

    success: bool
    message: str
    total_found: int
    recommendations: List[Dict[str, Any]]
    strategy: Dict[str, Any]
    metadata: Dict[str, Any]
    session_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


# ==================== NOTIFICATION FUNCTIONS ====================


def send_recommendations_ready_notification(session_id: str, total_found: int):
    """Gửi notification khi có recommendations mới"""
    notification = {
        "type": "recommendations_ready",
        "title": "Gợi ý sản phẩm đã sẵn sàng! 🛒",
        "message": f"Chúng tôi có {total_found} sản phẩm tươi sống phù hợp với bạn",
        "data": {
            "total_recommendations": total_found,
            "action": "view_recommendations",
        },
        "priority": "normal",
        "category": "recommendation",
    }

    notification_manager.add_notification(session_id, notification)


# ==================== API ENDPOINTS ====================


@router.post("/generate", response_model=RecommendationResponse)
async def generate_recommendations(
    request: RecommendationRequestModel, background_tasks: BackgroundTasks
):
    """
    Tạo gợi ý sản phẩm dựa trên sản phẩm hiện tại
    Updated: Chỉ hỗ trợ danh mục "Thực phẩm tươi sống"
    """
    try:
        logger.info(
            f"🎯 Generating recommendations for: {request.current_product.product_name}"
        )

        # Get recommendation service
        rec_service = get_recommendation_service()

        # Convert pydantic models to dict
        current_product = {
            "product_name": request.current_product.product_name,
            "unit_price": request.current_product.unit_price,
            "product_category": "Thực phẩm tươi sống",  # Force to our only category
            "quantity": request.current_product.quantity,
            "unit": request.current_product.unit,
        }

        customer_info = {}
        if request.customer_info:
            customer_info = {
                "customer_id": request.customer_info.customer_id,
                "customer_name": request.customer_info.customer_name,
                "customer_phone": request.customer_info.customer_phone,
                "customer_email": request.customer_info.customer_email,
            }

        # Create recommendation request
        rec_request = create_recommendation_request(
            current_product=current_product,
            customer_info=customer_info,
            session_id=request.session_id,
            limit=request.limit,
            include_history=request.include_history,
        )

        # Generate recommendations
        result = await rec_service.get_recommendations(rec_request)

        # Send notification in background if session_id provided
        if request.session_id and result.get("success"):
            background_tasks.add_task(
                send_recommendations_ready_notification,
                request.session_id,
                result.get("total_found", 0),
            )

        return RecommendationResponse(
            success=result.get("success", False),
            message=result.get("message", "Đã tạo gợi ý sản phẩm tươi sống"),
            total_found=result.get("total_found", 0),
            recommendations=result.get("recommendations", []),
            strategy=result.get("strategy", {}),
            metadata=result.get("metadata", {}),
            session_id=request.session_id,
        )

    except Exception as e:
        logger.error(f"❌ Error generating recommendations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}",
        )


@router.post("/from-session", response_model=RecommendationResponse)
async def generate_recommendations_from_session(
    request: SessionRecommendationRequest, background_tasks: BackgroundTasks
):
    """
    Tạo gợi ý sản phẩm dựa trên session order đã tạo
    - Nếu session không tồn tại trong memory order_sessions thì fallback tìm trong Qdrant
    """
    try:
        logger.info(f"🔍 Generating recommendations from session: {request.session_id}")

        # 1) Try in-memory session first
        session_data = order_sessions.get(request.session_id)

        # 2) Fallback: try to load from Qdrant if not found in memory
        if not session_data:
            try:
                rec_service = get_recommendation_service()
                client = None

                if hasattr(rec_service.vector_db, "_create_client"):
                    try:
                        client = rec_service.vector_db._create_client(read_only=True)
                    except Exception as e:
                        logger.warning(f"Unable to create client via wrapper: {e}")
                        client = None
                else:
                    # try if vector_db itself is a QdrantClient
                    try:
                        from qdrant_client import QdrantClient

                        if isinstance(rec_service.vector_db, QdrantClient):
                            client = rec_service.vector_db
                    except Exception:
                        client = None

                logger.info(f"ℹ️ Qdrant client available: {bool(client)}")

                if client:
                    # local import of filter models (works for qdrant-client v1.x)
                    try:
                        from qdrant_client.http.models import (
                            Filter,
                            FieldCondition,
                            MatchValue,
                        )

                        filter_supported = True
                    except Exception:
                        # older/newer qdrant-client may place models differently; still try scroll fallback
                        filter_supported = False

                    # Collections to try (add any collection name you use)
                    ORDER_COLLECTIONS_TO_TRY = [
                        "orders_storage",
                        "orders",
                        "order",
                        "user_orders",
                        "user_history",
                        rec_service.default_collection,
                        "orders_collection",
                        "orders_storage",
                        "users_storage",
                    ]

                    found_point = None
                    used_collection = None

                    for coll in ORDER_COLLECTIONS_TO_TRY:
                        if not coll:
                            continue
                        logger.debug(f"Trying collection: {coll}")

                        # 1) Try filter query if supported
                        if filter_supported:
                            try:
                                flt = Filter(
                                    must=[
                                        FieldCondition(
                                            key="session_id",
                                            match=MatchValue(value=request.session_id),
                                        )
                                    ]
                                )
                                scroll_res = client.scroll(
                                    collection_name=coll,
                                    with_payload=True,
                                    with_vectors=False,
                                    limit=1,
                                    filter=flt,
                                )
                                # handle different return shapes
                                pts = (
                                    scroll_res[0]
                                    if isinstance(scroll_res, (list, tuple))
                                    and len(scroll_res) > 0
                                    else scroll_res
                                )
                                if pts:
                                    # pts might be list of points or single point
                                    candidate = (
                                        pts[0]
                                        if isinstance(pts, (list, tuple))
                                        else pts
                                    )
                                    found_point = candidate
                                    used_collection = coll
                                    logger.info(
                                        f"Found by filter in collection '{coll}'"
                                    )
                                    break
                            except Exception as e:
                                logger.debug(
                                    f"Filter query failed for collection {coll}: {e}"
                                )

                        # 2) Fallback: scroll and manual payload match (more robust)
                        try:
                            scroll_res = client.scroll(
                                collection_name=coll,
                                with_payload=True,
                                with_vectors=False,
                                limit=3000,
                            )
                            pts = None
                            if isinstance(scroll_res, tuple) and len(scroll_res) > 0:
                                pts = scroll_res[0]
                            elif isinstance(scroll_res, list):
                                # some versions return list of points
                                pts = scroll_res
                            else:
                                pts = scroll_res

                            if pts:
                                for p in pts:
                                    payload = p.payload or {}
                                    # direct equality or contained in search_text
                                    sess_val = (
                                        payload.get("session_id")
                                        or payload.get("session")
                                        or payload.get("sessionId")
                                    )
                                    if sess_val and str(sess_val) == str(
                                        request.session_id
                                    ):
                                        found_point = p
                                        used_collection = coll
                                        logger.info(
                                            f"Found by manual payload match in collection '{coll}' (key 'session_id')"
                                        )
                                        break
                                    # sometimes session_id is only in search_text
                                    search_text = str(
                                        payload.get("search_text")
                                        or payload.get("notes")
                                        or ""
                                    )
                                    if request.session_id in search_text:
                                        found_point = p
                                        used_collection = coll
                                        logger.info(
                                            f"Found by search_text match in collection '{coll}'"
                                        )
                                        break
                                if found_point:
                                    break
                        except Exception as e:
                            logger.debug(
                                f"Scroll/manual match failed for collection {coll}: {e}"
                            )
                            # try next collection

                    # If found, normalize payload into session_data
                    if found_point:
                        payload = found_point.payload or {}
                        session_data = {
                            "session_id": request.session_id,
                            "product_info": {
                                "product_name": payload.get("product_name")
                                or payload.get("product_title")
                                or (
                                    payload.get("search_text")
                                    or payload.get("notes", "")
                                )[:200],
                                "unit_price": float(
                                    payload.get(
                                        "total_amount",
                                        payload.get("unit_price", 0) or 0,
                                    )
                                ),
                                "product_category": "Thực phẩm tươi sống",  # Force to our only category
                                "quantity": float(payload.get("quantity", 1) or 1),
                                "unit": payload.get("product_price_unit", "/ kg"),
                                "image_url": payload.get(
                                    "image_url", payload.get("image", "")
                                ),
                                "product_url": payload.get("product_url", ""),
                            },
                            "order_data": {
                                "order_id": payload.get("order_id"),
                                "customer_id": payload.get("customer_id"),
                                "customer_name": payload.get("customer_name"),
                                "customer_phone": payload.get("user_phone")
                                or payload.get("customer_phone"),
                                "customer_email": payload.get("customer_email"),
                                "payment_method": payload.get("payment_method"),
                                "status": payload.get("status"),
                                "notes": payload.get("notes"),
                                "raw_payload": payload,
                            },
                            "created_at": str(
                                payload.get("created_at")
                                or payload.get("createdAt")
                                or ""
                            ),
                            "source_collection": used_collection,
                        }
                        order_sessions[request.session_id] = session_data
                        logger.info(
                            f"ℹ️ Loaded session {request.session_id} from Qdrant collection '{used_collection}' and cached in memory."
                        )
                    else:
                        logger.info(
                            "No matching point found in Qdrant collections tried."
                        )

            except Exception as e:
                logger.exception(
                    f"⚠️ Error while fetching session from Qdrant fallback: {e}"
                )

        # If still not found -> 404
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {request.session_id} not found",
            )

        # Process session data
        product_info = session_data.get("product_info", {})
        order_data = session_data.get("order_data", {})

        current_product = {
            "product_name": product_info.get("product_name", ""),
            "unit_price": float(product_info.get("unit_price", 0)),
            "product_category": "Thực phẩm tươi sống",  # Force to our only category
            "quantity": float(product_info.get("quantity", 1.0)),
            "unit": product_info.get("unit", "kg"),
        }

        customer_info = {}
        if order_data:
            customer_info = {
                "customer_id": order_data.get("customer_id"),
                "customer_name": order_data.get("customer_name"),
                "customer_phone": order_data.get("customer_phone"),
                "customer_email": order_data.get("customer_email"),
            }

        rec_service = get_recommendation_service()

        rec_request = create_recommendation_request(
            current_product=current_product,
            customer_info=customer_info,
            session_id=request.session_id,
            limit=request.limit,
            include_history=request.include_history,
        )

        result = await rec_service.get_recommendations(rec_request)

        if result.get("success"):
            background_tasks.add_task(
                send_recommendations_ready_notification,
                request.session_id,
                result.get("total_found", 0),
            )

        if result.get("metadata"):
            result["metadata"]["order_session"] = {
                "session_id": request.session_id,
                "has_order_data": bool(order_data),
                "original_text": product_info.get("original_text", "")
                or product_info.get("product_name", ""),
                "created_at": str(session_data.get("created_at", "")),
            }

        return RecommendationResponse(
            success=result.get("success", False),
            message=result.get("message", "Đã tạo gợi ý từ session"),
            total_found=result.get("total_found", 0),
            recommendations=result.get("recommendations", []),
            strategy=result.get("strategy", {}),
            metadata=result.get("metadata", {}),
            session_id=request.session_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating recommendations from session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations from session: {str(e)}",
        )


@router.get("/session/{session_id}/auto")
async def auto_recommend_after_order(
    session_id: str,
    background_tasks: BackgroundTasks,
    limit: int = Query(6, description="Số lượng gợi ý", ge=1, le=20),
    include_history: bool = Query(False, description="Sử dụng lịch sử mua hàng"),
):
    """
    Tự động tạo recommendations ngay sau khi order hoàn thành
    Endpoint này được gọi tự động bởi order system
    """
    try:
        logger.info(
            f"🤖 Auto-generating recommendations for completed order: {session_id}"
        )

        # Use the session-based recommendation
        request = SessionRecommendationRequest(
            session_id=session_id, limit=limit, include_history=include_history
        )

        result = await generate_recommendations_from_session(request, background_tasks)

        logger.info(
            f"✅ Auto-generated {result.total_found} recommendations for session {session_id}"
        )

        return result

    except Exception as e:
        logger.error(f"❌ Error in auto-recommend: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to auto-generate recommendations: {str(e)}",
        )


@router.get("/trending")
async def get_trending_products(
    limit: int = Query(10, description="Số lượng sản phẩm trending", ge=1, le=50),
    category: Optional[str] = Query(
        None, description="Chỉ hỗ trợ 'Thực phẩm tươi sống'"
    ),
):
    """
    Lấy danh sách sản phẩm trending/phổ biến trong danh mục "Thực phẩm tươi sống"
    """
    try:
        logger.info(f"📈 Getting trending fresh food products (limit: {limit})")

        rec_service = get_recommendation_service()

        # Use the trending search method with our category
        trending_products = await rec_service._search_trending_products(
            price_reference=50000, exclude_names=[], limit=limit
        )

        # Format response
        formatted_products = []
        for product in trending_products:
            formatted_products.append(
                {
                    "product_name": product.product_name,
                    "product_price": product.product_price,
                    "product_price_formatted": product.product_price_formatted,
                    "product_category": "Thực phẩm tươi sống",
                    "product_url": product.product_url,
                    "image_url": product.image_url,
                    "confidence": product.confidence,
                    "reason": product.reason,
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(
                {
                    "success": True,
                    "message": f"Tìm thấy {len(formatted_products)} sản phẩm tươi sống được ưa chuộng",
                    "total_found": len(formatted_products),
                    "category": "Thực phẩm tươi sống",
                    "products": formatted_products,
                    "timestamp": datetime.now().isoformat(),
                }
            ),
        )

    except Exception as e:
        logger.error(f"❌ Error getting trending products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trending products: {str(e)}",
        )


@router.get("/similar/{product_name}")
async def get_similar_products(
    product_name: str,
    limit: int = Query(5, description="Số lượng sản phẩm tương tự", ge=1, le=20),
    price_range: Optional[str] = Query(
        None, description="Khoảng giá (VD: 50000-100000)"
    ),
):
    """
    Tìm sản phẩm tương tự với sản phẩm cho trước trong danh mục "Thực phẩm tươi sống"
    """
    try:
        logger.info(f"🔍 Finding similar fresh food products for: {product_name}")

        rec_service = get_recommendation_service()

        # Parse price range
        price_reference = 50000
        if price_range:
            try:
                if "-" in price_range:
                    min_price, max_price = price_range.split("-")
                    price_reference = (float(min_price) + float(max_price)) / 2
                else:
                    price_reference = float(price_range)
            except ValueError:
                logger.warning(f"⚠️ Invalid price range format: {price_range}")

        # Search for similar products
        similar_products = await rec_service._search_similar_products(
            product_name=product_name, price_reference=price_reference, limit=limit
        )

        # Format response
        formatted_products = []
        for product in similar_products:
            formatted_products.append(
                {
                    "product_name": product.product_name,
                    "product_price": product.product_price,
                    "product_price_formatted": product.product_price_formatted,
                    "product_category": "Thực phẩm tươi sống",
                    "product_url": product.product_url,
                    "image_url": product.image_url,
                    "similarity_score": product.similarity_score,
                    "confidence": product.confidence,
                    "reason": product.reason,
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(
                {
                    "success": True,
                    "message": f"Tìm thấy {len(formatted_products)} sản phẩm tươi sống tương tự",
                    "query_product": product_name,
                    "total_found": len(formatted_products),
                    "products": formatted_products,
                    "search_params": {
                        "limit": limit,
                        "price_reference": price_reference,
                        "price_range": price_range,
                    },
                    "timestamp": datetime.now().isoformat(),
                }
            ),
        )

    except Exception as e:
        logger.error(f"❌ Error getting similar products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get similar products: {str(e)}",
        )


@router.get("/complementary/{product_name}")
async def get_complementary_products(
    product_name: str,
    limit: int = Query(5, description="Số lượng sản phẩm kết hợp", ge=1, le=15),
    max_price: Optional[float] = Query(
        None, description="Giá tối đa cho sản phẩm kết hợp"
    ),
):
    """
    Tìm sản phẩm kết hợp với sản phẩm cho trước
    VD: thịt -> chanh, gừng, tiêu; cá -> gừng, chanh, tiêu
    """
    try:
        logger.info(f"🥄 Finding complementary products for: {product_name}")

        rec_service = get_recommendation_service()

        # Default max price for complementary items
        max_comp_price = max_price or 100000

        # FIXED: Use the correct method name
        complementary_products = (
            await rec_service._search_enhanced_complementary_products(
                current_product_name=product_name,
                price_reference=max_comp_price,
                limit=limit,
            )
        )

        # Format response
        formatted_products = []
        for product in complementary_products:
            formatted_products.append(
                {
                    "product_name": product.product_name,
                    "product_price": product.product_price,
                    "product_price_formatted": product.product_price_formatted,
                    "product_category": "Thực phẩm tươi sống",
                    "product_url": product.product_url,
                    "image_url": product.image_url,
                    "similarity_score": product.similarity_score,
                    "confidence": product.confidence,
                    "reason": product.reason,
                    "complementary_with": product_name,
                }
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(
                {
                    "success": True,
                    "message": f"Tìm thấy {len(formatted_products)} sản phẩm kết hợp với {product_name}",
                    "base_product": product_name,
                    "total_found": len(formatted_products),
                    "products": formatted_products,
                    "search_params": {"limit": limit, "max_price": max_comp_price},
                    "complementary_logic": {
                        "meat_products": ["gà", "heo", "bò"] + ["-> gừng, chanh, tiêu"],
                        "seafood_products": ["cá", "tôm", "cua"]
                        + ["-> gừng, chanh, tiêu"],
                        "vegetables": ["rau", "củ"] + ["-> thịt, cá, tôm"],
                        "spices": ["chanh", "gừng", "tiêu"] + ["-> thịt, cá, gà"],
                    },
                    "timestamp": datetime.now().isoformat(),
                }
            ),
        )

    except Exception as e:
        logger.error(f"❌ Error getting complementary products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get complementary products: {str(e)}",
        )
