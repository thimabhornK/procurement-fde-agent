"""Settings read from environment variables.

Two ways to reach Gemini:
- Gemini API: set GEMINI_API_KEY (or GOOGLE_API_KEY).
- Vertex AI: set GOOGLE_CLOUD_PROJECT (and optionally GOOGLE_CLOUD_LOCATION),
  then run `gcloud auth application-default login`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"

# Paid-tier list prices in USD per million tokens (input, output). Thinking
# tokens are billed as output. Used only to estimate cost in traces; override
# with PROCUREMENT_AGENT_PRICE_IN_PER_M / PROCUREMENT_AGENT_PRICE_OUT_PER_M.
PRICES = {
    "gemini-3.5-flash": (1.50, 9.00),
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3-flash-preview": (0.50, 3.00),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
}


def _thinking_budget(model: str) -> int | None:
    raw = os.environ.get("PROCUREMENT_AGENT_THINKING_BUDGET")
    if raw is not None:
        return int(raw) if raw.strip() else None
    # Gemini 2.5 Flash thinks by default, which roughly triples latency on these
    # short extraction tasks. Turn it off unless asked for.
    return 0 if model.startswith("gemini-2.5-flash") else None


@dataclass(frozen=True)
class Settings:
    model: str
    embedding_model: str
    thinking_budget: int | None
    api_key: str | None
    project: str | None
    location: str
    price_in_per_m: float | None
    price_out_per_m: float | None
    timeout_s: float

    @property
    def use_vertex(self) -> bool:
        flag = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower()
        if flag in ("1", "true", "yes"):
            return True
        return not self.api_key and bool(self.project)

    @property
    def configured(self) -> bool:
        return bool(self.api_key or self.project)


def load_settings() -> Settings:
    model = os.environ.get("PROCUREMENT_AGENT_MODEL", DEFAULT_MODEL)
    listed = PRICES.get(model)
    price_in = os.environ.get("PROCUREMENT_AGENT_PRICE_IN_PER_M")
    price_out = os.environ.get("PROCUREMENT_AGENT_PRICE_OUT_PER_M")
    return Settings(
        model=model,
        embedding_model=os.environ.get(
            "PROCUREMENT_AGENT_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL
        ),
        thinking_budget=_thinking_budget(model),
        api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"),
        project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        price_in_per_m=float(price_in) if price_in else (listed[0] if listed else None),
        price_out_per_m=float(price_out) if price_out else (listed[1] if listed else None),
        timeout_s=float(os.environ.get("PROCUREMENT_AGENT_TIMEOUT_S", "60")),
    )
