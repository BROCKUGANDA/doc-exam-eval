"""Phase B harness tests.

These use an injected transport, so they verify journaling, resume, backoff, the context
gate and normalisation without spending provider quota. They do not prove any model result —
only the live run does that, and the README keeps those claims separate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmark.generator.build import build_case
from benchmark.generator.scenarios import SCENARIOS
from benchmark.harness.client import Completion, ProviderError
from benchmark.harness.journal import Journal, Trial, utc_now
from benchmark.harness.panel import MAX_OUTPUT_TOKENS, ModelSpec, Panel, from_probe
from benchmark.harness.report import aggregate, to_markdown
from benchmark.harness.runner import _with_backoff, normalize_output, run_panel
from benchmark.rulebook import rulebook

RB = rulebook()
CASES = {cid: (b.package, b.truth) for cid, b in ((k, build_case(v, RB)) for k, v in SCENARIOS.items())}
SCN = SCENARIOS


def _completion(text: str, *, prompt_tokens: int = 5200) -> Completion:
    return Completion(
        model="fake",
        text=text,
        prompt_tokens=prompt_tokens,
        completion_tokens=400,
        latency_s=0.5,
        settings={"content_field": "content", "temperature": 0.0, "max_output_tokens": MAX_OUTPUT_TOKENS, "extra": {}},
    )


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
def test_think_block_is_stripped_and_recorded():
    raw = "\n<think>\nReasoning here.\n</think>\nThe answer is {\"ok\": true}"
    out, notes = normalize_output(raw)
    assert "Reasoning here." not in out
    assert out.endswith('{"ok": true}')
    assert any("think" in n for n in notes)


def test_markdown_fence_is_stripped():
    out, notes = normalize_output('```json\n{"assessment": "CLEAR"}\n```')
    assert json.loads(out) == {"assessment": "CLEAR"}
    assert any("fence" in n for n in notes)


def test_plain_json_is_untouched():
    text = '{"assessment": "CLEAR"}'
    out, notes = normalize_output(text)
    assert out == text
    assert notes == []


# ---------------------------------------------------------------------------
# Backoff
# ---------------------------------------------------------------------------
def test_retryable_error_is_retried_then_succeeds():
    sleeps: list[float] = []
    calls = {"n": 0}

    def fn(attempt):
        calls["n"] += 1
        if attempt < 3:
            raise ProviderError("throttled", status=429)
        return _completion("ok")

    out, attempts = _with_backoff(fn, sleep=sleeps.append)
    assert attempts == 3 and calls["n"] == 3
    assert sleeps == [2.0, 4.0]


def test_retry_after_is_honoured():
    sleeps: list[float] = []

    def fn(attempt):
        if attempt == 1:
            raise ProviderError("slow down", status=429, retry_after=13.0)
        return _completion("ok")

    _with_backoff(fn, sleep=sleeps.append)
    assert sleeps == [13.0]


def test_payment_required_is_not_retried():
    """402 will not fix itself; retrying burns wall-clock and quota for nothing."""
    calls = {"n": 0}

    def fn(attempt):
        calls["n"] += 1
        raise ProviderError("no credits", status=402)

    with pytest.raises(ProviderError):
        _with_backoff(fn, sleep=lambda s: None)
    assert calls["n"] == 1


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------
def _trial(case: str, model: str, n: int, status: str = "ok") -> Trial:
    return Trial(
        panel_id="p1", case_id=case, model_id=model, provider="groq", trial=n,
        status=status, started_at=utc_now(), finished_at=utc_now(),
    )


def test_journal_roundtrip_and_completed_set(tmp_path: Path):
    j = Journal(tmp_path / "runs" / "p1.jsonl")
    j.append(_trial("DOC-001", "m", 1))
    j.append(_trial("DOC-001", "m", 2, status="provider_error"))
    assert j.completed() == {"DOC-001::m::1"}
    assert j.counts() == {"ok": 1, "provider_error": 1}


def test_resume_skips_completed_trials(tmp_path: Path):
    j = Journal(tmp_path / "p1.jsonl")
    j.append(_trial("DOC-001", "groq-model", 1))
    done = j.completed()
    assert "DOC-001::groq-model::1" in done


def test_torn_final_line_does_not_break_resume(tmp_path: Path):
    j = Journal(tmp_path / "p1.jsonl")
    j.append(_trial("DOC-002", "m", 1))
    with (tmp_path / "p1.jsonl").open("a", encoding="utf-8") as fh:
        fh.write('{"case_id": "DOC-002", "model_id"  # interrupted write\n')
    assert j.completed() == {"DOC-002::m::1"}
    assert j.counts() == {"ok": 1}


# ---------------------------------------------------------------------------
# Panel derivation
# ---------------------------------------------------------------------------
def test_panel_is_derived_from_probe_evidence(tmp_path: Path):
    probe = tmp_path / "probe.json"
    probe.write_text(
        json.dumps(
            [
                {"candidate": "groq:openai/gpt-oss-120b", "status": "ok"},
                {"candidate": "openrouter:anthropic/claude-haiku-4.5", "status": "error", "http": 402},
                {"candidate": "gemini:models/gemini-3.1-pro-preview", "status": "error", "http": 429},
            ]
        ),
        encoding="utf-8",
    )
    panel = from_probe(probe)
    assert [m.spec_id for m in panel.models] == ["groq:openai/gpt-oss-120b"]
    reasons = {e["candidate"]: e["reason"] for e in panel.excluded}
    assert "402" in reasons["openrouter:anthropic/claude-haiku-4.5"]
    assert "429" in reasons["gemini:models/gemini-3.1-pro-preview"]


# ---------------------------------------------------------------------------
# Runner behaviour
# ---------------------------------------------------------------------------
def _panel(models: list[ModelSpec], trials: int = 1) -> Panel:
    return Panel(panel_id="test", models=models, trials=trials)


def _good_report(case_id: str) -> str:
    """A reference-shaped report with no findings, for the clean task."""
    return json.dumps(
        {
            "case_id": case_id,
            "assessment": "CLEAR",
            "documents_reviewed": ["LC-001", "INV-001"],
            "discrepancies": [],
            "unresolved_questions": [],
            "summary": "Compliant.",
        }
    )


def test_run_panel_grades_normalised_text_not_raw(tmp_path: Path):
    """A correct answer wrapped in a think block must score, or the benchmark would report a
    model failure that is really a formatting artifact."""
    j = Journal(tmp_path / "p.jsonl")
    spec = ModelSpec(provider="groq", model_id="m", family="f", closed_weights=True, window=131_072)

    def fake_call(p, model, prompt, **kw):
        return _completion("<think>let me look</think>\n" + _good_report("DOC-001"))

    trials = run_panel({"DOC-001": CASES["DOC-001"]}, {"DOC-001": SCN["DOC-001"]}, RB, _panel([spec]), j,
                       call=fake_call, sleep=lambda s: None, resolve=lambda name: object())
    assert trials[0].status == "ok"
    assert trials[0].scorecard["passed"] is True
    assert "<think>" in trials[0].raw_output
    assert "<think>" not in trials[0].normalized_output


def test_provider_error_is_not_scored_as_zero(tmp_path: Path):
    j = Journal(tmp_path / "p.jsonl")
    spec = ModelSpec(provider="openrouter", model_id="claude", family="f", closed_weights=False, window=131_072)

    def fake_call(p, model, prompt, **kw):
        raise ProviderError("insufficient credits", status=402)

    trials = run_panel({"DOC-001": CASES["DOC-001"]}, {"DOC-001": SCN["DOC-001"]}, RB, _panel([spec]), j,
                       call=fake_call, sleep=lambda s: None, resolve=lambda name: object())
    assert trials[0].status == "provider_error"
    assert trials[0].scorecard is None
    result = aggregate(j, [spec.spec_id])
    model = result["models"][spec.spec_id]
    assert model["trials_scored"] == 0
    assert model["overall_mean_total"] is None
    assert any("did not score" in w for w in result["warnings"])


def test_context_gate_refuses_instead_of_truncating(tmp_path: Path):
    j = Journal(tmp_path / "p.jsonl")
    spec = ModelSpec(provider="groq", model_id="tiny", family="f", closed_weights=True, window=4096)
    calls = {"n": 0}

    def fake_call(p, model, prompt, **kw):
        calls["n"] += 1
        return _completion(_good_report("DOC-001"))

    trials = run_panel({"DOC-001": CASES["DOC-001"]}, {"DOC-001": SCN["DOC-001"]}, RB, _panel([spec]), j,
                       call=fake_call, sleep=lambda s: None, resolve=lambda name: object())
    assert calls["n"] == 0, "a prompt that may not fit must never be sent"
    assert trials[0].status == "skipped_context"
    assert "refusing" in trials[0].error


def test_truncation_is_flagged_from_reported_tokens(tmp_path: Path):
    j = Journal(tmp_path / "p.jsonl")
    spec = ModelSpec(provider="groq", model_id="m", family="f", closed_weights=True, window=131_072)

    def fake_call(p, model, prompt, **kw):
        return _completion(_good_report("DOC-001"), prompt_tokens=900)

    trials = run_panel({"DOC-001": CASES["DOC-001"]}, {"DOC-001": SCN["DOC-001"]}, RB, _panel([spec]), j,
                       call=fake_call, sleep=lambda s: None, resolve=lambda name: object())
    assert "possible_truncation" in trials[0].settings


def test_report_markdown_lists_excluded_models():
    spec = ModelSpec(provider="groq", model_id="m", family="f", closed_weights=True, window=131_072)
    panel = {"panel_id": "p", "trials_per_task": 3, "temperature": 0.0,
             "excluded_after_probing": [{"candidate": "openrouter:x", "reason": "HTTP 402 insufficient credits"}]}
    md = to_markdown({"models": {}, "warnings": []}, panel)
    assert "Excluded after probing" in md
    assert "HTTP 402" in md


# ---------------------------------------------------------------------------
# Levers that exist because panel 1 produced fake results. Each of these was a
# real bug: reasoning budget consuming the whole completion, a provider that is
# out of quota for the day being retried across 24 trials, and reasoning effort
# not being part of the recorded configuration.
# ---------------------------------------------------------------------------
def _spec(**kw):
    base = dict(provider="groq", model_id="m", family="f", closed_weights=True, window=131_072)
    base.update(kw)
    return ModelSpec(**base)


def _ok_call(tmp):
    from benchmark.generator.build import build_case as _bc
    built = _bc(SCENARIOS["DOC-001"], RB)
    from benchmark.validation.fixtures import reference_output
    text = json.dumps(reference_output(built.truth, built.package, RB))
    return _completion(text)


def test_truncated_completion_is_not_graded(tmp_path):
    """finish_reason == 'length' means we cut the model off. Grading that as 0 turns a
    transport limit into a reported capability failure, which is exactly what panel 1 did."""
    j = Journal(tmp_path / "p.jsonl")

    def fake_call(p, model, prompt, **kw):
        c = _completion('{"case_id": "DOC-001", "assessment": ')
        c.finish_reason = "length"
        c.reasoning_tokens = 7998
        return c

    trials = run_panel({"DOC-001": CASES["DOC-001"]}, {"DOC-001": SCN["DOC-001"]}, RB,
                       _panel([_spec()]), j, call=fake_call, sleep=lambda s: None,
                       resolve=lambda name: object())
    assert trials[0].status == "truncated_output"
    assert trials[0].scorecard is None
    assert "max_output_tokens" in trials[0].error


def test_reasoning_effort_is_sent_and_recorded(tmp_path):
    """A setting that changes whether a model can answer at all must be in the request and
    in the frozen trial record, not implicit in a provider default."""
    j = Journal(tmp_path / "p.jsonl")
    seen = {}

    def fake_call(p, model, prompt, **kw):
        seen["extra"] = kw.get("extra")
        return _ok_call(tmp_path)

    spec = _spec(extra={"reasoning_effort": "low"})
    run_panel({"DOC-001": CASES["DOC-001"]}, {"DOC-001": SCN["DOC-001"]}, RB, _panel([spec]), j,
              call=fake_call, sleep=lambda s: None, resolve=lambda name: object())
    assert seen["extra"] == {"reasoning_effort": "low"}
    rec = list(j.records())[0]
    assert rec["settings"]["extra_request_params"] == {"reasoning_effort": "low"}


def test_circuit_breaker_abandons_a_model_after_repeated_provider_errors(tmp_path):
    """Quota exhaustion is a daily property of an account. Retrying it 5 times across 24
    trials spends the project window to reproduce the same 429."""
    from benchmark.harness.runner import CIRCUIT_BREAKER

    j = Journal(tmp_path / "p.jsonl")
    calls = {"n": 0}

    def fake_call(p, model, prompt, **kw):
        calls["n"] += 1
        raise ProviderError("quota", status=429)

    trials = run_panel(CASES, SCN, RB, _panel([_spec()]), j, call=fake_call,
                       sleep=lambda s: None, resolve=lambda name: object())
    # Each trial retries internally (429 is retryable), so the breaker bounds the number of
    # trials suffered, not the number of HTTP calls. Both must stay small.
    assert len(trials) == CIRCUIT_BREAKER, f"expected {CIRCUIT_BREAKER} trials before abandoning, got {len(trials)}"
    assert calls["n"] <= CIRCUIT_BREAKER * 5, f"unbounded retries: {calls['n']} calls"
    assert all(t.status == "provider_error" for t in trials)
