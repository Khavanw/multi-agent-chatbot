from fastapi import APIRouter

from .endpoints import (
    chat,
    evaluate,
    health,
    history,
    mcp,
    noti_email,
    noti_telegram,
    ordered,
    recommend,
)

api_router = APIRouter(prefix="/v1")

# Include all API endpoint routers
api_router.include_router(chat.router, tags=["agent"])
api_router.include_router(evaluate.router, tags=["evaluate"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(history.router, tags=["history"])
api_router.include_router(mcp.router, tags=["mcp"])
api_router.include_router(noti_email.router, tags=["notification email"])
api_router.include_router(noti_telegram.router, tags=["notification_telegram"])
api_router.include_router(ordered.router, tags=["orders"])
api_router.include_router(recommend.router, tags=["recommendation"])
