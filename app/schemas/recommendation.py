from pydantic import BaseModel

from app.schemas.common import Image, Position


class ChampionBuildRequest(BaseModel):
    champion_id: str
    position: Position
    enemy_champion_id: str | None = None
    play_style: str | None = None


class RecommendationRequest(BaseModel):
    champion_id: str
    position: Position


class ItemRecommendationRequest(RecommendationRequest):
    enemy_champion_id: str | None = None


class NamedImage(BaseModel):
    name: str
    image: Image | None = None


class RuneRecommendationData(BaseModel):
    champion_id: str
    position: Position
    primary_style: str
    keystone: NamedImage
    primary_runes: list[str]
    primary_rune_images: list[NamedImage] = []
    secondary_style: str
    secondary_runes: list[str]
    secondary_rune_images: list[NamedImage] = []
    stat_shards: list[str]


class RuneBuildData(BaseModel):
    primary_style: str
    keystone: NamedImage
    primary_runes: list[str]
    primary_rune_images: list[NamedImage] = []
    secondary_style: str
    secondary_runes: list[str]
    secondary_rune_images: list[NamedImage] = []
    stat_shards: list[str]


class SpellRecommendationData(BaseModel):
    champion_id: str
    position: Position
    spells: list[NamedImage]


class SituationalItem(BaseModel):
    name: str
    reason: str


class ItemRecommendationData(BaseModel):
    champion_id: str
    position: Position
    start_items: list[NamedImage]
    core_items: list[NamedImage]
    boots: list[NamedImage]
    situational_items: list[SituationalItem]


class ItemBuildData(BaseModel):
    start_items: list[NamedImage]
    core_items: list[NamedImage]
    boots: list[NamedImage]
    situational_items: list[SituationalItem]


class SkillRecommendationData(BaseModel):
    champion_id: str
    position: Position
    priority: list[str]
    priority_images: list[NamedImage] = []
    description: str


class SkillBuildData(BaseModel):
    priority: list[str]
    priority_images: list[NamedImage] = []
    description: str


class CounterChampion(BaseModel):
    champion_id: str
    name_ko: str
    reason: str
    image: Image | None = None


class CounterRecommendationData(BaseModel):
    champion_id: str
    position: Position
    counters: list[CounterChampion]


class ChampionBuildData(BaseModel):
    champion_id: str
    position: Position
    champion_image: NamedImage | None = None
    runes: RuneBuildData
    spells: list[NamedImage]
    items: ItemBuildData
    skills: SkillBuildData
    counters: list[CounterChampion]
    summary: str
