from fastapi import Request
from starlette.middleware import Middleware
from starlette_context import plugins
from starlette_context.middleware import ContextMiddleware


class CustomContextMiddleware(ContextMiddleware):
    async def set_context(self, request: Request) -> dict:
        # Get the standard context from plugins
        context = await super().set_context(request)

        # Add custom data0"
        context["user_info_cache"] = {}

        return context


request_context_middleware = Middleware(
    ContextMiddleware,
    plugins=(plugins.RequestIdPlugin(), plugins.CorrelationIdPlugin()),
)
