"""A scripted stand-in for Gemini, so the tests need no API key or network."""

from __future__ import annotations

import hashlib
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from procurement_agent.tracing import Span  # noqa: E402


def fake_embedding(text: str, dims: int = 256) -> list[float]:
    """Character-trigram hashing: similar wording gives similar vectors."""
    vector = [0.0] * dims
    for i in range(len(text) - 2):
        bucket = int(hashlib.md5(text[i:i + 3].encode()).hexdigest(), 16) % dims
        vector[bucket] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


class FakeLLM:
    model = "fake-model"

    def __init__(self, responses: dict | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[tuple[str, str]] = []

    def _reply(self, node: str, prompt: str, tracer):
        self.calls.append((node, prompt))
        if tracer is not None:
            tracer.add(Span(node=node, latency_s=0.01, model=self.model, tokens_in=100,
                            tokens_out=20, cost_usd=0.00001))
        reply = self.responses[node]
        return reply(prompt) if callable(reply) else reply

    def generate_json(self, node, system, prompt, schema, tracer=None):
        return self._reply(node, prompt, tracer)

    def generate_text(self, node, system, prompt, tracer=None):
        return self._reply(node, prompt, tracer)

    def choose_tools(self, node, system, prompt, declarations, tracer=None):
        return self._reply(node, prompt, tracer)

    def embed(self, texts, task, tracer=None, node="embed"):
        return [fake_embedding(t) for t in texts]


@pytest.fixture
def fake_llm():
    return FakeLLM
