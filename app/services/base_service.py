from __future__ import annotations

import datetime
from typing import Any, Callable, Generic, Optional, Sequence, Type, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base as BaseModel
from app.schemas.base import BaseSchema
from app.utils.common import ErrorCode
from app.utils.pagination import paginate

ModelT = TypeVar("ModelT", bound=BaseModel)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseSchema)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseSchema)


class GenericCRUDService(Generic[ModelT, CreateSchemaT, UpdateSchemaT]):
    """
    Base generic CRUD manager
    Asumsi:
        - Model memiliki primary key bernama 'id'
        - Soft delete menggunakan kolom 'deleted_at' (UTC datetime) dan/atau
            property 'is_deleted'
    Bisa dioverride sesuai kebutuhan.
    """

    model: Type[ModelT]
    not_found_error_code: str = ErrorCode.GENERIC_NOT_FOUND  # fallback
    soft_delete_field: str = "deleted_at"
    is_deleted_attr: str = "is_deleted"
    audit_entity_name: str = "AuditEntity"

    def __init__(self, session: AsyncSession):
        self.session = session

    # ============ Public Methods ============

    async def get(
        self,
        obj_id: int,
        *,
        allow_deleted: bool = False,
        return_none_if_not_found: bool = False,
        options: list[Any] | None = None,
    ) -> Optional[ModelT]:
        """Mendapatkan objek berdasarkan ID.

        Args:
            obj_id (int): ID objek yang ingin diambil.
            allow_deleted (bool, optional): Mengizinkan pengambilan objek yang
                dihapus. Defaults to False.
            return_none_if_not_found (bool, optional): Mengembalikan None jika objek
                tidak ditemukan. Defaults to False.
            options (list[Any] | None, optional): Opsi tambahan untuk query.
                Defaults to None.

        Raises:
            ValueError: Jika obj_id bukan int.
            self._exception_not_found: Jika objek tidak ditemukan.
            self._exception_not_found: Jika objek telah dihapus (soft delete).

        Returns:
            Optional[ModelT]: Objek yang ditemukan atau None.
        """
        instance = await self.session.get(self.model, obj_id, options=options)

        # Jika objek tidak ditemukan
        if instance is None:
            if return_none_if_not_found:
                return None
            raise self._exception_not_found()

        # objek di temukan tetapi telah dihapus (soft delete)
        if (not allow_deleted) and self._is_deleted(instance):
            if return_none_if_not_found:
                return None
            raise self._exception_not_found()

        return instance

    async def fetch_one(
        self,
        *,
        allow_deleted: bool = False,
        return_none_if_not_found: bool = True,
        filters: dict[str, Any] | None = None,
        options: list[Any] | None = None,
        condition: list[Any] | None = None,
        order_by: Any | None = None,
        custom_query: Callable[[Select], Select] | None = None,
    ) -> Optional[ModelT]:
        """Mendapatkan objek berdasarkan ID.

        Args:
            allow_deleted (bool, optional): Mengizinkan pengambilan objek yang
                dihapus (soft delete).
            return_none_if_not_found (bool, optional): Jika True, kembalikan None
                alih-alih raise.
            filters (dict[str, Any] | None, optional): Tambahan filter kolom exact
                match.
            options (list[Any] | None, optional): SQLAlchemy loader options
                (selectinload, joinedload, dll).
            condition (list[Any] | None, optional): Daftar ekspresi SQLAlchemy
                tambahan untuk where().
            order_by (Any | None, optional): Ekspresi order_by untuk query.
            custom_query (Callable[[Select], Select] | None, optional): Hook untuk
                memodifikasi stmt.
        """
        # Bangun stmt agar parameter di atas dapat dipakai
        stmt: Select = select(self.model)

        if options:
            stmt = stmt.options(*options)

        # Tambah filters dict
        if filters:
            for attr, value in filters.items():
                stmt = stmt.where(getattr(self.model, attr) == value)

        # Tambah condition list
        if condition:
            stmt = stmt.where(*condition)

        if order_by is not None:
            stmt = stmt.order_by(order_by)

        if custom_query is not None:
            stmt = custom_query(stmt)

        res = await self.session.execute(stmt)
        instance: Optional[ModelT] = res.scalars().first()

        # Jika objek tidak ditemukan
        if instance is None:
            if return_none_if_not_found:
                return None
            raise self._exception_not_found()

        # Jika objek ditemukan namun soft-deleted dan tidak diizinkan
        if (not allow_deleted) and self._is_deleted(instance):
            if return_none_if_not_found:
                return None
            raise self._exception_not_found()

        return instance

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
        filters: dict[str, Any] | None = None,
        order_by: Any | None = None,
        custom_query: Callable[[Select], Select] | None = None,
    ) -> Sequence[ModelT]:
        """Mendapatkan daftar / list objek

        Args:
            skip (int, optional): Jumlah objek yang dilewati. Defaults to 0.
            limit (int, optional): Jumlah objek yang diambil. Defaults to 100.
            include_deleted (bool, optional): Mengizinkan pengambilan objek yang
                dihapus. Defaults to False.
            filters (dict[str, Any] | None, optional): Filter untuk pencarian objek.
                Defaults to None.
            order_by (Any | None, optional): Urutan pengambilan objek. Defaults to
                None.
            custom_query (Any, optional): Custom SQLAlchemy query untuk modifikasi
                lebih lanjut.

        Returns:
            Sequence[ModelT]: Daftar objek yang ditemukan.
        """

        stmt = select(self.model)

        # Tambahkan filter jika ada
        if filters:
            for attr, value in filters.items():
                stmt = stmt.where(getattr(self.model, attr) == value)

        # Tambahkan filter untuk soft delete
        if not include_deleted and hasattr(self.model, self.soft_delete_field):
            stmt = stmt.where(getattr(self.model, self.soft_delete_field).is_(None))

        # Tambahkan urutan jika ada
        if order_by is not None:
            stmt = stmt.order_by(order_by)

        # Tambahkan custom query jika ada
        if custom_query is not None:
            stmt = custom_query(stmt)

        # Tambahkan pagination
        stmt = stmt.offset(skip).limit(limit)

        # Eksekusi query
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def pagination(
        self,
        *,
        page: int = 1,
        per_page: int = 10,
        include_deleted: bool = False,
        filters: dict[str, Any] | None = None,
        order_by: Any | None = None,
        custom_query: Callable[[Select], Select] | None = None,
    ):
        """Mendapatkan daftar / list objek

        Args:
            skip (int, optional): Jumlah objek yang dilewati. Defaults to 0.
            limit (int, optional): Jumlah objek yang diambil. Defaults to 100.
            include_deleted (bool, optional): Mengizinkan pengambilan objek yang
                dihapus. Defaults to False.
            filters (dict[str, Any] | None, optional): Filter untuk pencarian objek.
                Defaults to None.
            order_by (Any | None, optional): Urutan pengambilan objek. Defaults to
                None.
            custom_query (Any, optional): Custom SQLAlchemy query untuk modifikasi
                lebih lanjut.

        Returns:
            Sequence[ModelT]: Daftar objek yang ditemukan.
        """

        stmt = select(self.model)

        # Tambahkan filter jika ada
        if filters:
            for attr, value in filters.items():
                stmt = stmt.where(getattr(self.model, attr) == value)

        # Tambahkan filter untuk soft delete
        if not include_deleted and hasattr(self.model, self.soft_delete_field):
            stmt = stmt.where(getattr(self.model, self.soft_delete_field).is_(None))

        # Tambahkan urutan jika ada
        if order_by is not None:
            stmt = stmt.order_by(order_by)

        # Tambahkan custom query jika ada
        if custom_query is not None:
            stmt = custom_query(stmt)

        # Tambahkan pagination
        return await paginate(self.session, stmt, page=page, per_page=per_page)

    async def create(
        self,
        obj_in: CreateSchemaT,
        *,
        extra_fields: dict[str, Any] | None = None,
    ) -> ModelT:
        """Membuat objek baru.

        Args:
            obj_in (CreateSchemaT): Objek yang akan dibuat.
            extra_fields (dict[str, Any] | None, optional): Field tambahan untuk
                objek. Defaults to None.

        Returns:
            ModelT: Objek yang telah dibuat.
        """

        data = obj_in.model_dump() if hasattr(obj_in, "model_dump") else dict(obj_in)  # type: ignore
        if extra_fields:
            data.update(extra_fields)

        # buat instance baru bedasarkan data yang diberikan
        instance = self.model(**data)

        # Tambahkan instance ke session
        self.session.add(instance)
        await self.session.flush()

        # Panggil hook on_created
        await self.on_created(instance, **extra_fields or {})

        return await self._save(instance)

    async def update(
        self,
        obj: ModelT,
        obj_in: UpdateSchemaT | dict[str, Any],
    ) -> ModelT:
        """Memperbarui objek yang ada.

        Args:
            obj (int): Objek yang akan diperbarui.
            obj_in (UpdateSchemaT): Data yang akan diperbarui.

        Returns:
            ModelT: Objek yang telah diperbarui.
        """

        update_data = (
            obj_in.model_dump(exclude_unset=True)
            if not isinstance(obj_in, dict)
            else dict(obj_in)
        )
        # simpan data perubahan
        changed: dict[str, dict[str, Any]] = {}

        # Perbarui field yang ada. diasumsukan semua field sama
        for k, v in update_data.items():
            old_v = getattr(obj, k, None)
            # Membandingkan nilai lama dan baru
            if old_v != v:
                changed[k] = {"from": old_v, "to": v}
                setattr(obj, k, v)

        self.session.add(obj)

        # Panggil hook on_updated
        await self.on_updated(obj, **changed)

        return await self._save(obj)

    async def soft_delete(
        self, obj_id: int | None = None, obj: ModelT | None = None
    ) -> None:
        """Menghapus objek secara soft delete.

        Args:
            obj_id (int): ID objek yang akan dihapus.
        """

        if obj_id is None and obj is None:
            raise ValueError("Either obj_id or obj must be provided")

        if obj_id:
            instance = await self.get(obj_id)

        else:
            instance = obj

        if hasattr(instance, self.soft_delete_field):
            setattr(
                instance,
                self.soft_delete_field,
                datetime.datetime.now(datetime.timezone.utc),
            )
            self.session.add(instance)
        else:
            # fallback ke hard delete
            await self.session.delete(instance)

        # Panggil hook on_soft_deleted
        await self.on_soft_deleted(instance)  # type: ignore

        await self.session.commit()

    async def hard_delete(
        self, obj_id: int | None = None, obj: ModelT | None = None
    ) -> None:
        """Menghapus objek secara hard delete.

        Args:
            obj_id (int | None): ID objek yang akan dihapus.
            obj (ModelT | None): Objek yang akan dihapus.
        """

        if obj_id is None and obj is None:
            raise ValueError("Either obj_id or obj must be provided")

        if obj_id:
            instance = await self.get(obj_id)
        else:
            instance = obj

        await self.session.delete(instance)

        # Panggil hook on_hard_deleted
        await self.on_hard_deleted(instance)  # type: ignore

        await self.session.commit()

    # ============ Internal Helpers ============

    async def _save(self, instance: ModelT, *, commit: bool = True) -> ModelT:
        """Menyimpan objek ke database.

        Args:
            instance (ModelT): Objek yang akan disimpan.

        Returns:
            ModelT: Objek yang telah disimpan.
        """
        if commit:
            await self.session.commit()
            await self.session.refresh(instance)
        return instance

    def _is_deleted(self, instance: ModelT) -> bool:
        """Memeriksa apakah objek telah dihapus.

        Args:
            instance (ModelT): Objek yang akan diperiksa.

        Returns:
            bool: True jika objek telah dihapus, False sebaliknya.
        """

        # Prefer property 'is_deleted' jika ada
        if hasattr(instance, self.is_deleted_attr):
            return bool(getattr(instance, self.is_deleted_attr))
        # Fallback: cek kolom deleted_at
        if hasattr(instance, self.soft_delete_field):
            return getattr(instance, self.soft_delete_field) is not None
        return False

    def _exception_not_found(self, **extra) -> Exception:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": self.not_found_error_code,
                "message": "Item tidak ditemukan.",
                **extra,
            },
        )

    async def on_created(self, instance: ModelT, **kwargs) -> None:
        """Event handler yang dipanggil setelah objek dibuat.

        Args:
            instance (ModelT): Objek yang baru dibuat.
        """

    async def on_updated(self, instance: ModelT, **kwargs) -> None:
        """Event handler yang dipanggil setelah objek diperbarui.

        Args:
            instance (ModelT): Objek yang telah diperbarui.
        """

    async def on_soft_deleted(self, instance: ModelT, **kwargs) -> None:
        """Event handler yang dipanggil setelah objek dihapus secara soft delete.

        Args:
            instance (ModelT): Objek yang telah dihapus.
        """

    async def on_hard_deleted(self, instance: ModelT, **kwargs) -> None:
        """Event handler yang dipanggil setelah objek dihapus secara hard delete.

        Args:
            instance (ModelT): Objek yang telah dihapus.
        """
