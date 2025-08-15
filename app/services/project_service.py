from app.db.models.project_model import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.base_service import GenericCRUDService
from app.utils.exceptions import ProjectNotFoundError


class ProjectService(GenericCRUDService[Project, ProjectCreate, ProjectUpdate]):
    model = Project
    audit_entity_name = "project"

    def _exception_not_found(self, **extra):
        """
        Membuat exception jika proyek tidak ditemukan.
        """
        return ProjectNotFoundError()
