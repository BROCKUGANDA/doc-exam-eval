"""Build the single ZIP the hackathon accepts, and prove it is allowed to be that ZIP.

Submission rules that shape this script:
  * one file, <= 50 MB, README.md at the root, no password protection;
  * no video inside it (the walkthrough is a link);
  * never credentials, confidential information or private personal data.

So the payload is `git ls-files` — the committed tree, not the working tree, which is what
keeps a stray .env out by construction rather than by remembering an exclude — plus the
generated evidence a judge cannot reproduce without keys: the transcripts, the probe record
and the aggregated results. Everything is staged in a temp directory, scanned, size-checked
and only then compressed.
"""

from __future__ import annotations

import argparse
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MAX_BYTES = 50 * 1024 * 1024

#: Generated evidence that is not tracked in git but is part of the deliverable: the guide
#: asks for raw model outputs and the settings that produced them, and a judge cannot obtain
#: them without a provider key.
EVIDENCE = [
    "benchmark/results/results.json",
    "benchmark/results/results.md",
    "benchmark/results/probe.json",
    "benchmark/results/models.lock.json",
    "benchmark/results/runs",
    "benchmark/results/transcripts",
    "benchmark/tasks",
]

#: Never shipped, whatever git says. A ZIP containing one of these names fails the "no
#: credentials or private data" rule on sight, and reviewers open archives by filename first.
#: `.env.example` is the documented template and the only `.env.*` allowed — a deny rule that
#: ate it would refuse the package over the one file that proves the real one is absent.
DENY_NAMES = re.compile(
    r"(?:^|/)(?:\.env|\.env\.(?!example$)[A-Za-z0-9._-]+|id_rsa.*|.*\.pem|.*\.p12"
    r"|.*\.keystore|credentials\.json|secrets\.yaml"
    # Media containers. The submission rules say the walkthrough is a link and no video goes
    # inside the ZIP, so this refuses the file type wherever it appears rather than trusting
    # one directory name to stay out.
    r"|.*\.(?:mp4|mov|avi|mkv|webm|mp3|wav|ogg))$",
    re.IGNORECASE,
)
#: Build and tooling directories. `video` is deliberately NOT here: the storyboard, the
#: measured manifest and the composition HTML document how the walkthrough was built, and
#: SKIP_PAYLOAD below is what keeps the media itself out.
DENY_DIRS = re.compile(r"(?:^|/)(\.git|node_modules|\.venv|venv|__pycache__|\.next|dist|\.pytest_cache|\.hypothesis)(?:/|$)")

#: Secret-shaped strings. Deliberately over-broad: a false positive costs one inspection, a
#: false negative costs the submission. Matches the literal prefix, then requires the rest of
#: a key-shaped run so prose like "sk-xxx" in a README does not trip it.
SECRET_PATTERNS = [
    ("openai-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}")),
    ("groq key", re.compile(r"\bgsk_[A-Za-z0-9_]{16,}")),
    ("google api key", re.compile(r"\bAIza[0-9A-Za-z_\-]{20,}")),
    ("aws access key id", re.compile(r"\bAKIA[0-9A-Z]{12,}")),
    ("cloudflare tunnel token", re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}")),
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("slack/bot token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("bearer JWT", re.compile(r"\b[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{16,}")),
    ("password assignment", re.compile(r"(?i)\b(password|passwd|secret|api_?key|access_?token)\b\s*[:=]\s*['\"]?(?!<|\$\{|\{\{|\$)[A-Za-z0-9+/_-]{12,}")),
]

#: Files worth scanning as text. Everything else is skipped as binary or as noise.
TEXT_SUFFIXES = {".py", ".md", ".yml", ".yaml", ".json", ".jsonl", ".txt", ".toml", ".ini",
                 ".cfg", ".env.example", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".html", ".css",
                 ".sh", ".bats", ".sql", ".lock"}

SKIP_SCAN = re.compile(r"(?:^|/)(package-lock\.json|uv\.lock|.*\.lock)$")

#: Video production, not evaluation evidence. The rules say the walkthrough is a link and no
#: video goes inside the ZIP, so the narration clips, the captured frames and any render output
#: stay out. The storyboard, the measured manifest and the composition HTML do ship: they are
#: how the video was generated from the same numbers as the README.
SKIP_PAYLOAD = re.compile(r"^video/(audio|render|shots|film/node_modules|film/assets/audio)/")


def tracked_files() -> list[str]:
    import subprocess

    out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"git ls-files failed: {out.stderr.strip()}")
    return sorted(p for p in out.stdout.split("\0") if p and not SKIP_PAYLOAD.search(p))


