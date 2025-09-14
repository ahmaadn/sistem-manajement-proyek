import logging

from fastapi import Request
from starlette_context.middleware import ContextMiddleware

logger = logging.getLogger(__name__)


class CustomContextMiddleware(ContextMiddleware):
    async def set_context(self, request: Request) -> dict:
        # Get the standard context from plugins
        context = await super().set_context(request)

        # Add custom data0"
        context["user_info_cache"] = {}
        logger.debug("Custom context initialized with user_info_cache")

        return context
