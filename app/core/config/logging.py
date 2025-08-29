# app/core/logging_config.py

import logging

from rich.logging import RichHandler

logger = logging.getLogger(__name__)


def configure_logging():
    """
    Mengatur logging untuk menggunakan RichHandler di seluruh aplikasi.
    """
    # Buat instance RichHandler dengan konfigurasi yang diinginkan
    rich_handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
    )

    # Konfigurasi basicConfig untuk root logger
    # force=True akan menghapus semua handler yang sudah ada
    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[rich_handler],
        force=True,
    )

    # Atur level logging untuk root logger
    logging.root.setLevel(logging.INFO)

    # Hapus semua logger yang mungkin sudah dikonfigurasi
    loggers = (
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
        "asyncio",
        "starlette",
    )

    for logger_name in loggers:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = []
        logging_logger.propagate = True

    # Beri log konfirmasi
    logging.root.setLevel(logging.DEBUG)
    logger.info("Logging telah dikonfigurasi dengan RichHandler.")
