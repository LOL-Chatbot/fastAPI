from pydantic import BaseModel

from app.schemas.common import Position


class ChatRequest(BaseModel):
    message: str
    champion_id: str | None = None
    position: Position | None = None


class RelatedChampion(BaseModel):
    champion_id: str
    name_ko: str


class ChatData(BaseModel):
    answer: str
    related_champions: list[RelatedChampion]
