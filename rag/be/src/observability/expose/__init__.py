"""API-facing observability adapters that expose streams to clients."""

from observability.expose.sse import observability_stream_response

__all__ = ["observability_stream_response"]
