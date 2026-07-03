from dataclasses import dataclass

from fastapi import FastAPI, Request

from app.core.config import Settings, create_llm_client, get_settings
from app.services.champion_service import ChampionService
from app.services.data_dragon_service import DataDragonService
from app.services.llm_service import LlmService
from app.services.recommendation_service import RecommendationService


@dataclass
class AppState:
    settings: Settings
    data_dragon_service: DataDragonService
    champion_service: ChampionService
    recommendation_service: RecommendationService
    llm_service: LlmService


def create_app_state() -> AppState:
    settings = get_settings()
    llm_client = create_llm_client(settings)
    data_dragon_service = DataDragonService(settings=settings)
    recommendation_service = RecommendationService(
        settings=settings,
        data_dragon_service=data_dragon_service,
    )

    return AppState(
        settings=settings,
        data_dragon_service=data_dragon_service,
        champion_service=ChampionService(settings=settings),
        recommendation_service=recommendation_service,
        llm_service=LlmService(
            settings=settings,
            llm_client=llm_client,
            recommendation_service=recommendation_service,
        ),
    )


def set_app_state(app: FastAPI, state: AppState) -> None:
    app.state.container = state


def get_app_state(request: Request) -> AppState:
    return request.app.state.container


def get_champion_service(request: Request) -> ChampionService:
    return get_app_state(request).champion_service


def get_recommendation_service(request: Request) -> RecommendationService:
    return get_app_state(request).recommendation_service


def get_llm_service(request: Request) -> LlmService:
    return get_app_state(request).llm_service
