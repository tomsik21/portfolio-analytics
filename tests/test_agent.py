"""
Agent module tests.

Deliberately does NOT call the real Anthropic API in the test suite —
that would make tests slow, flaky, cost money, and non-deterministic,
none of which belong in a unit test. Instead this tests the two things
that ARE deterministic and worth pinning down: the prompt formatting
(so a future refactor can't silently drop a sector from what the LLM
sees) and the missing-API-key guardrail (so a misconfigured deployment
fails with a clear message instead of an unhandled exception).
"""
import os

import pytest

from app.agent import _format_attribution_for_prompt, summarize_attribution
from app.calculations.brinson import SectorData, brinson_fachler


@pytest.fixture
def sample_attribution():
    sectors = [
        SectorData("Tech", 0.5, 0.3, 0.10, 0.08),
        SectorData("Energy", 0.2, 0.3, 0.02, 0.05),
        SectorData("Health", 0.3, 0.4, 0.06, 0.04),
    ]
    return brinson_fachler(sectors)


class TestFormatAttributionForPrompt:
    def test_includes_every_sector(self, sample_attribution):
        text = _format_attribution_for_prompt(sample_attribution)
        for sector in ("Tech", "Energy", "Health"):
            assert sector in text

    def test_includes_active_return(self, sample_attribution):
        text = _format_attribution_for_prompt(sample_attribution)
        assert "Active return" in text

    def test_no_sectors_dropped_when_result_has_many(self):
        sectors = [
            SectorData(f"Sector{i}", 1 / 5, 1 / 5, 0.01 * i, 0.01 * i)
            for i in range(1, 6)
        ]
        result = brinson_fachler(sectors)
        text = _format_attribution_for_prompt(result)
        for i in range(1, 6):
            assert f"Sector{i}" in text


class TestSummarizeAttributionGuardrails:
    def test_missing_api_key_raises_runtime_error_not_unhandled_exception(
        self, sample_attribution, monkeypatch
    ):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            summarize_attribution(sample_attribution)

    def test_error_message_tells_user_how_to_fix_it(
        self, sample_attribution, monkeypatch
    ):
        """A guardrail error should be actionable, not just descriptive."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="export ANTHROPIC_API_KEY"):
            summarize_attribution(sample_attribution)
