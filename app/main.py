import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import websocket
from app.api import api
from app.core.config import settings
from app.core.config.logging import configure_logging
from app.core.domain.subscribers import register_event_handlers
from app.db import create_db_and_tables
from app.db.models import load_all_models
from app.middleware import middleware
from app.utils.error_handler import register_exception_handlers
from app.utils.exceptions import ValidationErrorResponse

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    await create_db_and_tables()
    load_all_models()
    register_event_handlers()
    yield


def get_app() -> FastAPI:
    """Create and return a FastAPI application instance."""

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=f"v{settings.VERSION_API}",
        lifespan=lifespan,
        redoc_url=None,
        middleware=middleware,
        responses={
            422: {
                "model": ValidationErrorResponse,
                "description": "Kesalahan validasi.",
            }
        },
    )

    # Static files
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    # Routers
    app.include_router(api.router)
    app.include_router(websocket.router)

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # register exception handlers
    register_exception_handlers(app)
    return app


app = get_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level=logging.INFO,
    )
