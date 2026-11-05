"""Edge-configuration gate tests.

The gate is only worth having if it can fail, so each test breaks one boundary and runs the
checker against the broken copy. The copy is in a temp tree: the first version mutated the
repository's own files and restored them in a fixture teardown, and one interrupted run left
`(hardened_headers_unused)` sitting in the committed Caddyfile. Tests that write to the thing
they are supposed to protect are not tests, they are accidents waiting for a Ctrl-C.
"""

from __future__ import annotations

import pytest

from scripts.check_edge import REPO, check

CONFIG_FILES = (
    "infra/caddy/Caddyfile",
    "infra/cloudflared/config.yml",
    "docker-compose.yml",
    ".env.example",
)

CADDY = "infra/caddy/Caddyfile"
TUNNEL = "infra/cloudflared/config.yml"
COMPOSE = "docker-compose.yml"

READ_ONLY_SNIPPET = """(read_only_api) {
	handle @public_write {
		header Content-Type "application/json"
		respond `{"error":"READ_ONLY_HOST","message":"This host serves evaluation evidence for review. Mutating operations are available on the studio host."}` 403
	}
}"""

DEMO_BOUNDARY = """	@public_write {
		method POST PUT PATCH DELETE
		path /api/*
	}
	import read_only_api"""

LOCAL_BOUNDARY = """	# Same boundary as the public host, so a laptop demo shows the real policy instead of a
	# more permissive one that only exists locally.
	@public_write {
		method POST PUT PATCH DELETE
		path /api/*
	}
	import read_only_api"""


@pytest.fixture
def tree(tmp_path):
    """The committed edge config, copied. Nothing below this line writes to the repository."""
    for rel in CONFIG_FILES:
        destination = tmp_path / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text((REPO / rel).read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    return tmp_path


def _break(root, rel, old, new):
    path = root / rel
    original = path.read_text(encoding="utf-8")
    assert old in original, f"mutation target absent from {path.name}: the fixture drifted"
    path.write_text(original.replace(old, new, 1), encoding="utf-8", newline="\n")


def test_edge_config_is_clean_as_committed():
    problems = check()
    # A gate that returns None is indistinguishable from a gate that passes. This assert
    # exists because exactly that happened: an edit moved check()'s return into the wrong
    # function, and every "OK" printed afterwards was vacuous.
    assert isinstance(problems, list), "check() must return a list of problems"
    assert problems == [], problems


def test_copy_of_the_config_is_also_clean(tree):
    """The tree the mutations run against starts green, or every mutation 'detects' nothing."""
    assert check(root=tree) == []


def test_demo_host_is_read_only_at_the_edge():
    """The rule that the judge link opens without requesting access is enforced here, not
    assumed in a document."""
    caddy = (REPO / CADDY).read_text(encoding="utf-8")
    assert "@public_write" in caddy
    assert "method POST PUT PATCH DELETE" in caddy
    assert "READ_ONLY_HOST" in caddy
    assert "403" in caddy


def test_demo_and_studio_are_separate_hosts():
    tunnel = (REPO / TUNNEL).read_text(encoding="utf-8")
    assert "${DEMO_HOSTNAME}" in tunnel and "${STUDIO_HOSTNAME}" in tunnel
    assert "http_status:404" in tunnel


@pytest.mark.parametrize(
    "rel,old,new,expected",
    [
        (CADDY, DEMO_BOUNDARY, "\t# boundary removed\n", "read-only"),
        # The failure this gate was written for: `respond` at site level is sequenced *after*
        # `handle` by Caddy, so the deny is silently unreachable and POSTs reach FastAPI.
        (CADDY, READ_ONLY_SNIPPET,
         '(read_only_api) {\n\trespond @public_write `{"error":"READ_ONLY_HOST"}` 403\n}',
         "handle @public_write"),
        (CADDY, LOCAL_BOUNDARY, "\t# local listener proxies without a write rule\n", "read-only"),
        (CADDY, "(hardened_headers) {", "(hardened_headers_unused) {", "import hardened_headers"),
        (CADDY, "{$DEMO_HOSTNAME:localhost:20081}", "{$DEMO_HOSTNAME}", "no default"),
        (CADDY, "\timport hardened_headers\n\t# The judge-facing boundary", "\t# The judge-facing boundary", "headers"),
        (TUNNEL, "    service: http://caddy:20080", "    service: http://caddy:20080\n    access: true", "Access"),
        (TUNNEL, "  - service: http_status:404", "", "catch-all"),
        (TUNNEL, "hostname: ${STUDIO_HOSTNAME}", "hostname: ${DEMO_HOSTNAME}", "distinct"),
        (COMPOSE, "TUNNEL_TOKEN: ${CLOUDFLARE_TUNNEL_TOKEN:-}",
         "TUNNEL_TOKEN: anactualtunneltokenvalue123456", "literal value"),
        (COMPOSE, 'profiles: ["public"]', "", "profile"),
        # Compose writing `DEMO_HOSTNAME: ${DEMO_HOSTNAME:-}` injects an empty value, which
        # beats Caddy's `:default` and collapses the site key to nothing.
        (COMPOSE, "      - DEMO_HOSTNAME\n", "      DEMO_HOSTNAME: ${DEMO_HOSTNAME:-}\n", "no default"),
    ],
    ids=[
        "read-only-boundary-removed",
        "deny-not-in-a-handle-block",
        "local-listener-left-unprotected",
        "snippet-renamed-away-from-import",
        "hostname-without-default",
        "security-headers-dropped",
        "access-configured",
        "catch-all-removed",
        "hosts-collapsed",
        "token-pasted-into-compose",
        "tunnel-profile-removed",
        "compose-injects-empty-hostname",
    ],
)
def test_gate_detects_each_mistake(tree, rel, old, new, expected):
    _break(tree, rel, old, new)
    problems = check(root=tree)
    assert problems, f"gate accepted the {expected} mutation; it is not a gate"
    assert any(expected.lower() in p.lower() for p in problems), (
        f"gate failed but for the wrong reason: {problems}"
    )


@pytest.fixture(scope="session", autouse=True)
def repository_untouched():
    """The invariant the old teardown was supposed to provide and did not.

    Snapshot the real config files when this module starts and fail the run if any of them
    differs at the end, whichever test wrote it and whether or not the write was undone.
    """
    before = {rel: (REPO / rel).read_text(encoding="utf-8") for rel in CONFIG_FILES}
    yield
    for rel, text in before.items():
        after = (REPO / rel).read_text(encoding="utf-8")
        if after != text:
            first_diff = next(i for i, (a, b) in enumerate(zip(text, after)) if a != b)
            raise AssertionError(
                f"{rel} was written by this test run (first difference at offset {first_diff}). "
                "Break a copy under tmp_path instead."
            )
