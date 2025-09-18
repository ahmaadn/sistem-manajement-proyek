from fastapi import Depends

from app.api.dependencies.uow import get_uow
from app.db.uow.sqlalchemy import UnitOfWork
from app.services.attachment_service import AttachmentService
from app.services.category_service import CategoryService
from app.services.comment_service import CommentService
from app.services.dashboard_service import DashboardService
from app.services.milestone_service import MilestoneService
from app.services.notification_service import NotificationService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService


def get_project_service(uow: UnitOfWork = Depends(get_uow)) -> ProjectService:
    """Mendapatkan layanan project."""
    return ProjectService(uow)


def get_task_service(uow: UnitOfWork = Depends(get_uow)) -> TaskService:
    """Mendapatkan layanan task."""
    return TaskService(uow)


def get_dashboard_service(
    uow: UnitOfWork = Depends(get_uow),
) -> DashboardService:
    """Mendapatkan layanan dasbor."""
    return DashboardService(uow)


def get_comment_service(uow: UnitOfWork = Depends(get_uow)) -> CommentService:
    """Mendapatkan layanan komentar."""
    return CommentService(uow)


def get_attachment_service(uow: UnitOfWork = Depends(get_uow)) -> AttachmentService:
    """Mendapatkan layanan lampiran."""
    return AttachmentService(uow)


def get_milestone_service(uow: UnitOfWork = Depends(get_uow)) -> MilestoneService:
    return MilestoneService(uow=uow)


def get_category_service(uow: UnitOfWork = Depends(get_uow)):
    return CategoryService(uow=uow)


def get_notification_service(uow: UnitOfWork = Depends(get_uow)):
    return NotificationService(uow)
