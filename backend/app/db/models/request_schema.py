from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    content: str = Field(..., description="Prompt or content for deep research")


class VoiceRequest(BaseModel):
    file_bytes: bytes = Field(..., description="bytes voices")
