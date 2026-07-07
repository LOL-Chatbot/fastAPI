from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import Position


class ChatRequest(BaseModel):
    message: str
    champion_id: str | None = None
    position: Position | None = None


class RelatedChampion(BaseModel):
    champion_id: str
    name_ko: str


class ChatAttachment(BaseModel):
    type: str
    title: str
    data: Any


class ChatData(BaseModel):
    answer: str
    related_champions: list[RelatedChampion]
    attachments: list[ChatAttachment] = Field(default_factory=list)
