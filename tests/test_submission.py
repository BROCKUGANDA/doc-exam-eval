"""The submission packer must be capable of refusing.

`scripts/make_submission.py` is the last gate before a ZIP goes to a third party, so its
deny-list and its secret patterns are tested in both directions: it must reject a planted key
and it must not reject the files that are supposed to ship. A gate with only the first
property is noise the author disables; a gate with only the second is a stamp.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("make_submission", REPO / "scripts" / "make_submission.py")
packager = importlib.util.module_from_spec(_spec)
sys.modules["make_submission"] = packager
_spec.loader.exec_module(packager)


def _name_problems(rel: str) -> list[str]:
    return packager.scan(rel, b"harmless content")


def test_env_example_ships_and_every_other_env_does_not():
    """The template proves the real file is absent; the real file disqualifies the entry."""
    assert _name_problems(".env.example") == [], "the documented template must be allowed"
    assert _name_problems("backend/.env.example") == []
    for denied in (".env", ".env.local", ".env.production", ".env.vps"):
        assert _name_problems(denied), f"{denied} must be refused by name"


def test_excluded_directories_are_refused_wherever_they_sit():
    for rel in ("node_modules/left-pad/index.js", "frontend/node_modules/next/package.json",
                ".venv/pyvenv.cfg", ".git/config", "video/walkthrough.mp4"):
        assert _name_problems(rel), f"{rel} should not be packable"
    assert _name_problems("frontend/app/page.tsx") == []


def test_a_planted_key_is_caught_in_a_python_file():
    planted = ('GROQ = "gsk_' + "Zm9vYmFyYmF6cXV1eGNvcmci" * 2 + '"\n').encode()
    problems = packager.scan("benchmark/harness/client.py", planted)
    assert problems, "a groq-shaped key in a scanned file must be reported"
    assert "groq key" in problems[0]


def test_a_private_key_block_is_caught_even_in_yaml():
    pem = b"password: dummy\n-----BEGIN RSA PRIVATE KEY-----\nMIIBOgIBAAJ"
    assert any("private key block" in p for p in packager.scan("infra/edge.yml", pem))


def test_documented_placeholders_are_not_reported_as_secrets():
    """A gate that fires on `<your-key-here>` gets switched off; a switched-off gate ships keys."""
    samples = [
        b"GROQ_API_KEY=<your-key-here>\n",
        b'CLOUDFLARE_TUNNEL_TOKEN="${TUNNEL_TOKEN}"\n',
        b"api_key = os.environ['DOCX_API_KEY']\n",
        b"# put a key shaped like sk-xxxxxxxx in .env, never here\n",
    ]
    for text in samples:
        assert packager.scan(".env.example", text) == [], text


def test_lockfiles_are_not_scanned_and_sources_are():
    assert not packager.is_scannable("frontend/package-lock.json")
    assert packager.is_scannable("run_eval.py")
    assert packager.is_scannable("README.md")
    assert packager.is_scannable("benchmark/results/runs/panel-02-probe-derived.jsonl")


def test_binary_payloads_are_left_alone():
    assert packager.scan("docs/diagram.png", b"\x89PNG\r\n\x1a\n\x00\x00") == []


def test_the_current_payload_actually_passes():
    """The claim in the README is that this tree is packable; this is what makes it a claim."""
    files = packager.collect()
    assert files, "collect() walked zero files — a scan over nothing proves nothing"
    assert any(f == "README.md" for f in files), "README.md must sit at the archive root"
    problems: list[str] = []
    total = 0
    for rel in files:
        data = (REPO / rel).read_bytes()
        total += len(data)
        if packager.is_scannable(rel):
            problems += packager.scan(rel, data)
    assert problems == [], f"this tree would not be packaged: {problems[:6]}"
    assert total < packager.MAX_BYTES, (
        f"{total/1024/1024:.1f} MB uncompressed — compressed size is not the only thing to watch"
    )


def test_archive_root_is_the_archive_not_a_folder_inside_it(tmp_path):
    """`README.md at the root of the ZIP` is checked by opening the ZIP and looking at level one."""
    import zipfile

    assert packager.build(tmp_path / "ignored-name.zip", check_only=False) == 0
    produced = list(tmp_path.glob("doc-exam-eval-*.zip"))
    assert len(produced) == 1, f"expected one archive, got {[p.name for p in produced]}"

    with zipfile.ZipFile(produced[0]) as zf:
        names = zf.namelist()
        assert "README.md" in names, f"README.md is nested, not at root: {names[:4]}"
        assert "MANIFEST.txt" in names
        assert not any(n.startswith("doc-exam-eval/") for n in names)
        assert not any("/node_modules/" in f"/{n}" or n.startswith("node_modules/") for n in names)
        assert zf.read("README.md").startswith(b"#"), "the root README must be the real document"
