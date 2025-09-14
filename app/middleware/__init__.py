from starlette.middleware import Middleware
from starlette_context import plugins

from .context_middleware import CustomContextMiddleware
from .request_middleware import RequestMiddleware

__all__ = ("CustomContextMiddleware", "RequestMiddleware", "middleware")

middleware = [
    Middleware(RequestMiddleware),
    Middleware(
        CustomContextMiddleware,
        plugins=(plugins.RequestIdPlugin(), plugins.CorrelationIdPlugin()),
    ),
]
