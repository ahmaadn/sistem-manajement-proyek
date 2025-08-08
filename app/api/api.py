from fastapi import APIRouter

from app.core.config import settings

from .routes import auth_route as auth

router = APIRouter(prefix=settings.version_url)  # url prefix for all routes ex: /v1
router.include_router(auth.router)
