from __future__ import annotations

from typing import Optional

from app.core.domain.event import DomainEvent


class AttachmentUploadRequestedEvent(DomainEvent):
    def __init__(
        self,
        *,
        attachment_id: int,
        task_id: int,
        user_id: int,
        comment_id: Optional[int],
        file_bytes: bytes,
        content_type: str,
        original_filename: str,
    ) -> None:
        super().__init__()
        self.attachment_id = attachment_id
        self.task_id = task_id
        self.user_id = user_id
        self.comment_id = comment_id
        self.file_bytes = file_bytes
        self.content_type = content_type
        self.original_filename = original_filename


class AttachmentDeleteRequestedEvent(DomainEvent):
    def __init__(self, *, attachment_id: int, file_url: str) -> None:
        super().__init__()
        self.attachment_id = attachment_id
        self.file_url = file_url
