"""Context-budget gate.

Ollama defaults num_ctx to 4096 and truncates silently, keeping the tail of the prompt.
An DOC-EXAM prompt is rulebook (~3.3k tokens) plus ten documents, so on a default setup the
model would lose the *rulebook and instruction* while keeping the last document. It would
then miss discrepancies it was never given rules for, and the grader would record a
reasoning failure that was really a truncation artifact — precisely the confound the
benchmark specification's two-track design forbids.

So a trial either has provably enough window, or it is recorded as SKIPPED_CONTEXT and
never scored.
"""

from __future__ import annotations

from dataclasses import dataclass

import tiktoken

# o200k_base is used as a documented proxy. It is not the tokenizer every model uses, so
# the fit test applies MARGIN rather than trusting the count exactly.
PROXY_ENCODING = "o200k_base"
MARGIN = 1.35
DEFAULT_OUTPUT_RESERVE = 2000

_ENCODING = tiktoken.get_encoding(PROXY_ENCODING)


class ContextTooSmall(Exception):
    """Raised when a model cannot be given the whole prompt. Never scored as a failure."""


@dataclass(frozen=True)
class Budget:
    prompt_tokens: int
    output_reserve: int
    window: int
    margin: float

    @property
    def required_window(self) -> int:
        return int((self.prompt_tokens + self.output_reserve) * self.margin)

    @property
    def fits(self) -> bool:
        return self.window >= self.required_window

    def to_dict(self) -> dict:
        return {
            "prompt_tokens_estimated_with": PROXY_ENCODING,
            "prompt_tokens": self.prompt_tokens,
            "output_reserve": self.output_reserve,
            "model_window": self.window,
            "required_window_with_margin": self.required_window,
            "fits": self.fits,
        }


def estimate_tokens(text: str) -> int:
    return len(_ENCODING.encode(text, disallowed_special=()))


def budget(prompt_text: str, window: int, output_reserve: int = DEFAULT_OUTPUT_RESERVE) -> Budget:
    return Budget(
        prompt_tokens=estimate_tokens(prompt_text),
        output_reserve=output_reserve,
        window=window,
        margin=MARGIN,
    )


def detect_truncation(b: Budget, reported_prompt_tokens: int | None) -> bool:
    """A provider that echoes fewer prompt tokens than we sent has truncated the input."""
    if reported_prompt_tokens is None:
        return False
    return reported_prompt_tokens < int(b.prompt_tokens * 0.95)


def require_fits(b: Budget, model: str) -> None:
    if not b.fits:
        raise ContextTooSmall(
            f"{model}: prompt needs ~{b.required_window} tokens of window (estimate "
            f"{b.prompt_tokens} + reserve {b.output_reserve} x {b.margin}) but the model "
            f"advertises {b.window}. Record SKIPPED_CONTEXT; do not score this trial."
        )
