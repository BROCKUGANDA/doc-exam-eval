"""Edge-configuration gate tests.

The gate is only worth having if it can fail, so each test breaks one boundary in a copy,
runs the checker, and restores from memory. No `git checkout` is involved: an earlier
attempt at this used it against an uncommitted file and silently deleted the services being
tested, which is how the credential check went unverified for several rounds.
"""

from __future__ import annotations

import pytest

from scripts.check_edge import REPO, check

CADDY = REPO / "infra" / "caddy" / "Caddyfile"
TUNNEL = REPO / "infra" / "cloudflared" / "config.yml"
COMPOSE = REPO / "docker-compose.yml"

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


def _mutate(path, old, new):
    original = path.read_text(encoding="utf-8")
    assert old in original, f"mutation target absent from {path.name}: the fixture drifted"
    path.write_text(original.replace(old, new, 1), encoding="utf-8", newline="\n")
    return original


@pytest.fixture
def restore():
    saved: list[tuple] = []

    def _save(path, original):
        saved.append((path, original))

    yield _save
    for path, original in saved:
        path.write_text(original, encoding="utf-8", newline="\n")


def test_edge_config_is_clean_as_committed():
    problems = check()
    # A gate that returns None is indistinguishable from a gate that passes. This assert
    # exists because exactly that happened: an edit moved check()'s return into the wrong
    # function, and every "OK" printed afterwards was vacuous.
    assert isinstance(problems, list), "check() must return a list of problems"
    assert problems == []


def test_demo_host_is_read_only_at_the_edge():
    """The rule that the judge link opens without requesting access is enforced here, not
    assumed in a document."""
    caddy = CADDY.read_text(encoding="utf-8")
    assert "@public_write" in caddy
    assert "method POST PUT PATCH DELETE" in caddy
    assert "READ_ONLY_HOST" in caddy
    assert "403" in caddy


def test_demo_and_studio_are_separate_hosts():
    tunnel = TUNNEL.read_text(encoding="utf-8")
    assert "${DEMO_HOSTNAME}" in tunnel and "${STUDIO_HOSTNAME}" in tunnel
    assert "http_status:404" in tunnel


@pytest.mark.parametrize(
    "path,old,new,expected",
    [
        (CADDY, DEMO_BOUNDARY, "\t# boundary removed\n", "read-only"),
        # The failure this gate was written for: `respond` at site level is sequenced *after*
        # `handle` by Caddy, so the deny is silently unreachable and POSTs reach FastAPI.
        (CADDY, READ_ONLY_SNIPPET,
         "(read_only_api) {\n\trespond @public_write `{\"error\":\"READ_ONLY_HOST\"}` 403\n}",
         "handle @public_write"),
        (CADDY, LOCAL_BOUNDARY, "\t# local listener proxies without a write rule\n", "read-only"),
        (CADDY, "(hardened_headers) {", "(hardened_headers_unused) {", "import hardened_headers"),
        (CADDY, "{$DEMO_HOSTNAME:localhost:20081}", "{$DEMO_HOSTNAME}", "no default"),
        (CADDY, "\timport hardened_headers\n\t# The judge-facing boundary", "\t# The judge-facing boundary", "headers"),
        (TUNNEL, "    service: http://caddy:20080", "    service: http://caddy:20080\n    access: true", "Access"),
        (TUNNEL, "  - service: http_status:404", "", "catch-all"),
        (TUNNEL, "hostname: ${STUDIO_HOSTNAME}", "hostname: ${DEMO_HOSTNAME}", "distinct"),
        (
            COMPOSE,
            "TUNNEL_TOKEN: ${CLOUDFLARE_TUNNEL_TOKEN:-}",
            "TUNNEL_TOKEN: anactualtunneltokenvalue123456",
            "literal value",
        ),
        (COMPOSE, "profiles: [\"public\"]", "", "profile"),
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
def test_gate_detects_each_mistake(path, old, new, expected, restore):
    restore(path, _mutate(path, old, new))
    problems = check()
    assert problems, f"gate accepted the {expected} mutation; it is not a gate"
    assert any(expected.lower() in p.lower() for p in problems), (
        f"gate failed but for the wrong reason: {problems}"
    )
