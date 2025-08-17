from fastapi import APIRouter
from uuid import UUID, uuid4
from datetime import datetime
from typing import List
from pydantic import BaseModel


class MessageResponse(BaseModel):
    id: UUID
    content: str
    conversation_id: UUID
    created_at: datetime


class CreateMessageRequest(BaseModel):
    content: str
    conversation_id: UUID


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime


class CreateConversationRequest(BaseModel):
    title: str


router = APIRouter()

# Fake in-memory storage
conversations = []
messages = []


@router.get("/history/conversations", response_model=List[ConversationResponse])
async def list_conversations():
    return conversations


@router.get(
    "/history/conversations/{conversation_id}", response_model=List[MessageResponse]
)
async def get_conversation_messages(conversation_id: UUID):
    return [m for m in messages if m.conversation_id == conversation_id]


@router.post("/history/conversations", response_model=ConversationResponse)
async def create_conversation(request: CreateConversationRequest):
    new_conv = ConversationResponse(
        id=uuid4(), title=request.title, created_at=datetime.utcnow()
    )
    conversations.append(new_conv)
    return new_conv


@router.delete("/history/conversations/{conversation_id}")
async def delete_conversation(conversation_id: UUID):
    global conversations, messages
    conversations = [c for c in conversations if c.id != conversation_id]
    messages = [m for m in messages if m.conversation_id != conversation_id]
    return {"message": "Deleted successfully"}


@router.post("/history/messages", response_model=MessageResponse)
async def save_message(request: CreateMessageRequest):
    new_msg = MessageResponse(
        id=uuid4(),
        content=request.content,
        conversation_id=request.conversation_id,
        created_at=datetime.utcnow(),
    )
    messages.append(new_msg)
    return new_msg
