"""Layanan untuk mengelola lampiran (attachment) pada tugas dan komentar.

Fitur utama:
- Mengambil lampiran berdasarkan ID atau daftar lampiran per tugas.
- Membuat lampiran berbasis tautan (link) untuk tugas atau komentar.
- Mengunggah berkas (file) ke penyimpanan (Cloudinary) dan mencatat metadata.
- Memicu event untuk proses unggah/hapus asinkron.
- Validasi tipe MIME dan batas ukuran berkas.

Catatan:
- Ukuran berkas maksimum: 5 MB.
- Tipe file yang didukung: PNG, JPG/JPEG, PDF, DOC, DOCX.
"""

import logging
from typing import List

from fastapi import UploadFile

from app.core.domain.events.attachment import (
    AttachmentDeleteRequestedEvent,
    AttachmentUploadRequestedEvent,
)
from app.db.models.attachment_model import Attachment
from app.db.models.role_model import Role
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.attachment import AttachmentLinkCreate
from app.schemas.user import User
from app.utils import exceptions
from app.utils.cloudinary import upload_bytes

ALLOWED_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",  # noqa: E501
    "application/msword": ".doc",
}

MAX_SIZE = 5 * 1024 * 1024  # 5 MB

logger = logging.getLogger(__name__)


class AttachmentService:
    """Service untuk operasi terkait attachment."""

    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.repo = self.uow.attachment_repo

    async def get_attachment(self, attachment_id: int) -> Attachment | None:
        """Mengambil detail lampiran berdasarkan ID.

        Args:
            attachment_id: ID lampiran.

        Returns:
            Objek Attachment jika ditemukan, selain itu None.
        """
        return await self.repo.get_by_id(attachment_id)

    async def get_attachments_by_task(self, task_id: int) -> List[Attachment]:
        """Mengambil semua lampiran milik sebuah tugas.

        Args:
            task_id: ID tugas yang ingin diambil lampirannya.

        Returns:
            Daftar Attachment yang terkait dengan tugas.
        """
        return await self.repo.list_by_reference(task_id=task_id)

    async def create_link_task_attachment(
        self,
        *,
        payload: AttachmentLinkCreate,
        task_id: int,
        user: User,
    ) -> Attachment:
        """Membuat lampiran berupa tautan (link) untuk sebuah tugas.

        Pengguna non-admin harus merupakan anggota proyek dari tugas tersebut.

        Args:
            payload: Data link lampiran (nama file dan URL).
            task_id: ID tugas yang akan dilampiri.
            user: Pengguna yang melakukan aksi.

        Returns:
            Attachment yang berhasil dibuat.

        Raises:
            NotAMemberError: Jika pengguna bukan anggota proyek terkait tugas.
        """
        if user.role != Role.ADMIN:
            is_member = await self.uow.task_repo.is_user_member_of_task_project(
                task_id=task_id, user_id=user.id
            )
            if not is_member:
                raise exceptions.NotAMemberError("Anda bukan anggota proyek ini.")

        att: Attachment = await self.repo.create_attachment(
            payload={
                "user_id": user.id,
                "task_id": task_id,
                "comment_id": None,
                "file_name": payload.file_name,
                "file_size": "0",
                "file_path": payload.link,
                "mime_type": "hyperlink",
            }
        )
        logger.info("attachment.upload.done", extra={"attachment_id": att.id})
        return att

    async def create_link_comment_attachment(
        self,
        *,
        comment_id: int,
        payload: AttachmentLinkCreate,
        user: User,
    ) -> Attachment:
        """Membuat lampiran berupa tautan (link) untuk sebuah komentar.

        Hanya pemilik komentar yang dapat menambahkan lampiran pada komentar
        tersebut.

        Args:
            comment_id: ID komentar yang akan dilampiri.
            payload: Data link lampiran (nama file dan URL).
            user: Pengguna yang melakukan aksi.

        Returns:
            Attachment yang berhasil dibuat.

        Raises:
            CommentNotFoundError: Jika komentar tidak ditemukan.
            ForbiddenError: Jika pengguna bukan pemilik komentar.
        """
        comment = await self.uow.comment_repo.get_by_id(comment_id=comment_id)

        if comment is None:
            raise exceptions.CommentNotFoundError("Komentar tidak ditemukan.")

        if comment.user_id != user.id:
            raise exceptions.ForbiddenError(
                "Anda tidak memiliki izin untuk mengunggah lampiran ini."
            )

        att: Attachment = await self.repo.create_attachment(
            payload={
                "user_id": user.id,
                "task_id": None,
                "comment_id": comment_id,
                "file_name": payload.file_name,
                "file_size": str("0"),
                "file_path": payload.link,
                "mime_type": "hyperlink",
            }
        )
        logger.info("attachment.upload.done", extra={"attachment_id": att.id})
        return att

    async def create_task_attachment(
        self,
        *,
        file: UploadFile,
        task_id: int,
        actor: User,
        is_admin: bool = False,
    ) -> Attachment:
        """Mengunggah lampiran berkas untuk sebuah tugas.

        Pengguna non-admin harus merupakan anggota proyek dari tugas tersebut.
        Validasi dilakukan terhadap tipe konten (MIME) dan ukuran berkas.

        Args:
            file: Berkas yang akan diunggah.
            task_id: ID tugas tujuan lampiran.
            actor: Pengguna yang melakukan aksi.
            is_admin: True jika aksi dilakukan dalam konteks admin.

        Returns:
            Attachment yang berhasil dibuat.

        Raises:
            NotAMemberError: Jika pengguna bukan anggota proyek terkait tugas (dan
                bukan admin).
            MediaNotSupportedError: Jika tipe berkas tidak didukung.
            FileTooLargeError: Jika ukuran berkas melebihi batas.
        """
        if not is_admin:
            is_member = await self.uow.task_repo.is_user_member_of_task_project(
                task_id=task_id, user_id=actor.id
            )
            if not is_member:
                raise exceptions.NotAMemberError("Anda bukan anggota proyek ini.")

        if file.content_type not in ALLOWED_EXTENSIONS:
            raise exceptions.MediaNotSupportedError(
                "Tipe file tidak didukung. Hanya PNG, JPG/JPEG, PDF, dan WORD."
            )

        file_bytes = await file.read()
        file_size = len(file_bytes)
        if file_size > MAX_SIZE:
            raise exceptions.FileTooLargeError(
                "Ukuran file melebihi batas yang diizinkan."
            )

        return await self.upload_attachment(
            user=actor,
            file=file,
            file_bytes=file_bytes,
            task_id=task_id,
            file_size=str(file_size),
            comment_id=None,
        )

    async def create_comment_attachment(
        self,
        *,
        file: UploadFile,
        comment_id: int,
        actor: User,
    ) -> Attachment:
        """Mengunggah lampiran berkas untuk sebuah komentar.

        Hanya pemilik komentar yang dapat menambahkan lampiran pada komentar
        tersebut. Validasi dilakukan terhadap tipe konten (MIME) dan ukuran berkas.

        Args:
            file: Berkas yang akan diunggah.
            comment_id: ID komentar tujuan lampiran.
            actor: Pengguna yang melakukan aksi.

        Returns:
            Attachment yang berhasil dibuat.

        Raises:
            CommentNotFoundError: Jika komentar tidak ditemukan.
            ForbiddenError: Jika pengguna bukan pemilik komentar.
            MediaNotSupportedError: Jika tipe berkas tidak didukung.
            FileTooLargeError: Jika ukuran berkas melebihi batas.
        """
        comment = await self.uow.comment_repo.get_by_id(comment_id=comment_id)

        if comment is None:
            raise exceptions.CommentNotFoundError("Komentar tidak ditemukan.")

        if comment.user_id != actor.id:
            raise exceptions.ForbiddenError(
                "Anda tidak memiliki izin untuk mengunggah lampiran ini."
            )

        if file.content_type not in ALLOWED_EXTENSIONS:
            raise exceptions.MediaNotSupportedError(
                "Tipe file tidak didukung. Hanya PNG, JPG/JPEG, PDF, dan WORD."
            )

        file_bytes = await file.read()
        file_size = len(file_bytes)
        if file_size > MAX_SIZE:
            raise exceptions.FileTooLargeError(
                "Ukuran file melebihi batas yang diizinkan."
            )

        return await self.upload_attachment(
            user=actor,
            file=file,
            file_bytes=file_bytes,
            task_id=comment.task_id,
            file_size=str(file_size),
            comment_id=comment_id,
        )

    async def upload_attachment(
        self,
        *,
        user: User,
        file: UploadFile,
        file_bytes: bytes,
        file_size: str,
        task_id: int,
        comment_id: int | None = None,
    ) -> Attachment:
        """Mengunggah berkas ke penyimpanan dan membuat record lampiran.

        Proses ini langsung mengunggah ke Cloudinary melalui helper upload_bytes.
        Jika unggah gagal, tetap membuat record dengan penanda error.

        Args:
            user: Pengguna yang melakukan unggah.
            file: Objek UploadFile asli dari FastAPI.
            file_bytes: Isi berkas dalam bentuk bytes.
            file_size: Ukuran berkas dalam bentuk string (informasional).
            task_id: ID tugas tujuan lampiran.
            comment_id: ID komentar tujuan lampiran, jika ada.

        Returns:
            Attachment yang tercatat pada basis data.
        """
        logger.info("attachment.upload.start")
        try:
            result = upload_bytes(
                file_bytes=file_bytes, filename=file.filename or "attachment"
            )
            url = result.get("secure_url") or result.get("url") or ""
            bytes_size = result.get("bytes") or len(file_bytes)

            att: Attachment = await self.repo.create_attachment(
                payload={
                    "user_id": user.id,
                    "task_id": task_id,
                    "comment_id": comment_id,
                    "file_name": file.filename or "attachment",
                    "file_size": str(bytes_size),
                    "file_path": url,
                    "mime_type": file.content_type or "application/octet-stream",
                }
            )
            logger.info("attachment.upload.done", extra={"attachment_id": att.id})
        except Exception as e:
            logger.exception("attachment.upload.failed", extra={"error": str(e)})
            att: Attachment = await self.repo.create_attachment(
                payload={
                    "user_id": user.id,
                    "task_id": task_id,
                    "comment_id": comment_id,
                    "file_name": file.filename or "attachment",
                    "file_size": "",
                    "file_path": "Error Uploading",
                    "mime_type": file.content_type or "application/octet-stream",
                }
            )
        return att

    async def upload_attachment_with_event(
        self,
        *,
        user: User,
        file: UploadFile,
        file_bytes: bytes,
        file_size: str,
        task_id: int,
        comment_id: int | None = None,
    ) -> Attachment:
        """Mengantrikan proses unggah berkas melalui event domain.

        Metode ini hanya membuat record awal dengan status "Progress Upload ..."
        lalu mem-publish event AttachmentUploadRequestedEvent untuk diproses
        di background.

        Args:
            user: Pengguna yang melakukan unggah.
            file: Objek UploadFile asli dari FastAPI.
            file_bytes: Isi berkas dalam bentuk bytes.
            file_size: Ukuran berkas dalam bentuk string.
            task_id: ID tugas tujuan lampiran.
            comment_id: ID komentar tujuan lampiran, jika ada.

        Returns:
            Attachment awal yang disimpan, sebelum proses unggah selesai.
        """
        att: Attachment = await self.repo.create_attachment(
            payload={
                "user_id": user.id,
                "task_id": task_id,
                "comment_id": comment_id,
                "file_name": file.filename or "attachment",
                "file_size": file_size,
                "file_path": "Progress Upload ...",
                "mime_type": file.content_type or "application/octet-stream",
            }
        )

        self.uow.add_event(
            AttachmentUploadRequestedEvent(
                attachment_id=att.id,
                task_id=task_id,
                user_id=user.id,
                comment_id=comment_id,
                file_bytes=file_bytes,
                content_type=file.content_type or "application/octet-stream",
                original_filename=file.filename or "attachment",
            )
        )
        return att

    async def delete_attachment(self, attachment_id: int, actor: User) -> None:
        """Menghapus lampiran beserta memicu penghapusan file di penyimpanan.

        Aturan akses:
        - Admin dapat menghapus lampiran apa pun.
        - Non-admin harus pemilik proyek tempat tugas lampiran berada.

        Args:
            attachment_id: ID lampiran yang akan dihapus.
            actor: Pengguna yang melakukan aksi.

        Raises:
            AttachmentNotFoundError: Jika lampiran tidak ditemukan.
            TaskNotFoundError: Jika tugas terkait lampiran tidak ditemukan.
            ForbiddenError: Jika pengguna bukan pemilik proyek (dan bukan admin).
        """

        attachment = await self.get_attachment(attachment_id)
        if not attachment:
            raise exceptions.AttachmentNotFoundError("Attachment tidak ditemukan.")

        if actor.role != Role.ADMIN:
            task = await self.uow.task_repo.get_by_id(task_id=attachment.task_id)
            if not task:
                raise exceptions.TaskNotFoundError

            is_owner = await self.uow.project_repo.is_user_owner_of_project(
                project_id=task.project_id, user_id=actor.id
            )

            if not is_owner:
                raise exceptions.ForbiddenError("Anda bukan pemilik proyek ini.")

        # Trigger event untuk delete file dari cloudinary di background
        self.uow.add_event(
            AttachmentDeleteRequestedEvent(
                attachment_id=attachment.id,
                file_url=attachment.file_path,
            )
        )

        await self.repo.delete_by_id(attachment.id)
