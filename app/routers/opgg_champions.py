from fastapi import APIRouter, Request

from app.core.state import get_recommendation_service
from app.schemas.common import SuccessResponse
from app.schemas.opgg_champion import (
    OpggChampionAnalysisRequest,
    OpggChampionDetailsRequest,
    OpggChampionLeaderboardRequest,
    OpggChampionSynergyRequest,
    OpggLaneMatchupGuideRequest,
    OpggLaneMetaRequest,
    OpggRawToolData,
)


router = APIRouter(prefix="/opgg/champions", tags=["opgg-champions"])


@router.post("/analysis", response_model=SuccessResponse)
def get_champion_analysis(
    request: OpggChampionAnalysisRequest,
    http_request: Request,
) -> SuccessResponse:
    recommendation_service = get_recommendation_service(http_request)
    raw_text = recommendation_service.get_opgg_champion_analysis_raw(
        champion_id=request.champion_id,
        position=request.position,
    )
    return SuccessResponse(
        data=OpggRawToolData(
            tool_name="lol_get_champion_analysis",
            query=request.model_dump(),
            raw_text=raw_text,
        ),
        message="OP.GG 챔피언 분석 정보를 조회했습니다.",
    )


@router.post("/synergies", response_model=SuccessResponse)
def get_champion_synergies(
    request: OpggChampionSynergyRequest,
    http_request: Request,
) -> SuccessResponse:
    recommendation_service = get_recommendation_service(http_request)
    raw_text = recommendation_service.get_opgg_champion_synergies_raw(
        champion_id=request.champion_id,
        my_position=request.my_position,
        synergy_position=request.synergy_position,
    )
    return SuccessResponse(
        data=OpggRawToolData(
            tool_name="lol_get_champion_synergies",
            query=request.model_dump(),
            raw_text=raw_text,
        ),
        message="OP.GG 챔피언 시너지 정보를 조회했습니다.",
    )


@router.post("/lane-matchup-guide", response_model=SuccessResponse)
def get_lane_matchup_guide(
    request: OpggLaneMatchupGuideRequest,
    http_request: Request,
) -> SuccessResponse:
    recommendation_service = get_recommendation_service(http_request)
    raw_text = recommendation_service.get_opgg_lane_matchup_guide_raw(
        my_champion_id=request.my_champion_id,
        opponent_champion_id=request.opponent_champion_id,
        position=request.position,
    )
    return SuccessResponse(
        data=OpggRawToolData(
            tool_name="lol_get_lane_matchup_guide",
            query=request.model_dump(),
            raw_text=raw_text,
        ),
        message="OP.GG 라인전 매치업 가이드를 조회했습니다.",
    )


@router.post("/details", response_model=SuccessResponse)
def get_champion_details(
    request: OpggChampionDetailsRequest,
    http_request: Request,
) -> SuccessResponse:
    recommendation_service = get_recommendation_service(http_request)
    raw_text = recommendation_service.get_opgg_champion_details_raw(
        champion_ids=request.champion_ids,
    )
    return SuccessResponse(
        data=OpggRawToolData(
            tool_name="lol_list_champion_details",
            query=request.model_dump(),
            raw_text=raw_text,
        ),
        message="OP.GG 챔피언 상세 정보를 조회했습니다.",
    )


@router.post("/leaderboard", response_model=SuccessResponse)
def get_champion_leaderboard(
    request: OpggChampionLeaderboardRequest,
    http_request: Request,
) -> SuccessResponse:
    recommendation_service = get_recommendation_service(http_request)
    raw_text = recommendation_service.get_opgg_champion_leaderboard_raw(
        champion_id=request.champion_id,
        region=request.region,
    )
    return SuccessResponse(
        data=OpggRawToolData(
            tool_name="lol_list_champion_leaderboard",
            query=request.model_dump(),
            raw_text=raw_text,
        ),
        message="OP.GG 챔피언 리더보드 정보를 조회했습니다.",
    )


@router.get("/list", response_model=SuccessResponse)
def list_champions(http_request: Request) -> SuccessResponse:
    recommendation_service = get_recommendation_service(http_request)
    raw_text = recommendation_service.get_opgg_champions_raw()
    return SuccessResponse(
        data=OpggRawToolData(
            tool_name="lol_list_champions",
            query={},
            raw_text=raw_text,
        ),
        message="OP.GG 챔피언 목록 정보를 조회했습니다.",
    )


@router.post("/lane-meta", response_model=SuccessResponse)
def list_lane_meta_champions(
    request: OpggLaneMetaRequest,
    http_request: Request,
) -> SuccessResponse:
    recommendation_service = get_recommendation_service(http_request)
    raw_text = recommendation_service.get_opgg_lane_meta_raw(
        position=request.position,
    )
    return SuccessResponse(
        data=OpggRawToolData(
            tool_name="lol_list_lane_meta_champions",
            query=request.model_dump(),
            raw_text=raw_text,
        ),
        message="OP.GG 라인별 메타 챔피언 정보를 조회했습니다.",
    )
