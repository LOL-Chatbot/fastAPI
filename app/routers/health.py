from fastapi import APIRouter, Request

from app.core.state import get_app_state
from app.core.config import create_llm_client
from app.schemas.common import SuccessResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=SuccessResponse)
def health_check(request: Request) -> SuccessResponse:
    app_state = get_app_state(request)
    gemini_check = check_gemini_api_key(app_state.settings)
    opgg_mcp_check = app_state.recommendation_service.check_opgg_mcp()
    checks = {
        "server": {
            "status": "ok",
            "ok": True,
            "message": "FastAPI 서버 응답이 정상입니다.",
        },
        "gemini": gemini_check,
        "opgg_mcp": opgg_mcp_check,
    }
    overall_ok = all(check.get("ok", False) for check in checks.values())

    return SuccessResponse(
        data={
            "status": "ok" if overall_ok else "degraded",
            "service": "lol-chatbot-api",
            "version": "v1",
            "checks": checks,
        },
        message=(
            "서버 및 외부 연동 상태를 확인했습니다."
            if overall_ok
            else "일부 연동 상태 확인에 실패했습니다."
        ),
    )


def check_gemini_api_key(settings) -> dict[str, object]:
    if not settings.gemini_api_key:
        return {
            "status": "error",
            "ok": False,
            "configured": False,
            "message": "GEMINI_API_KEY가 설정되어 있지 않습니다.",
        }

    try:
        client = create_llm_client(settings)
    except Exception as exc:
        return {
            "status": "error",
            "ok": False,
            "configured": True,
            "message": "Gemini 클라이언트 생성에 실패했습니다.",
            "detail": str(exc),
        }

    if client is None:
        return {
            "status": "error",
            "ok": False,
            "configured": True,
            "message": "Gemini 클라이언트를 생성하지 못했습니다.",
        }

    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents="health check",
        )
    except Exception as exc:
        return {
            "status": "error",
            "ok": False,
            "configured": True,
            "model": settings.gemini_model,
            "message": "Gemini API 응답 확인에 실패했습니다.",
            "detail": str(exc),
        }

    return {
        "status": "ok",
        "ok": True,
        "configured": True,
        "model": settings.gemini_model,
        "response_received": bool(getattr(response, "text", None)),
        "message": "Gemini API 응답이 정상입니다.",
    }
