"""structlog setup. Call `configure_logging()` once at process start."""

import logging

import structlog

from app.config import settings


def configure_logging() -> None:
    if settings.log_format == "json":
        renderer_processors = [structlog.processors.dict_tracebacks, structlog.processors.JSONRenderer(ensure_ascii=False)]
    else:
        # The default formatter (rich, with local variables) renders
        # tracebacks through PydanticAI's agent graph for minutes; plain
        # tracebacks keep the same information and stay fast.
        renderer_processors = [structlog.dev.ConsoleRenderer(exception_formatter=structlog.dev.plain_traceback)]

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            *renderer_processors,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[settings.log_level]),
    )
