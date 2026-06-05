"""Latency benchmark for OpenRouter chat models.

Measures time-to-first-token (TTFT) and total streaming time for a set of
candidate models, then prints a comparison table. Run directly:

    python wheatley_V2/benchmark.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Allow running directly as a script (``python wheatley_V2/benchmark.py``).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

from wheatley_V2.openrouter import OpenRouterClient  # noqa: E402

#: Candidate models to benchmark. ``provider`` is optional OpenRouter routing.
BENCHMARK_MODELS: list[dict] = [
    {
        "label": "deepseek-chat-v3-0324",
        "model": "deepseek/deepseek-chat-v3-0324",
        "provider": None,
    },
    {
        "label": "gemini-2.0-flash-001",
        "model": "google/gemini-2.0-flash-001",
        "provider": None,
    },
    {
        "label": "llama-3.3-70b @ Groq",
        "model": "meta-llama/llama-3.3-70b-instruct",
        "provider": {"order": ["Groq"], "allow_fallbacks": False},
    },
]

#: Short prompt used for every model so results are comparable.
PROMPT = "In one short sentence, say hello and tell me a fun fact about space."

MAX_TOKENS = 120


def benchmark_model(client: OpenRouterClient, spec: dict) -> dict:
    """Run a single streaming completion and time it.

    Args:
        client: Configured OpenRouter client.
        spec: Mapping with ``label``, ``model`` and optional ``provider``.

    Returns:
        A result dict with timing metrics (or an ``error`` key on failure).
    """
    messages = [{"role": "user", "content": PROMPT}]
    start = time.perf_counter()
    ttft: float | None = None
    chars = 0

    try:
        for chunk in client.chat_stream(
            messages,
            model=spec["model"],
            max_tokens=MAX_TOKENS,
            provider=spec.get("provider"),
        ):
            if chunk.text:
                if ttft is None:
                    ttft = time.perf_counter() - start
                chars += len(chunk.text)
        total = time.perf_counter() - start
    except Exception as exc:  # noqa: BLE001 - report any failure inline
        return {"label": spec["label"], "error": str(exc)}

    return {
        "label": spec["label"],
        "ttft": ttft if ttft is not None else float("nan"),
        "total": total,
        "chars": chars,
    }


def print_table(results: list[dict]) -> None:
    """Print a formatted comparison table of benchmark results."""
    header = f"{'Model':<26}{'TTFT (s)':>10}{'Total (s)':>11}{'Chars':>8}"
    print(header)
    print("-" * len(header))
    for r in results:
        if "error" in r:
            print(f"{r['label']:<26}  ERROR: {r['error']}")
            continue
        print(f"{r['label']:<26}{r['ttft']:>10.3f}{r['total']:>11.3f}{r['chars']:>8}")


def main() -> None:
    """Load the API key, benchmark all models and print the table."""
    # Load .env from the repo root (two levels up from this file).
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY not set (create repo-root .env).")

    client = OpenRouterClient(api_key, title="Wheatley-Benchmark")

    results = [benchmark_model(client, spec) for spec in BENCHMARK_MODELS]
    print()
    print_table(results)


if __name__ == "__main__":
    main()
