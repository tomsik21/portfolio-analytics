"""
AI insight agent.

Deliberately narrow scope: this agent explains numbers the calculation
engine already produced — it never computes anything itself. That
boundary matters for a QE to be able to articulate clearly: the
deterministic, testable math lives entirely in app/calculations/; the
LLM's only job is turning already-verified numbers into a plain-English
summary a portfolio manager could read without a finance degree.

Requires ANTHROPIC_API_KEY to be set in the environment. If it isn't
set, the endpoint returns a 503 with a clear message rather than
crashing — a real integration point should degrade predictably, not
throw an unhandled exception, when a downstream dependency is missing.
"""
from __future__ import annotations

import os

from app.calculations.brinson import AttributionResult


def _format_attribution_for_prompt(result: AttributionResult) -> str:
    lines = [
        f"Portfolio total return: {result.portfolio_total_return:.4%}",
        f"Benchmark total return: {result.benchmark_total_return:.4%}",
        f"Active return: {result.active_return:.4%}",
        "",
        "Sector breakdown (allocation / selection / interaction / total effect):",
    ]
    for s in result.sector_results:
        lines.append(
            f"  {s.sector}: {s.allocation_effect:+.4%} / {s.selection_effect:+.4%} / "
            f"{s.interaction_effect:+.4%} / {s.total_effect:+.4%}"
        )
    return "\n".join(lines)


def summarize_attribution(result: AttributionResult) -> str:
    """
    Calls the Anthropic API to narrate an already-computed attribution
    result. Raises RuntimeError if the API key is missing or the call
    fails — the caller (main.py) maps this to an HTTP 503.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Set it in your environment to enable "
            "the AI insight agent, e.g.: export ANTHROPIC_API_KEY=sk-ant-..."
        )

    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError(
            "The 'anthropic' package is not installed. Run: pip install anthropic"
        ) from e

    client = anthropic.Anthropic(api_key=api_key)
    data_summary = _format_attribution_for_prompt(result)

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": (
                    "You are a performance analytics assistant for a portfolio "
                    "manager. Given this Brinson-Fachler attribution result, "
                    "write a concise (3-5 sentence) plain-English summary of what "
                    "drove performance this period. Call out the single biggest "
                    "positive and negative contributor by name. Do not restate "
                    "every number — synthesize.\n\n"
                    f"{data_summary}"
                ),
            }
        ],
    )

    return "".join(
        block.text for block in message.content if block.type == "text"
    )
