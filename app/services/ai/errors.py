"""AI-specific domain errors."""

from app.services.exceptions import AppError


class AIError(AppError):
    """Base class for AI failures."""

    status_code = 502
    detail = "ai service error"


class AIUnavailableError(AIError):
    """The AI provider is not configured or could not be reached."""

    status_code = 503
    detail = "ai service is not configured or unavailable"


class AIResponseError(AIError):
    """The model returned a malformed or schema-invalid payload."""

    status_code = 502
    detail = "ai service returned an invalid response"
