from pydantic import BaseModel

from app.schemas.common import Image, Position


class ChampionSummary(BaseModel):
    champion_id: str
    name_ko: str
    name_en: str
    positions: list[Position]
    image: Image | None = None


class ChampionDetail(ChampionSummary):
    summary: str


class ChampionListData(BaseModel):
    champions: list[ChampionSummary]


class ChampionTierListItem(BaseModel):
    rank: int
    champion_id: str
    name_ko: str
    name_en: str
    image: Image | None = None
    position: Position
    tier: int
    win_rate: float
    pick_rate: float
    ban_rate: float
    kda: float


class ChampionTierListData(BaseModel):
    position: str
    query: str | None = None
    champions: list[ChampionTierListItem]
