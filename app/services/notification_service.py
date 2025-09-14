from app.db.uow.sqlalchemy import UnitOfWork


class NotificationService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
