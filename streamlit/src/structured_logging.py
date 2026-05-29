from __future__ import annotations

import logging
import os
import sys

import structlog


_CONFIGURED = False
_CONTEXT_INDENT = "    "


def _should_use_colors() -> bool:
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _format_context_value(value: object) -> str:
    if isinstance(value, str):
        if value == "" or set(value) & {" ", "\t", "=", "\r", "\n", '"', "'"}:
            return repr(value)
        return value

    return repr(value)


class _IndentedKeyValueColumnFormatter:
    def __init__(self, styles: structlog.dev.ColumnStyles) -> None:
        self._styles = styles

    def __call__(self, key: str, value: object) -> str:
        styles = self._styles
        return (
            f"\n{_CONTEXT_INDENT}"
            f"{styles.kv_key}{key}{styles.reset}="
            f"{styles.kv_value}{_format_context_value(value)}{styles.reset}"
        )


def _console_renderer(colors: bool | None = None) -> structlog.dev.ConsoleRenderer:
    use_colors = _should_use_colors() if colors is None else colors
    styles = structlog.dev.ConsoleRenderer.get_default_column_styles(use_colors)
    default_level_styles = structlog.dev.ConsoleRenderer.get_default_level_styles(
        use_colors
    )
    level_styles = {
        level: style + styles.bright
        for level, style in default_level_styles.items()
    }
    logger_name_formatter = structlog.dev.KeyValueColumnFormatter(
        key_style=None,
        value_style=styles.bright + styles.logger_name,
        reset_style=styles.reset,
        value_repr=str,
        prefix="[",
        postfix="]",
    )

    return structlog.dev.ConsoleRenderer(
        columns=[
            structlog.dev.Column(
                "timestamp",
                structlog.dev.KeyValueColumnFormatter(
                    key_style=None,
                    value_style=styles.timestamp,
                    reset_style=styles.reset,
                    value_repr=str,
                ),
            ),
            structlog.dev.Column(
                "level",
                structlog.dev.LogLevelColumnFormatter(
                    level_styles,
                    reset_style=styles.reset,
                ),
            ),
            structlog.dev.Column(
                "event",
                structlog.dev.KeyValueColumnFormatter(
                    key_style=None,
                    value_style=styles.bright,
                    reset_style=styles.reset,
                    value_repr=str,
                    width=30,
                ),
            ),
            structlog.dev.Column("logger", logger_name_formatter),
            structlog.dev.Column("", _IndentedKeyValueColumnFormatter(styles)),
        ],
    )


def configure_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED

    if _CONFIGURED:
        return

    logging.basicConfig(
        format="%(message)s",
        level=level,
        stream=sys.stdout,
    )

    structlog.configure(
        cache_logger_on_first_use=True,
        logger_factory=structlog.stdlib.LoggerFactory(),
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            _console_renderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
    )

    _CONFIGURED = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    configure_logging()
    return structlog.get_logger(name)
