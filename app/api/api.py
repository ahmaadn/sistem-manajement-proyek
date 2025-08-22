from fastapi import APIRouter

from app.core.config import settings

from .routes import auth_route as auth
from .routes import dashboard_route as dashboard
from .routes import project_member_route as project_member
from .routes import project_route as proyek
from .routes import task_route as task
from .routes import user_route as user

router = APIRouter(prefix=settings.version_url)  # url prefix for all routes ex: /v1
router.include_router(auth.router)
router.include_router(user.router)
router.include_router(proyek.router)
router.include_router(project_member.router)
router.include_router(task.router)
router.include_router(dashboard.router)
