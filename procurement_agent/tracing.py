"""Per-call tracing: latency, tokens (thinking included) and estimated cost.

Nodes of the graph can run in parallel threads, so records are appended under
a lock, and the wall-clock time of a run is kept separately from the sum of
the node latencies.
"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field


@dataclass
class Span:
    node: str
    latency_s: float
    model: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    thinking_tokens: int = 0
    cost_usd: float | None = None
    error: str | None = None

    @property
    def tokens_per_s(self) -> float | None:
        if not self.tokens_out or not self.latency_s:
            return None
        return self.tokens_out / self.latency_s


def estimate_cost(tokens_in: int, tokens_out: int,
                  price_in_per_m: float | None, price_out_per_m: float | None) -> float | None:
    if price_in_per_m is None or price_out_per_m is None:
        return None
    return round((tokens_in * price_in_per_m + tokens_out * price_out_per_m) / 1e6, 8)


@dataclass
class Tracer:
    spans: list[Span] = field(default_factory=list)
    wall_s: float | None = None

    def __post_init__(self) -> None:
        self._lock = threading.Lock()

    def add(self, span: Span) -> None:
        with self._lock:
            self.spans.append(span)

    @contextmanager
    def timed(self, node: str):
        """Time a step that does not call a model (retrieval, scoring in code)."""
        start = time.perf_counter()
        span = Span(node=node, latency_s=0.0)
        try:
            yield span
        finally:
            span.latency_s = round(time.perf_counter() - start, 4)
            self.add(span)

    @contextmanager
    def run(self):
        """Measure the wall-clock time of a whole run."""
        start = time.perf_counter()
        try:
            yield self
        finally:
            self.wall_s = round(time.perf_counter() - start, 4)

    def totals(self) -> dict:
        costs = [s.cost_usd for s in self.spans if s.cost_usd is not None]
        model_spans = [s for s in self.spans if s.model]
        return {
            "wall_s": self.wall_s,
            "sum_of_node_latency_s": round(sum(s.latency_s for s in self.spans), 4),
            "model_calls": len(model_spans),
            "tokens_in": sum(s.tokens_in for s in self.spans),
            "tokens_out": sum(s.tokens_out for s in self.spans),
            "thinking_tokens": sum(s.thinking_tokens for s in self.spans),
            "cost_usd": round(sum(costs), 8) if len(costs) == len(model_spans) else None,
        }

    def as_dict(self) -> dict:
        return {"spans": [asdict(s) for s in self.spans], "totals": self.totals()}

    def summary(self) -> str:
        lines = []
        for s in self.spans:
            cost = f"${s.cost_usd:.6f}" if s.cost_usd is not None else "-"
            tokens = f"in={s.tokens_in} out={s.tokens_out}" if s.model else ""
            lines.append(f"{s.node:<22} {s.latency_s:>7.2f}s  {tokens:<20} {cost}")
        t = self.totals()
        cost = f"${t['cost_usd']:.6f}" if t["cost_usd"] is not None else "-"
        lines.append(
            f"{'total (wall clock)':<22} {t['wall_s'] or 0:>7.2f}s  "
            f"{t['model_calls']} model calls, {t['tokens_in']} in / {t['tokens_out']} out  {cost}"
        )
        return "\n".join(lines)
