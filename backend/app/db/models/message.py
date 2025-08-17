from uuid import UUID
from datetime import datetime
from sqlmodel import SQLModel


class MessageResponse(SQLModel):
    """
    Schema for message response.
    """

    id: UUID
    content: str
    conversation_id: UUID
    created_at: datetime
