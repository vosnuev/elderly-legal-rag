from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.chat import router as chat_router
from settings import settings
from logger import configure_logging, get_logger

logger = get_logger(__name__)

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

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": settings.service_name,
            "version": settings.service_version,
        }

    @app.get("/api/system/dependencies")
    def dependencies() -> dict[str, object]:
        return {
            "runtime": "FastAPI",
            "agent_stack": ["LangChain", "LangGraph"],
            "settings": "pydantic-settings",
        }

    app.include_router(chat_router)

    return app


app = create_app()


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
