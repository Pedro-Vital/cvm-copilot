"""structlog setup. Call `configure_logging()` once at process start."""

import structlog


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            # The default formatter (rich, with local variables) renders
            # tracebacks through PydanticAI's agent graph for minutes; plain
            # tracebacks keep the same information and stay fast.
            structlog.dev.ConsoleRenderer(exception_formatter=structlog.dev.plain_traceback),
        ]
    )
