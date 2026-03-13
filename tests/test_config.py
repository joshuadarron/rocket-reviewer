"""Tests for configuration loading."""

from __future__ import annotations

from src.config import AGENT_ROUTING, BOT_USERNAMES, MODELS


class TestConstants:
    """Tests for project-wide constants."""

    def test_all_models_defined(self) -> None:
        assert "claude-reviewer" in MODELS
        assert "gpt-reviewer" in MODELS
        assert "gemini-reviewer" in MODELS
        assert "aggregator" in MODELS

    def test_agent_routing_maps_all_bots(self) -> None:
        assert len(AGENT_ROUTING) == 3
        assert "claude-reviewer[bot]" in AGENT_ROUTING
        assert "gpt-reviewer[bot]" in AGENT_ROUTING
        assert "gemini-reviewer[bot]" in AGENT_ROUTING

    def test_bot_usernames_matches_routing_keys(self) -> None:
        assert set(AGENT_ROUTING.keys()) == BOT_USERNAMES

    def test_routing_values_match_model_keys(self) -> None:
        for node_id in AGENT_ROUTING.values():
            assert node_id in MODELS
