from pydantic import BaseModel

from app.schemas.common import Position


class OpggChampionAnalysisRequest(BaseModel):
    champion_id: str
    position: Position


class OpggChampionSynergyRequest(BaseModel):
    champion_id: str
    my_position: Position
    synergy_position: Position


class OpggLaneMatchupGuideRequest(BaseModel):
    my_champion_id: str
    opponent_champion_id: str
    position: Position


class OpggChampionDetailsRequest(BaseModel):
    champion_ids: list[str]


class OpggChampionLeaderboardRequest(BaseModel):
    champion_id: str
    region: str = "KR"


class OpggLaneMetaRequest(BaseModel):
    position: Position


class OpggRawToolData(BaseModel):
    tool_name: str
    query: dict[str, object]
    raw_text: str
