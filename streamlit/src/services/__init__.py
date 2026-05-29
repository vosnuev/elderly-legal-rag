from __future__ import annotations

from typing import Any


def example_chat_messages(*args: Any, **kwargs: Any) -> Any:
    from .chat_flow import example_chat_messages as _example_chat_messages

    return _example_chat_messages(*args, **kwargs)


def submit_consultation_message(*args: Any, **kwargs: Any) -> Any:
    from .chat_flow import submit_consultation_message as _submit_consultation_message

    return _submit_consultation_message(*args, **kwargs)


def submit_initial_consultation(*args: Any, **kwargs: Any) -> Any:
    from .chat_flow import submit_initial_consultation as _submit_initial_consultation

    return _submit_initial_consultation(*args, **kwargs)

__all__ = [
    "example_chat_messages",
    "submit_consultation_message",
    "submit_initial_consultation",
]
