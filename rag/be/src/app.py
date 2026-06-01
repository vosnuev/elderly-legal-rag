from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.mcp import create_external_mcp
from api.router import api_router
from observability.logger import configure_logging
from settings import settings

configure_logging()

external_mcp = create_external_mcp()
external_mcp_app = external_mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    async with external_mcp.session_manager.run():
        yield


app = FastAPI(title="SKN28 RAG Backend", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(api_router)
app.mount(settings.external_mcp_path, external_mcp_app)


def main() -> None:
    uvicorn.run(
        "app:app",
        host=settings.mcp_host,
        port=settings.mcp_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
