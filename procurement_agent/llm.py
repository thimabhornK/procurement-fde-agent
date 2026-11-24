"""The only module that talks to Gemini.

Agents call four methods: generate_json, generate_text, choose_tools and
embed. Tests replace this class with a scripted fake, so nothing else in the
package imports the SDK.
"""

from __future__ import annotations

import json
import re
import time

from procurement_agent.config import Settings, load_settings
from procurement_agent.tracing import Span, Tracer, estimate_cost

KEY_PATTERN = re.compile(r"AIza[0-9A-Za-z_\-]{20,}")
RETRYABLE = ("429", "resource_exhausted", "503", "unavailable", "timeout", "timed out")


def describe_error(exc: Exception) -> str:
    text = KEY_PATTERN.sub("[key removed]", " ".join(str(exc).split()))
    return f"{type(exc).__name__}: {text[:300]}"


class Gemini:
    def __init__(self, settings: Settings | None = None, retries: int = 3,
                 retry_wait_s: float = 20.0) -> None:
        from google import genai
        from google.genai import types

        self.settings = settings or load_settings()
        if not self.settings.configured:
            raise RuntimeError(
                "No Gemini credentials. Set GEMINI_API_KEY, or GOOGLE_CLOUD_PROJECT "
                "for Vertex AI."
            )
        http = types.HttpOptions(timeout=int(self.settings.timeout_s * 1000))
        if self.settings.use_vertex:
            self.client = genai.Client(vertexai=True, project=self.settings.project,
                                       location=self.settings.location, http_options=http)
        else:
            self.client = genai.Client(api_key=self.settings.api_key, http_options=http)
        self.model = self.settings.model
        self.retries = retries
        self.retry_wait_s = retry_wait_s

    # -- internals ---------------------------------------------------------

    def _config(self, system: str | None, **extra):
        from google.genai import types

        kwargs = {"system_instruction": system, "temperature": 0.0, **extra}
        if self.settings.thinking_budget is not None:
            kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_budget=self.settings.thinking_budget
            )
        return types.GenerateContentConfig(**kwargs)

    def _call(self, fn):
        for attempt in range(self.retries):
            try:
                return fn()
            except Exception as exc:
                text = f"{type(exc).__name__} {exc}".lower()
                if attempt == self.retries - 1 or not any(k in text for k in RETRYABLE):
                    raise
                time.sleep(self.retry_wait_s * (attempt + 1))
        raise AssertionError("unreachable")

    def _generate(self, node: str, prompt: str, config, tracer: Tracer | None):
        start = time.perf_counter()
        try:
            response = self._call(lambda: self.client.models.generate_content(
                model=self.model, contents=prompt, config=config))
        except Exception as exc:
            if tracer is not None:
                tracer.add(Span(node=node, model=self.model, error=describe_error(exc),
                                latency_s=round(time.perf_counter() - start, 4)))
            raise
        latency = time.perf_counter() - start
        usage = response.usage_metadata
        tokens_in = getattr(usage, "prompt_token_count", 0) or 0
        thinking = getattr(usage, "thoughts_token_count", 0) or 0
        tokens_out = (getattr(usage, "candidates_token_count", 0) or 0) + thinking
        if tracer is not None:
            tracer.add(Span(
                node=node, latency_s=round(latency, 4), model=self.model,
                tokens_in=tokens_in, tokens_out=tokens_out, thinking_tokens=thinking,
                cost_usd=estimate_cost(tokens_in, tokens_out, self.settings.price_in_per_m,
                                       self.settings.price_out_per_m),
            ))
        return response

    # -- what agents use ---------------------------------------------------

    def generate_json(self, node: str, system: str, prompt: str, schema: dict,
                      tracer: Tracer | None = None) -> dict:
        config = self._config(system, response_mime_type="application/json",
                              response_schema=schema)
        response = self._generate(node, prompt, config, tracer)
        return json.loads(response.text)

    def generate_text(self, node: str, system: str, prompt: str,
                      tracer: Tracer | None = None) -> str:
        response = self._generate(node, prompt, self._config(system), tracer)
        return response.text or ""

    def choose_tools(self, node: str, system: str, prompt: str, declarations: list[dict],
                     tracer: Tracer | None = None) -> list[tuple[str, dict]]:
        """Let the model pick tools by native function calling. Nothing is executed here."""
        from google.genai import types

        tools = [types.Tool(function_declarations=[
            types.FunctionDeclaration(**d) for d in declarations
        ])]
        config = self._config(
            system, tools=tools,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        response = self._generate(node, prompt, config, tracer)
        return [(call.name, dict(call.args or {})) for call in (response.function_calls or [])]

    def embed(self, texts: list[str], task: str, tracer: Tracer | None = None,
              node: str = "embed") -> list[list[float]]:
        from google.genai import types

        config = types.EmbedContentConfig(task_type=task)

        def batch(items: list[str]) -> list[list[float]]:
            result = self._call(lambda: self.client.models.embed_content(
                model=self.settings.embedding_model, contents=items, config=config))
            return [list(e.values) for e in result.embeddings]

        start = time.perf_counter()
        try:
            vectors = batch(texts)
        except Exception:
            # Some endpoints (gemini-embedding-001 on Vertex AI) take one text per request.
            if len(texts) == 1:
                raise
            vectors = [batch([text])[0] for text in texts]
        if tracer is not None:
            tracer.add(Span(node=node, latency_s=round(time.perf_counter() - start, 4)))
        return vectors
