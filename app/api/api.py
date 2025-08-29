from fastapi import APIRouter, Depends

from app.api.dependencies.events import inject_event_background
from app.core.config import settings

from .routes import assignee_task_route as assignee_task
from .routes import auth_route as auth
from .routes import comment_route as comment
from .routes import dashboard_route as dashboard
from .routes import project_member_route as project_member
from .routes import project_route as proyek
from .routes import task_route as task
from .routes import user_route as user

# url prefix for all routes ex: /v1
# inject event background task untuk semua route
router = APIRouter(
    prefix=settings.version_url, dependencies=[Depends(inject_event_background)]
)
router.include_router(auth.router)
router.include_router(user.router)
router.include_router(proyek.router)
router.include_router(project_member.router)
router.include_router(task.router)
router.include_router(assignee_task.router)
router.include_router(dashboard.router)
router.include_router(comment.r)
