from fastapi import APIRouter, Request

from app.core.state import get_recommendation_service
from app.schemas.common import SuccessResponse
from app.schemas.recommendation import (
    ChampionBuildRequest,
    ItemRecommendationRequest,
    RecommendationRequest,
)


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/champion-build", response_model=SuccessResponse)
def recommend_champion_build(
    request: ChampionBuildRequest,
    http_request: Request,
) -> SuccessResponse:
    recommendation_service = get_recommendation_service(http_request)
    recommendation = recommendation_service.get_champion_build(
        champion_id=request.champion_id,
        position=request.position,
        enemy_champion_id=request.enemy_champion_id,
        play_style=request.play_style,
    )
    return SuccessResponse(
        data=recommendation,
        message="챔피언 종합 빌드를 추천했습니다.",
    )


@router.post("/runes", response_model=SuccessResponse)
def recommend_runes(
    request: RecommendationRequest,
    http_request: Request,
) -> SuccessResponse:
    recommendation_service = get_recommendation_service(http_request)
    recommendation = recommendation_service.get_runes(
        champion_id=request.champion_id,
        position=request.position,
    )
    return SuccessResponse(
        data=recommendation,
        message="룬 추천을 조회했습니다.",
    )


@router.post("/spells", response_model=SuccessResponse)
def recommend_spells(
    request: RecommendationRequest,
    http_request: Request,
) -> SuccessResponse:
    recommendation_service = get_recommendation_service(http_request)
    recommendation = recommendation_service.get_spells(
        champion_id=request.champion_id,
        position=request.position,
    )
    return SuccessResponse(
        data=recommendation,
        message="스펠 추천을 조회했습니다.",
    )


@router.post("/items", response_model=SuccessResponse)
def recommend_items(
    request: ItemRecommendationRequest,
    http_request: Request,
) -> SuccessResponse:
    recommendation_service = get_recommendation_service(http_request)
    recommendation = recommendation_service.get_items(
        champion_id=request.champion_id,
        position=request.position,
        enemy_champion_id=request.enemy_champion_id,
    )
    return SuccessResponse(
        data=recommendation,
        message="아이템 빌드를 추천했습니다.",
    )


@router.post("/skills", response_model=SuccessResponse)
def recommend_skills(
    request: RecommendationRequest,
    http_request: Request,
) -> SuccessResponse:
    recommendation_service = get_recommendation_service(http_request)
    recommendation = recommendation_service.get_skills(
        champion_id=request.champion_id,
        position=request.position,
    )
    return SuccessResponse(
        data=recommendation,
        message="스킬 선마 순서를 추천했습니다.",
    )


@router.post("/counters", response_model=SuccessResponse)
def recommend_counters(
    request: RecommendationRequest,
    http_request: Request,
) -> SuccessResponse:
    recommendation_service = get_recommendation_service(http_request)
    recommendation = recommendation_service.get_counters(
        champion_id=request.champion_id,
        position=request.position,
    )
    return SuccessResponse(
        data=recommendation,
        message="카운터 챔피언을 추천했습니다.",
    )
