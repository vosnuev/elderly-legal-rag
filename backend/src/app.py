from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.files import router as files_router
from api.chat import router as chat_router
from settings import settings
from logger import configure_logging, get_logger

logger = get_logger(__name__)

# FastAPI 앱 생성, 공통 라우터와 미들웨어 연결
def create_app() -> FastAPI:
    configure_logging()
    logger.info("Starting %s v%s", settings.service_name, settings.service_version)

    app = FastAPI(title=settings.service_name, version=settings.service_version)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # 서비스 상태 확인 응답 반환
    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": settings.service_name,
            "version": settings.service_version,
        }

    # backend가 사용하는 주요 런타임 의존성 반환
    @app.get("/api/system/dependencies")
    def dependencies() -> dict[str, object]:
        return {
            "runtime": "FastAPI",
            "agent_stack": ["LangChain", "LangGraph"],
            "settings": "pydantic-settings",
        }

    app.include_router(chat_router)
    app.include_router(files_router)

    return app


app = create_app()


# uvicorn으로 backend 서버 실행
def main() -> None:
    import uvicorn

    uvicorn.run(
        "app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.reload,
    )


if __name__ == "__main__":
    main()
