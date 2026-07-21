"""Logging configuration."""

import logging


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging with a consistent format.

    Idempotent enough for repeated calls in tests via ``force=True``.
    """
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
