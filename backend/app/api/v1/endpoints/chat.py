import os
import uuid
import pytz
import logging
import tempfile
import shutil
from datetime import datetime
from fastapi import APIRouter, UploadFile, File

from app.db.models.message import MessageResponse
from app.db.models.request_schema import ChatRequest, VoiceRequest
from app.tools.stt_agent import SttAgent
from app.services.agent_service import (
    DeepResearchService,
    RetrieverVectordbService,
    RetrieverMemService,
    WebSearchService,
    AgentSupervisorService,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/agent/deep_research", response_model=MessageResponse)
async def deep_research(request: ChatRequest):
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


@router.post("/agent/web_search", response_model=MessageResponse)
async def web_search(request: ChatRequest):
    logger.info("Processing chat message for conversation")

    full_result = ""
    for text in WebSearchService.run(request.content):
        full_result += text

    response = MessageResponse(
        id=uuid.uuid4(),
        content=full_result.strip(),
        conversation_id=uuid.uuid4(),
        created_at=datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")),
    )

    return response


@router.post("/agent/chat_supervisor", response_model=MessageResponse)
async def chat_supervisor(request: ChatRequest):
    logger.info("Processing chat message for conversation")

    full_result = ""
    for text in AgentSupervisorService.run(request.content):
        full_result += text

    response = MessageResponse(
        id=uuid.uuid4(),
        content=full_result.strip(),
        conversation_id=uuid.uuid4(),
        created_at=datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")),
    )

    return response


@router.post("/agent/chat_vectordb", response_model=MessageResponse)
async def chat_vectordb(request: ChatRequest):
    logger.info("Processing chat message for conversation")

    full_result = ""
    for text in RetrieverVectordbService.run(request.content):
        full_result += text

    response = MessageResponse(
        id=uuid.uuid4(),
        content=full_result.strip(),
        conversation_id=uuid.uuid4(),
        created_at=datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")),
    )

    return response


@router.post("/agent/chat_memory", response_model=MessageResponse)
async def chat_memory(request: ChatRequest):
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


@router.post("/agent/tts_chat", response_model=MessageResponse)
async def tts_chat(request: VoiceRequest):
    logger.info("Processing chat message for conversation")

    suffix = ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(request.file_bytes)
        tmp_path = tmp_file.name

    logger.info(f"Temporary audio file saved at: {tmp_path}")

    try:
        # Xử lý audio
        init_agent = SttAgent(tmp_path)
        init_agent.parse_audio()
        results = init_agent.parse_text()

        if not results:
            return MessageResponse(
                id=uuid.uuid4(),
                content="Không nhận diện được giọng nói.",
                conversation_id=uuid.uuid4(),
                created_at=datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")),
            )

        full_text = " ".join(results).strip()

        return MessageResponse(
            id=uuid.uuid4(),
            content=full_text,
            conversation_id=uuid.uuid4(),
            created_at=datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")),
        )

    finally:
        # Xoá file tạm sau khi xử lý
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/agent/ordered", response_model=MessageResponse)
async def ordered(request: ChatRequest):
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
