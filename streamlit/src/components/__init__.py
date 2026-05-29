from __future__ import annotations

from typing import Any


def render_chat_history(*args: Any, **kwargs: Any) -> Any:
    from .chat_panel import render_chat_history as _render_chat_history

    return _render_chat_history(*args, **kwargs)


def render_chat_prompt(*args: Any, **kwargs: Any) -> Any:
    from .chat_panel import render_chat_prompt as _render_chat_prompt

    return _render_chat_prompt(*args, **kwargs)


def render_example_chat(*args: Any, **kwargs: Any) -> Any:
    from .chat_panel import render_example_chat as _render_example_chat

    return _render_example_chat(*args, **kwargs)


def render_consultation_summary(*args: Any, **kwargs: Any) -> Any:
    from .consultation_summary import (
        render_consultation_summary as _render_consultation_summary,
    )

    return _render_consultation_summary(*args, **kwargs)


def render_page_hero(*args: Any, **kwargs: Any) -> Any:
    from .page_hero import render_page_hero as _render_page_hero

    return _render_page_hero(*args, **kwargs)

__all__ = [
    "render_chat_history",
    "render_chat_prompt",
    "render_consultation_summary",
    "render_example_chat",
    "render_page_hero",
]
