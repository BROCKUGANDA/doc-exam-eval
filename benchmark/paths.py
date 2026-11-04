"""Filesystem layout for generated artifacts.

Everything generated is derived from seeds and can be rebuilt, so it is gitignored
and never shipped inside the submission ZIP unless explicitly materialised.
"""

from __future__ import annotations

from pathlib import Path

from benchmark import PACKAGE_ROOT, REPO_ROOT

RULEBOOK_DIR = PACKAGE_ROOT / "rulebook"
RULEBOOK_FILE = RULEBOOK_DIR / "rulebook.yaml"
TASKS_DIR = PACKAGE_ROOT / "tasks"
GENERATOR_DIR = PACKAGE_ROOT / "generator"
GRADERS_DIR = PACKAGE_ROOT / "graders"
VALIDATION_DIR = PACKAGE_ROOT / "validation"
HARNESS_DIR = PACKAGE_ROOT / "harness"

ARTIFACTS_DIR = PACKAGE_ROOT / "artifacts"
RESULTS_DIR = PACKAGE_ROOT / "results"
RUNS_DIR = RESULTS_DIR / "runs"
TRANSCRIPTS_DIR = RESULTS_DIR / "transcripts"
MODELS_LOCK = RESULTS_DIR / "models.lock.json"

ENV_FILE = REPO_ROOT / ".env"
ENV_EXAMPLE = REPO_ROOT / ".env.example"


def ensure_dirs() -> None:
    for d in (ARTIFACTS_DIR, RESULTS_DIR, RUNS_DIR, TRANSCRIPTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
