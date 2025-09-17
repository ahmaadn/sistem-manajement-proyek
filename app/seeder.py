import argparse
import asyncio
import datetime
import os
import random
import sys
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from starlette_context import context, request_cycle_context

from app.core.config.settings import get_settings
from app.db.models import load_all_models
from app.db.models.project_model import StatusProject
from app.db.models.role_model import Role
from app.db.models.task_model import PriorityLevel, StatusTask
from app.db.uow.sqlalchemy import SQLAlchemyUnitOfWork as UnitOfWork
from app.schemas.category import CategoryCreate
from app.schemas.milestone import MilestoneCreate
from app.schemas.project import ProjectCreate
from app.schemas.task import TaskCreate
from app.schemas.user import User
from app.services.category_service import CategoryService
from app.services.milestone_service import MilestoneService
from app.services.pegawai_service import PegawaiService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.utils import exceptions

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    str(get_settings().db_url),
)

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

load_all_models()


def dummy_context():
    with request_cycle_context({}):
        context["debug"] = True
        yield context


context_generator = dummy_context()
context = next(context_generator)


class Seeder:
    def __init__(
        self,
        session: AsyncSession,
        pm_user_id: int,
        total_projects: int,
        milestones_per_project: int,
        tasks_per_milestone: int,
        categories_per_project: int,
        seed_all_projects: bool,
    ):
        self.session = session
        self.total_projects = total_projects
        self.milestones_per_project = milestones_per_project
        self.tasks_per_milestone = tasks_per_milestone
        self.categories_per_project = categories_per_project
        self.seed_all_projects = seed_all_projects
        self.pm_user_id = pm_user_id

        self.uow = UnitOfWork(session=self.session)
        self.pegawai_service = PegawaiService()
        self.user_service = UserService(
            pegawai_service=self.pegawai_service,
            uow=self.uow,
            repo=self.uow.user_repository,
        )
        self.project_service = ProjectService(
            uow=self.uow, repo=self.uow.project_repo
        )
        self.milestone_service = MilestoneService(uow=self.uow)
        self.task_service = TaskService(uow=self.uow)
        self.category_service = CategoryService(uow=self.uow)

        self.pm_user = None
        self.special_index = random.randrange(self.total_projects)
        self.created_project_ids: list[int] = []
        self.start_time = None

    # ------------------ RANDOM HELPERS ------------------
    @staticmethod
    def random_sentence() -> str:
        subjects = ["API", "Sistem", "Layanan", "Modul", "Pipeline", "Dashboard"]
        verbs = [
            "mengelola",
            "memproses",
            "menganalisa",
            "mengsinkronkan",
            "mengotomatiskan",
        ]
        objs = [
            "data pengguna",
            "transaksi",
            "notifikasi",
            "log aktivitas",
            "metadata",
        ]
        return (
            f"{random.choice(subjects)} {random.choice(verbs)} {random.choice(objs)}"
        )

    @staticmethod
    def random_task_dates():
        """
        Menghasilkan (start_date, due_date) dengan rentang relatif sekarang.
        start_date: antara -3 sampai +5 hari dari sekarang
        due_date  : >= start_date (1..14 hari setelah start)
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        start = now + datetime.timedelta(days=random.randint(-3, 5))
        due = start + datetime.timedelta(days=random.randint(1, 14))
        return start, due

    def random_description(self) -> str:
        return " ".join(self.random_sentence() for _ in range(3))

    @staticmethod
    def random_task_name(idx: int) -> str:
        verbs = [
            "Analisis",
            "Desain",
            "Implementasi",
            "Review",
            "Optimasi",
            "Integrasi",
        ]
        targets = [
            "Auth",
            "Database",
            "API Gateway",
            "Frontend",
            "Layanan Email",
            "Queue",
        ]
        return f"{random.choice(verbs)} {random.choice(targets)} #{idx + 1}"

    @staticmethod
    def random_project_dates_and_status():
        status = random.choice(list(StatusProject))
        now = datetime.datetime.now(datetime.timezone.utc)
        start_offset_days = random.randint(-30, 10)
        start_date = now + datetime.timedelta(days=start_offset_days)
        duration_days = random.randint(1, 30)
        end_date = start_date + datetime.timedelta(days=duration_days)

        if status == StatusProject.TENDER:
            if start_date <= now:
                start_date = now + datetime.timedelta(days=random.randint(1, 15))
                end_date = start_date + datetime.timedelta(days=duration_days)
        elif status == StatusProject.ACTIVE:
            if start_date > now:
                start_date = now - datetime.timedelta(days=random.randint(0, 5))
                end_date = start_date + datetime.timedelta(days=duration_days)
            if end_date <= now:
                end_date = now + datetime.timedelta(days=random.randint(1, 20))
        elif status == StatusProject.COMPLETED:
            end_date = now - datetime.timedelta(days=random.randint(1, 5))
            start_date = end_date - datetime.timedelta(days=duration_days)
        elif status == StatusProject.CANCEL and end_date < start_date:
            end_date = start_date + datetime.timedelta(days=1)
        return status, start_date, end_date

    # ------------------ CORE STEPS ------------------
    async def fetch_pm_user(self):
        if self.pm_user is None:
            # user = await self.user_service.get_user(self.pm_user_id)
            # if user.role.name.lower() != "project_manager":
            #     raise RuntimeError(
            #         f"User {user.id} bukan project_manager (role sekarang: {user.role}). "  # noqa: E501
            #         "Ubah role dulu sebelum menjalankan seeder."
            #     )
            self.pm_user = User(
                id=self.pm_user_id,
                name="Project Manager",
                email="",
                position="",
                profile_url="",
                employee_role="Project Manager",
                role=Role.PROJECT_MANAGER,
            )

    async def create_project(self, index: int):
        status, start_date, end_date = self.random_project_dates_and_status()
        title = (
            "Project Auto Seed "
            f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')}-"
            f"{index + 1}-{random.randint(100, 999)}"
        )
        payload = ProjectCreate(
            title=title,
            description=self.random_description(),
            status=status,
            start_date=start_date,
            end_date=end_date,
        )
        project = await self.project_service.create_project(
            user=self.pm_user,  # type: ignore
            project_create=payload,
        )
        print(
            f"  -> Project dibuat id={project.id} status={status} "
            f"start={start_date.date()} end={end_date.date()}"
        )
        return project, status, start_date, end_date

    async def create_categories(self, project_id: int) -> list[int]:
        ids: list[int] = []
        for idx in range(self.categories_per_project):
            payload = CategoryCreate(
                name=f"Kategori {idx + 1}",
                description=self.random_sentence(),
            )
            category = await self.category_service.create(
                user=self.pm_user,  # type: ignore
                project_id=project_id,
                payload=payload,
            )
            ids.append(category.id)
            print(f"       - Category {category.id}: {payload.name}")
        return ids

    async def create_subtasks(
        self,
        task_id: int,
        parent_name: str,
        category_ids: list[int],
    ):
        sub_count = random.randint(0, 4)
        if not sub_count:
            return
        print(f"          · Subtasks ({sub_count}) utk task_id={task_id}")
        for s_idx in range(sub_count):
            start_date, due_date = self.random_task_dates()
            payload = TaskCreate(
                name=f"{parent_name} - Subtask {s_idx + 1}",
                description=self.random_description(),
                status=random.choice(list(StatusTask)),
                priority=random.choice(list(PriorityLevel)),
                category_id=random.choice(category_ids) if category_ids else None,
                start_date=start_date,
                due_date=due_date,
            )
            await self.task_service.create_subtask(
                user=self.pm_user,  # type: ignore
                task_id=task_id,
                payload=payload,
            )

    async def create_tasks_for_milestone(
        self,
        milestone_id: int,
        category_ids: list[int],
    ):
        print(
            f"       > Tasks milestone {milestone_id} "
            f"({self.tasks_per_milestone} task)"
        )
        for t_idx in range(self.tasks_per_milestone):
            start_date, due_date = self.random_task_dates()
            payload = TaskCreate(
                name=self.random_task_name(t_idx),
                description=self.random_description(),
                status=random.choice(list(StatusTask)),
                priority=random.choice(list(PriorityLevel)),
                category_id=random.choice(category_ids) if category_ids else None,
                start_date=start_date,
                due_date=due_date,
            )
            task = await self.task_service.create_task(
                user=self.pm_user,  # type: ignore
                milestone_id=milestone_id,
                payload=payload,
            )
            await self.create_subtasks(
                task_id=task.id,
                parent_name=task.name,
                category_ids=category_ids,
            )

    async def create_milestones_with_tasks(
        self,
        project_id: int,
        category_ids: list[int],
    ):
        print(
            f"    > Buat {self.milestones_per_project} milestone "
            f"(tasks/milestone={self.tasks_per_milestone})"
        )
        for m_idx in range(self.milestones_per_project):
            payload = MilestoneCreate(
                title=f"Milestone {m_idx + 1} - Project {project_id}"
            )
            milestone = await self.milestone_service.create_milestone(
                user=self.pm_user,  # type: ignore
                project_id=project_id,
                payload=payload,
            )
            await self.create_tasks_for_milestone(
                milestone_id=milestone.id, category_ids=category_ids
            )

    async def populate_project(self, project_id: int):
        print("   (Populate) Mulai isi project")
        category_ids = await self.create_categories(project_id)
        await self.create_milestones_with_tasks(project_id, category_ids)
        print("   (Populate) Selesai isi project")

    # ------------------ PUBLIC ENTRY ------------------
    async def seed(self):
        if self.total_projects < 1:
            print("total_projects harus >= 1")
            return

        self.start_time = datetime.datetime.now()
        await self.fetch_pm_user()

        print(
            f"Seeding {self.total_projects} project. "
            f"Project spesial index: {self.special_index} "
            f"(milestone={self.milestones_per_project}, task/milestone={self.tasks_per_milestone}, "  # noqa: E501
            f"categories={self.categories_per_project})"
        )

        for i in range(self.total_projects):
            proj_start = datetime.datetime.now()
            async with self.uow:
                project, status, start_date, end_date = await self.create_project(i)
                self.created_project_ids.append(project.id)

                is_special = (i == self.special_index) or self.seed_all_projects
                if is_special:
                    await self.populate_project(project.id)

                await self.uow.commit()

            dur = (datetime.datetime.now() - proj_start).total_seconds()
            print(
                f"- Project {project.id} {'(SPESIAL)' if is_special else ''} "
                f"status={status} start={start_date.date()} end={end_date.date()} "
                f"done {dur:.2f}s"
            )
        total_dur = (datetime.datetime.now() - self.start_time).total_seconds()
        print(f"Selesai. Project IDs: {self.created_project_ids}")
        print(f"Total waktu: {total_dur:.2f}s")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seeder Project + Milestone + Task")
    parser.add_argument(
        "--total", type=int, default=int(os.getenv("TOTAL_PROJECTS", "3"))
    )
    parser.add_argument("--pm", type=int, default=int(os.getenv("PM_USER_ID", "1")))
    parser.add_argument(
        "--milestones",
        type=int,
        default=int(os.getenv("SPECIAL_PROJECT_MILESTONES", "3")),
        help="Jumlah milestone untuk project spesial",
    )
    parser.add_argument(
        "--tasks",
        type=int,
        default=int(os.getenv("TASKS_PER_MILESTONE", "5")),
        help="Jumlah task per milestone",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Jika diset, semua project di-populate (bukan hanya 1 random)",
    )
    parser.add_argument(
        "--categories",
        type=int,
        default=int(os.getenv("CATEGORIES_PER_PROJECT", "3")),
        help="Jumlah kategori untuk project spesial",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Set random seed agar deterministik",
    )
    return parser.parse_args(argv)


async def main(argv: Optional[list[str]] = None):
    args = parse_args(argv or [])
    if args.seed is not None:
        random.seed(args.seed)

    async with SessionLocal() as session:
        try:
            seeder = Seeder(
                session=session,
                pm_user_id=args.pm,
                total_projects=args.total,
                milestones_per_project=args.milestones,
                tasks_per_milestone=args.tasks,
                categories_per_project=args.categories,
                seed_all_projects=args.all,
            )
            await seeder.seed()
        except exceptions.AppException as e:
            await session.rollback()
            print(f"AppException: {e}")
        except Exception as e:
            await session.rollback()
            print(f"General error: {e}")
            raise


if __name__ == "__main__":
    # Contoh:
    # python -m app.seeder --total 5 --pm 1 --milestones 3 --tasks 5 --categories 4 --seed 42  # noqa: E501
    asyncio.run(main(sys.argv[1:]))
