"""Domain exceptions shared across services.

Services stay framework-agnostic by raising these; the API layer maps them to
HTTP responses with a single exception handler.
"""


class AppError(Exception):
    """Base class for domain failures carrying an HTTP status and detail."""

    status_code = 400
    detail = "error"


class ResourceNotFoundError(AppError):
    """A requested resource does not exist (or is not visible to the caller)."""

    status_code = 404
    detail = "resource not found"
