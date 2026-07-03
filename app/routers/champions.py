from fastapi import APIRouter, Request

from app.core.state import get_champion_service
from app.schemas.champion import ChampionListData, ChampionTierListData
from app.schemas.common import Position, SuccessResponse


router = APIRouter(prefix="/champions", tags=["champions"])


@router.get("", response_model=SuccessResponse)
def get_champions(request: Request, position: Position | None = None) -> SuccessResponse:
    champion_service = get_champion_service(request)
    champions = champion_service.get_champions(position)
    return SuccessResponse(
        data=ChampionListData(champions=champions),
        message="챔피언 목록을 조회했습니다.",
    )


@router.get("/tier-list", response_model=SuccessResponse)
def get_champion_tier_list(
    request: Request,
    position: Position | None = None,
    query: str | None = None,
) -> SuccessResponse:
    champion_service = get_champion_service(request)
    champions = champion_service.get_champion_tier_list(
        position=position,
        query=query,
    )
    return SuccessResponse(
        data=ChampionTierListData(
            position=position.value if position else "ALL",
            query=query,
            champions=champions,
        ),
        message="챔피언 티어표를 조회했습니다.",
    )


@router.get("/{champion_id}", response_model=SuccessResponse)
def get_champion(champion_id: str, request: Request) -> SuccessResponse:
    champion_service = get_champion_service(request)
    champion = champion_service.get_champion(champion_id)
    return SuccessResponse(
        data=champion,
        message="챔피언 정보를 조회했습니다.",
    )
