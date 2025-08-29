from __future__ import annotations

import io
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


def extract_public_id(cloudinary_url: str) -> str:
    """
    Ekstrak public_id dari URL Cloudinary.

    Args:
        cloudinary_url: URL Cloudinary

    Returns:
        str: Public ID
    """
    # Format URL: https://res.cloudinary.com/{cloud_name}/{resource_type}/upload/{version}/{public_id}.{format}
    parts = cloudinary_url.split("/")
    public_id_with_ext = parts[-1]
    # Hapus ekstensi file
    public_id = ".".join(public_id_with_ext.split(".")[:-1])
    folder = parts[-2]
    return f"{folder}/{public_id}"


def destroy_by_url(file_url: str) -> Dict[str, Any]:
    """
    Hapus resource berdasarkan URL Cloudinary.
    Mengambil public_id dari URL: .../upload/v<version>/<public_id>.<ext>
    """
    public_id = extract_public_id(file_url)
    if not public_id:
        return {"result": "not_found"}

    return cloudinary.uploader.destroy(public_id)
