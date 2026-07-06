from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.state import create_app_state, set_app_state
from app.routers import champions, chat, health, opgg_champions, recommendations


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    set_app_state(app, create_app_state())
    yield


app = FastAPI(
    title="LOL 챗봇 API",
    version="v1",
    lifespan=lifespan,
    root_path=get_settings().fastapi_root_path,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(champions.router)
app.include_router(recommendations.router)
app.include_router(opgg_champions.router)
app.include_router(chat.router)


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        error = exc.detail
    else:
        error = {
            "code": "INVALID_REQUEST",
            "message": str(exc.detail),
        }

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": error,
        },
    )


@app.exception_handler(RequestValidationError)
def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "요청 데이터 검증에 실패했습니다.",
            },
        },
    )
