from __future__ import annotations

import io
import re
from typing import Any, Dict

import cloudinary
import cloudinary.uploader

from app.core.config import settings


def init_cloudinary() -> None:
    """
    Inisialisasi Cloudinary Configurasi.
    """

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def upload_bytes(
    *,
    file_bytes: bytes,
    filename: str,
    resource_type: str = "auto",
    folder: str = "attachments",
) -> Dict[str, Any]:
    """Upload file ke Cloudinary.

    Args:
        file_bytes (bytes): Konten file dalam bentuk bytes.
        filename (str): Nama file yang akan digunakan di Cloudinary.
        resource_type (str, optional): Tipe resource yang akan diupload. Defaults to
            "auto".
        folder (str, optional): Nama folder di Cloudinary. Defaults to "attachments".

    Returns:
        Dict[str, Any]: Hasil upload dari Cloudinary.
    """
    init_cloudinary()
    return cloudinary.uploader.upload(
        io.BytesIO(file_bytes),
        public_id=None,
        resource_type=resource_type,
        folder=folder,
        use_filename=True,
        unique_filename=True,
        overwrite=False,
        filename=filename,
    )


def destroy_by_url(file_url: str) -> Dict[str, Any]:
    """
    Hapus resource berdasarkan URL Cloudinary.
    Mengambil public_id dari URL: .../upload/v<version>/<public_id>.<ext>
    """
    init_cloudinary()
    m = re.search(r"/upload/(?:v\d+/)?([^/.]+)(?:\.[a-zA-Z0-9]+)?$", file_url)
    public_id = m.group(1) if m else None
    if not public_id:
        return {"result": "not_found"}

    return cloudinary.uploader.destroy(public_id, resource_type="auto")
