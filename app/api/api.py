from fastapi import APIRouter

from app.core.config import settings

from .routes import auth_route as auth
from .routes import project_route as proyek

router = APIRouter(prefix=settings.version_url)  # url prefix for all routes ex: /v1
router.include_router(auth.router)
router.include_router(proyek.router)
