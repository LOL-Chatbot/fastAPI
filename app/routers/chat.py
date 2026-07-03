from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.state import get_llm_service
from app.schemas.chat import ChatRequest
from app.schemas.common import SuccessResponse


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=SuccessResponse)
def chat(request: ChatRequest, http_request: Request) -> SuccessResponse:
    llm_service = get_llm_service(http_request)
    answer = llm_service.create_answer(
        message=request.message,
        champion_id=request.champion_id,
        position=request.position,
    )
    return SuccessResponse(
        data=answer,
        message="챗봇 답변을 생성했습니다.",
    )


@router.post("/stream")
def chat_stream(request: ChatRequest, http_request: Request) -> StreamingResponse:
    llm_service = get_llm_service(http_request)
    return StreamingResponse(
        llm_service.create_answer_stream(
            message=request.message,
            champion_id=request.champion_id,
            position=request.position,
        ),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )
