from starlette.middleware import Middleware

from .request import RequestMiddleware

__all__ = ("RequestMiddleware", "middleware")

middleware = [Middleware(RequestMiddleware)]
