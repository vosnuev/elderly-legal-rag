from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import SecretStr

from external.openrouter import client


class OpenRouterClientTest(unittest.TestCase):
    def test_chat_model_passes_provider_routing_body(self) -> None:
        fake_settings = SimpleNamespace(
            openrouter_api_key=SecretStr("test-key"),
            graph_llm_model="deepseek/deepseek-v4-pro",
            llm_model=None,
            openrouter_base_url="https://openrouter.ai/api/v1",
            query_timeout_ms=30_000,
            graph_llm_provider="deepseek",
            graph_llm_provider_allow_fallbacks=False,
            graph_llm_thinking="disabled",
            graph_llm_request_timeout_seconds=60,
            graph_llm_stream_chunk_timeout_seconds=45,
            graph_llm_max_retries=3,
        )

        with (
            patch("external.openrouter.client.settings", fake_settings),
            patch("external.openrouter.client.ChatOpenAI") as chat_openai,
        ):
            client.create_openrouter_chat_model()

        chat_openai.assert_called_once()
        kwargs = chat_openai.call_args.kwargs
        self.assertEqual(kwargs["model"], "deepseek/deepseek-v4-pro")
        self.assertEqual(kwargs["timeout"], 60)
        self.assertEqual(kwargs["stream_chunk_timeout"], 45)
        self.assertEqual(kwargs["max_retries"], 3)
        self.assertEqual(
            kwargs["extra_body"],
            {
                "provider": {
                    "order": ["deepseek"],
                    "allow_fallbacks": False,
                },
                "thinking": {"type": "disabled"},
            },
        )

    def test_chat_model_omits_provider_routing_body_when_unset(self) -> None:
        fake_settings = SimpleNamespace(
            openrouter_api_key=SecretStr("test-key"),
            graph_llm_model="openai/gpt-oss-120b",
            llm_model=None,
            openrouter_base_url="https://openrouter.ai/api/v1",
            query_timeout_ms=30_000,
            graph_llm_provider="",
            graph_llm_provider_allow_fallbacks=False,
            graph_llm_thinking="",
            graph_llm_request_timeout_seconds=60,
            graph_llm_stream_chunk_timeout_seconds=60,
            graph_llm_max_retries=2,
        )

        with (
            patch("external.openrouter.client.settings", fake_settings),
            patch("external.openrouter.client.ChatOpenAI") as chat_openai,
        ):
            client.create_openrouter_chat_model()

        self.assertIsNone(chat_openai.call_args.kwargs["extra_body"])

    def test_chat_model_can_skip_configured_provider_route(self) -> None:
        fake_settings = SimpleNamespace(
            openrouter_api_key=SecretStr("test-key"),
            graph_llm_model="openai/gpt-oss-120b",
            llm_model=None,
            openrouter_base_url="https://openrouter.ai/api/v1",
            query_timeout_ms=30_000,
            graph_llm_provider="cerebras",
            graph_llm_provider_allow_fallbacks=True,
            graph_llm_thinking="",
            graph_llm_request_timeout_seconds=60,
            graph_llm_stream_chunk_timeout_seconds=60,
            graph_llm_max_retries=2,
        )

        with (
            patch("external.openrouter.client.settings", fake_settings),
            patch("external.openrouter.client.ChatOpenAI") as chat_openai,
        ):
            client.create_openrouter_chat_model(use_default_provider=False)

        self.assertIsNone(chat_openai.call_args.kwargs["extra_body"])

    def test_chat_model_uses_explicit_agent_route(self) -> None:
        fake_settings = SimpleNamespace(
            openrouter_api_key=SecretStr("test-key"),
            graph_llm_model="openai/gpt-oss-120b",
            llm_model=None,
            openrouter_base_url="https://openrouter.ai/api/v1",
            query_timeout_ms=30_000,
            graph_llm_provider="groq",
            graph_llm_provider_allow_fallbacks=False,
            graph_llm_thinking="",
            graph_llm_request_timeout_seconds=60,
            graph_llm_stream_chunk_timeout_seconds=60,
            graph_llm_max_retries=2,
        )

        with (
            patch("external.openrouter.client.settings", fake_settings),
            patch("external.openrouter.client.ChatOpenAI") as chat_openai,
        ):
            client.create_openrouter_chat_model(
                model_name="deepseek/deepseek-v4-pro",
                use_default_provider=False,
                provider="deepseek",
                allow_provider_fallbacks=True,
                thinking="disabled",
            )

        kwargs = chat_openai.call_args.kwargs
        self.assertEqual(kwargs["model"], "deepseek/deepseek-v4-pro")
        self.assertEqual(
            kwargs["extra_body"],
            {
                "provider": {
                    "order": ["deepseek"],
                    "allow_fallbacks": True,
                },
                "thinking": {"type": "disabled"},
            },
        )


if __name__ == "__main__":
    unittest.main()
