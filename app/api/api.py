from fastapi import APIRouter

from app.core.config import settings

from .routes import assignee_task_route as assignee_task
from .routes import attachment_route as attachment
from .routes import auth_route as auth
from .routes import category_route as category
from .routes import comment_route as comment
from .routes import dashboard_route as dashboard
from .routes import milestone_route as milestone
from .routes import notification_route as notification
from .routes import project_member_route as project_member
from .routes import project_route as proyek
from .routes import task_route as task
from .routes import user_route as user

# url prefix for all routes ex: /v1
router = APIRouter(prefix=settings.version_url)
router.include_router(auth.router)
router.include_router(user.router)
router.include_router(proyek.router)
router.include_router(project_member.router)
router.include_router(task.router)
router.include_router(milestone.router)
router.include_router(assignee_task.router)
router.include_router(dashboard.router)
router.include_router(comment.router)
router.include_router(attachment.router)
router.include_router(category.router)
router.include_router(notification.router)
