"""ORM models. Importing this package registers all models on ``Base.metadata``."""

from app.models.user import User

__all__ = ["User"]
