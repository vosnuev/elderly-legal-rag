from __future__ import annotations

import unittest
from types import SimpleNamespace

from pipeline.sub_agents.llm_settings import (
    agent_model_name,
    agent_provider,
    agent_provider_allow_fallbacks,
    agent_retry_without_provider,
    agent_thinking,
)


class SubAgentLlmSettingsTest(unittest.TestCase):
    def test_agent_override_wins_over_graph_default(self) -> None:
        fake_settings = SimpleNamespace(
            graph_llm_provider="groq",
            graph_llm_provider_allow_fallbacks=False,
            graph_llm_retry_without_provider=False,
            graph_llm_thinking="",
            chunking_agent_llm_model="deepseek/deepseek-v4-pro",
            chunking_agent_llm_provider="deepseek",
            chunking_agent_llm_provider_allow_fallbacks=True,
            chunking_agent_llm_retry_without_provider=True,
            chunking_agent_llm_thinking="disabled",
        )

        self.assertEqual(
            agent_model_name(fake_settings, "chunking_agent_llm_model"),
            "deepseek/deepseek-v4-pro",
        )
        self.assertEqual(
            agent_provider(fake_settings, "chunking_agent_llm_provider"),
            "deepseek",
        )
        self.assertTrue(
            agent_provider_allow_fallbacks(
                fake_settings,
                "chunking_agent_llm_provider_allow_fallbacks",
            )
        )
        self.assertTrue(
            agent_retry_without_provider(
                fake_settings,
                "chunking_agent_llm_retry_without_provider",
            )
        )
        self.assertEqual(
            agent_thinking(fake_settings, "chunking_agent_llm_thinking"),
            "disabled",
        )

    def test_unset_agent_fields_inherit_graph_defaults(self) -> None:
        fake_settings = SimpleNamespace(
            graph_llm_provider="groq",
            graph_llm_provider_allow_fallbacks=True,
            graph_llm_retry_without_provider=True,
            graph_llm_thinking="",
            graph_candidate_agent_llm_model="",
            graph_candidate_agent_llm_provider=None,
            graph_candidate_agent_llm_provider_allow_fallbacks=None,
            graph_candidate_agent_llm_thinking=None,
        )

        self.assertIsNone(
            agent_model_name(fake_settings, "graph_candidate_agent_llm_model")
        )
        self.assertEqual(
            agent_provider(fake_settings, "graph_candidate_agent_llm_provider"),
            "groq",
        )
        self.assertTrue(
            agent_provider_allow_fallbacks(
                fake_settings,
                "graph_candidate_agent_llm_provider_allow_fallbacks",
            )
        )
        self.assertTrue(
            agent_retry_without_provider(
                fake_settings,
                "graph_candidate_agent_llm_retry_without_provider",
            )
        )
        self.assertEqual(
            agent_thinking(fake_settings, "graph_candidate_agent_llm_thinking"),
            "",
        )


if __name__ == "__main__":
    unittest.main()