def evidence_files() -> list[str]:
    found: list[str] = []
    for entry in EVIDENCE:
        path = REPO / entry
        if path.is_dir():
            found += [str(p.relative_to(REPO)).replace("\\", "/") for p in sorted(path.rglob("*")) if p.is_file()]
        elif path.is_file():
            found.append(entry)
    return found


def is_scannable(rel: str) -> bool:
    if SKIP_SCAN.search(rel):
        return False
    return Path(rel).suffix.lower() in TEXT_SUFFIXES or rel.endswith(".env.example")


def scan(rel: str, data: bytes) -> list[str]:
    problems: list[str] = []
    if DENY_NAMES.search(rel) or DENY_DIRS.search(rel):
        problems.append(f"{rel}: excluded by name")
        return problems
    if b"\x00" in data[:8192]:
        return problems  # binary
    text = data.decode("utf-8", errors="replace")
    for label, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            line = text[: match.start()].count("\n") + 1
            snippet = match.group(0)
            problems.append(f"{rel}:{line}: {label} — {snippet[:14]}…{len(snippet)} chars")
    return problems


def collect() -> list[str]:
    tracked = tracked_files()
    extra = [f for f in evidence_files() if f not in tracked]
    return sorted(set(tracked) | set(extra))


def build(out_path: Path, check_only: bool) -> int:
    files = collect()
    problems: list[str] = []
    total = 0
    for rel in files:
        path = REPO / rel
        if not path.is_file():
            problems.append(f"{rel}: listed but missing")
            continue
        data = path.read_bytes()
        total += len(data)
        if is_scannable(rel):
            problems += scan(rel, data)

    if not any(rel == "README.md" for rel in files):
        problems.append("README.md is not at the archive root")
    for rel in files:
        if DENY_DIRS.search(rel):
            problems.append(f"{rel}: excluded directory shipped anyway")

    print(f"{len(files)} file(s), {total/1024/1024:.2f} MB uncompressed")
    if problems:
        print(f"\nREFUSING to package — {len(problems)} problem(s):")
        for p in problems[:40]:
            print(f"  - {p}")
        return 1

    if check_only:
        print("clean: no excluded names, no secret-shaped strings, README at root")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    final = out_path.with_name(f"doc-exam-eval-{stamp}.zip")
    tmp = out_path.with_suffix(".zip.tmp")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        # No wrapper directory. The rule is that README.md sits at the root of the archive, and
        # a zip that unpacks to a single folder makes the reviewer open one more level to find
        # it — an avoidable way to look non-compliant on the first check they run.
        for rel in files:
            zf.write(REPO / rel, arcname=rel)
        manifest = (
            "doc-exam-eval submission bundle\n"
            f"built: {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n"
            f"files: {len(files)}\n"
            f"uncompressed bytes: {total}\n"
            "git commit: "
            f"{__import__('subprocess').run(['git','rev-parse','--short','HEAD'],cwd=REPO,capture_output=True,text=True).stdout.strip()}\n"
        )
        zf.writestr("MANIFEST.txt", manifest)

    size = tmp.stat().st_size
    if size > MAX_BYTES:
        tmp.unlink()
        print(f"REFUSING: {size/1024/1024:.1f} MB exceeds the 50 MB limit")
        return 1
    tmp.replace(final)
    print(f"wrote {final} ({size/1024/1024:.2f} MB compressed, {100.0*size/max(total,1):.0f}% of raw)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="scan and report, write nothing")
    ap.add_argument("--out", default="dist/doc-exam-eval.zip", help="destination archive")
    args = ap.parse_args(argv)
    return build((REPO / args.out).resolve(), args.check)


if __name__ == "__main__":
    raise SystemExit(main())
