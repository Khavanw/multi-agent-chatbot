import uuid
import pytz
import logging
from datetime import datetime
from fastapi import APIRouter

from app.db.models.message import MessageResponse
from app.db.models.request_schema import ChatRequest

from app.services.agent_service import (
    DeepResearchService,
    RetrieverVectordbService,
    RetrieverMemService,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/mcp/email", response_model=MessageResponse)
async def email(request: ChatRequest):
    logger.info("Processing chat message for conversation")

    full_result = ""
    for text in DeepResearchService.run(request.content):
        full_result += text

    response = MessageResponse(
        id=uuid.uuid4(),
        content=full_result.strip(),
        conversation_id=uuid.uuid4(),
        created_at=datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")),
    )

    return response


@router.post("/mcp/google_drive", response_model=MessageResponse)
async def google_drive(request: ChatRequest):
    logger.info("Processing chat message for conversation")

    full_result = ""
    for text in RetrieverMemService.run(request.content):
        full_result += text

    response = MessageResponse(
        id=uuid.uuid4(),
        content=full_result.strip(),
        conversation_id=uuid.uuid4(),
        created_at=datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")),
    )

    return response


@router.post("/mcp/web_search", response_model=MessageResponse)
async def web_search(request: ChatRequest):
    logger.info("Processing chat message for conversation")

    full_result = ""
    for text in RetrieverMemService.run(request.content):
        full_result += text

    response = MessageResponse(
        id=uuid.uuid4(),
        content=full_result.strip(),
        conversation_id=uuid.uuid4(),
        created_at=datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")),
    )

    return response
