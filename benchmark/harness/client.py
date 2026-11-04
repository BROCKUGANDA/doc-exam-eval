"""Minimal OpenAI-compatible chat client shared by every provider.

Deliberately small: one adapter covers Groq, Gemini, OpenRouter and Ollama because all four
serve `/chat/completions`. Fewer dependencies is a reproducibility feature, not a shortcut.

`complete` returns everything the results table needs to be honest — the exact model id the
provider echoed back, token counts, latency, and the settings actually sent — because a
results row that cannot be traced to a request is not evidence.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from benchmark.harness.providers import Provider


class ProviderError(Exception):
    def __init__(self, message: str, status: int | None = None, retry_after: float | None = None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


@dataclass
class Completion:
    model: str
    text: str
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_s: float
    settings: dict[str, Any]
    raw_id: str = ""

    def to_dict(self) -> dict:
        return {
            "model_requested": self.raw_id or self.model,
            "model_echoed": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "latency_s": round(self.latency_s, 3),
            "settings": self.settings,
        }


def complete(
    p: Provider,
    model: str,
    prompt: str,
    *,
    temperature: float = 0.0,
    max_output_tokens: int = 1500,
    system: str | None = None,
    timeout: float = 120.0,
    extra: dict[str, Any] | None = None,
) -> Completion:
    if not p.configured:
        raise ProviderError(f"provider {p.name} has no key/base url configured")

    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_output_tokens,
        "stream": False,
    }
    if extra:
        payload.update(extra)

    started = time.perf_counter()
    with httpx.Client(timeout=timeout) as client:
        response = client.post(p.url("chat/completions"), headers=p.headers(), json=payload)
    latency = time.perf_counter() - started

    if response.status_code >= 400:
        retry_after = None
        header = response.headers.get("retry-after")
        if header:
            try:
                retry_after = float(header)
            except ValueError:
                retry_after = None
        detail = response.text[:280].replace("\n", " ")
        raise ProviderError(
            f"{p.name}/{model}: HTTP {response.status_code} {detail}",
            status=response.status_code,
            retry_after=retry_after,
        )

    body = response.json()
    choices = body.get("choices") or []
    if not choices:
        raise ProviderError(f"{p.name}/{model}: response contained no choices")
    message = choices[0].get("message") or {}

    # Some providers put the answer somewhere other than `content`. Groq's gpt-oss returns
    # HTTP 200 with an empty `content` and the text in `reasoning`; reading only `content`
    # grades a perfectly good completion as unparseable, which would have shown up as a
    # 0% pass rate and been reported as a model limitation. The empty guard below is what
    # makes a silent miss impossible.
    text = ""
    content_field = "content"
    for field in ("content", "reasoning", "reasoning_content"):
        candidate = message.get(field)
        if isinstance(candidate, str) and candidate.strip():
            text = candidate
            content_field = field
            break

    if not text.strip():
        raise ProviderError(
            f"{p.name}/{model}: HTTP 200 but no usable text in content/reasoning. "
            "Refusing to hand an empty completion to the grader: it would score 0 and be "
            "recorded as a model failure rather than a transport problem.",
            status=response.status_code,
        )

    usage = body.get("usage") or {}
    return Completion(
        model=str(body.get("model") or model),
        text=text,
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        latency_s=latency,
        settings={
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "extra": extra or {},
            "content_field": content_field,
        },
        raw_id=model,
    )
