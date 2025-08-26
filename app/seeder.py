import asyncio
import datetime
import os

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.models.project_member_model import ProjectMember, RoleProject

# Import model & enum
from app.db.models.project_model import Project, StatusProject
from app.db.models.task_model import StatusTask, Task
from app.utils import exceptions

# Ambil DATABASE_URL dari environment (contoh: postgresql+asyncpg://user:pass@localhost:5432/dbname)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/smp_db",
)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def seed_projects(session: AsyncSession):
    """
    Seed beberapa project beserta member & task.
    User (1=admin,2=hrd,3/4=pegawai) sudah disediakan oleh PegawaiService dummy.
    """
    now = datetime.datetime.now(datetime.timezone.utc)

    seed_def = [
        {
            "title": "Implementasi Sistem Inventori",
            "description": "Pengembangan modul inventori gudang",
            "status": StatusProject.ACTIVE,
            "created_by": 1,
            "members": [
                (1, RoleProject.OWNER),
                (2, RoleProject.CONTRIBUTOR),
                (3, RoleProject.CONTRIBUTOR),
            ],
            "tasks": [
                {
                    "name": "Analisa Kebutuhan",
                    "status": StatusTask.IN_PROGRESS,
                    "assignees": [1, 2],
                },
                {
                    "name": "Desain Database",
                    "status": StatusTask.IN_PROGRESS,
                    "assignees": [1, 3],
                },
            ],
        },
        {
            "title": "Portal HRD",
            "description": "Portal internal untuk manajemen pegawai",
            "status": StatusProject.COMPLETED,
            "created_by": 2,
            "members": [
                (2, RoleProject.OWNER),
                (1, RoleProject.CONTRIBUTOR),
                (4, RoleProject.CONTRIBUTOR),
            ],
            "tasks": [
                {
                    "name": "Setup Auth",
                    "status": StatusTask.COMPLETED,
                    "assignees": [2],
                },
                {
                    "name": "Integrasi Email",
                    "status": StatusTask.IN_PROGRESS,
                    "assignees": [4],
                },
            ],
        },
    ]

    for proj in seed_def:
        # Cegah duplikasi berdasarkan title
        existing = await session.execute(
            Project.__table__.select().where(Project.title == proj["title"])
        )
        if existing.first():
            continue

        project = Project(
            title=proj["title"],
            description=proj["description"],
            status=proj["status"],
            created_by=proj["created_by"],
            created_at=now,
            updated_at=now,
        )
        session.add(project)
        await session.flush()  # dapatkan project.id

        # Members
        for user_id, role in proj["members"]:
            session.add(
                ProjectMember(
                    project_id=project.id,
                    user_id=user_id,
                    role=role,
                    created_at=now,
                    updated_at=now,
                )
            )

        # Tasks
        for idx, t in enumerate(proj["tasks"]):
            task = Task(
                project_id=project.id,
                name=t["name"],
                status=t["status"],
                display_order=(idx + 1) * 10000,
                created_at=now,
                updated_at=now,
            )
            session.add(task)
            await session.flush()
            # Assignees (pakai association table TaskAssignee jika ada)
            # Hindari import sirkular
            from app.db.models.task_assigne_model import TaskAssignee

            for uid in t["assignees"]:
                session.add(TaskAssignee(task_id=task.id, user_id=uid))

    await session.commit()


async def main():
    async with AsyncSessionLocal() as session:
        try:
            await seed_projects(session)
            print("Seed data selesai.")
        except exceptions.AppException as e:
            await session.rollback()
            print(f"Gagal seed (app error): {e}")
        except Exception as e:
            await session.rollback()
            print(f"Gagal seed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
