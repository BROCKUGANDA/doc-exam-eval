"""DOC-EXAM — documentary credit examination benchmark.

Import-light on purpose: nothing in this package may depend on the FastAPI or
Next.js layers, so the benchmark runs standalone from a clean environment.
"""

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent

__all__ = ["PACKAGE_ROOT", "REPO_ROOT"]
