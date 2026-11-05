#!/usr/bin/env python3
"""Edge-configuration gate.

This exists because the two most expensive mistakes available here are silent:

1. Putting Zero Trust in front of the judge-facing URL. The submission rules require that
   anyone with the link opens it *without requesting access*, so an Access policy or a
   mutating-method hole on the demo host is a completeness failure, not a security win.
2. Routing a hostname to the wrong origin, or exposing the studio host under the same name
   as the demo host, which would make the read-only boundary a fiction.

Every check here can fail, and each failure names the file to fix.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CADDYFILE = REPO / "infra" / "caddy" / "Caddyfile"
TUNNEL = REPO / "infra" / "cloudflared" / "config.yml"
COMPOSE = REPO / "docker-compose.yml"

MUTATING = r"\bPOST\s+PUT\s+PATCH\s+DELETE\b"
CREDENTIAL_PATTERNS = re.compile(
    r"(credentials-file\s*:\s*(?!\s*/etc/cloudflared/credentials\.json)[^\s]+)"
    r"|(eyJ[A-Za-z0-9_-]{20,}\.eyJ)"  # JWT-shaped token pasted inline
    r"|(CF_Authorization\s*=\s*[A-Za-z0-9._-]{20,})",
    re.IGNORECASE,
)


def _site_blocks(text: str) -> dict[str, str]:
    """Split a Caddyfile into {site_key: block_body}.

    Site keys are recognised only at column 0, which is what keeps nested directives
    (`header {`, `handle /api/* {`) from being mistaken for sites. A key may legitimately
    begin with `{`, because a placeholder hostname is written `{$DEMO_HOSTNAME}`, so the
    rule is "unindented line ending in a brace, with something before it".
    """
    lines = text.splitlines()
    blocks: dict[str, str] = {}
    for index, line in enumerate(lines):
        stripped = line.rstrip()
        if not stripped.endswith("{") or not stripped[:-1].strip():
            continue
        if line[:1].isspace():
            continue
        name = stripped[:-1].strip()
        if name == "{":
            continue
        depth = 0
        body: list[str] = []
        for j in range(index, len(lines)):
            depth += lines[j].count("{") - lines[j].count("}")
            if depth == 0:
                break
            body.append(lines[j])
        blocks[name] = "\n".join(body[1:])
    return blocks


def _snippets(text: str) -> dict[str, str]:
    """Named Caddy snippets, `(name) { ... }`, keyed by bare name.

    The parenthesis form sits at column 0 like a site key, so `_site_blocks` returns them too.
    Splitting them out is what makes the import check possible: an `import hardened_headers`
    with no definition is not a style problem, it is a container that crash-loops with
    "File to import not found" and an edge that never came up.
    """
    out: dict[str, str] = {}
    for key, body in _site_blocks(text).items():
        m = re.fullmatch(r"\((\w+)\)", key)
        if m:
            out[m.group(1)] = body
    return out


def _resolve(body: str, snippets: dict[str, str], depth: int = 0) -> str:
    """A site body with every `import <snippet>` expanded, so checks see what Caddy sees."""
    if depth > 4:
        return body
    expanded = body
    for name in re.findall(r"^\s*import\s+(\w+)\s*$", body, re.MULTILINE):
        if name in snippets:
            expanded += "\n" + _resolve(snippets[name], snippets, depth + 1)
        else:
            expanded += f"\n[UNDEFINED SNIPPET {name}]"
    return expanded


def check() -> list[str]:
    problems: list[str] = []

    for path in (CADDYFILE, TUNNEL, COMPOSE):
        if not path.is_file():
            problems.append(f"{path.relative_to(REPO)}: missing")
    if problems:
        return problems

    caddy = CADDYFILE.read_text(encoding="utf-8")
    tunnel = TUNNEL.read_text(encoding="utf-8")
    compose = COMPOSE.read_text(encoding="utf-8")

    blocks = {k: v for k, v in _site_blocks(caddy).items() if not re.fullmatch(r"\(\w+\)", k)}
    snippets = _snippets(caddy)

    # Every import must resolve. Caddy fails the whole file on one dangling name, so this is
    # the difference between "the edge is down" and "the edge was never configured".
    for name in set(re.findall(r"^\s*import\s+(\w+)\s*$", caddy, re.MULTILINE)):
        if name not in snippets:
            problems.append(
                f"Caddyfile: 'import {name}' has no ({name}) snippet — caddy refuses to adapt "
                "the config and the container restart-loops."
            )
    for name in snippets:
        if not re.search(rf"^\s*import\s+{name}\s*$", caddy, re.MULTILINE):
            problems.append(f"Caddyfile: snippet ({name}) is defined but never imported (dead config)")

    # A site key of the form {$VAR} with no default expands to nothing when the variable is
    # unset *or set-but-empty*, and Caddy then reads the block as global config appearing after
    # a server block. Both hostnames are optional in this deployment, so the defaults are the
    # only thing keeping `docker compose up` from failing outright.
    for key in blocks:
        for match in re.finditer(r"\{\$([A-Z_]+)(:[^}]*)?\}", key):
            if not match.group(2):
                problems.append(
                    f"Caddyfile site '{key}': ${{{match.group(1)}}} has no default. With the "
                    "variable unset or empty the site address becomes empty and Caddy rejects "
                    "the file as 'global configuration after a server block'."
                )

    demo_key = next((k for k in blocks if "DEMO_HOSTNAME" in k), None)
    studio_key = next((k for k in blocks if "STUDIO_HOSTNAME" in k), None)
    local_key = next((k for k in blocks if "CADDY_LOCAL_ADDR" in k), None)

    if demo_key is None:
        problems.append("Caddyfile: no site block bound to {$DEMO_HOSTNAME}")
    if studio_key is None:
        problems.append("Caddyfile: no site block bound to {$STUDIO_HOSTNAME}")

    # The read-only rule is enforced by policy, not by which hostname happens to be recognised.
    # Any site block that proxies the API and is not the studio host must refuse writes; the
    # local demo listener used to be an exception, which is how a boundary that "exists in the
    # Caddyfile" ended up not existing in behaviour.
    for key, body in blocks.items():
        if key == studio_key or "api_upstreams" not in body:
            continue
        label = key if key in (demo_key, local_key) else key
        if not re.search(MUTATING, body):
            problems.append(
                f"Caddyfile site '{label}': does not match POST/PUT/PATCH/DELETE on /api/*. "
                "Any host that reaches the API must be read-only except the studio host."
            )
        resolved = _resolve(body, snippets)
        # `respond @m ...` at site level is ordered *after* `handle`, so the proxy answers first
        # and the deny never fires. It has to be a handle block, matched before the others.
        if "handle @public_write" not in resolved:
            problems.append(
                f"Caddyfile site '{label}': the mutating-method deny is not a "
                "`handle @public_write` block. A bare `respond` is sequenced after `handle` by "
                "Caddy's directive order, so the request reaches FastAPI instead of being refused."
            )
        if "403" not in resolved:
            problems.append(f"Caddyfile site '{label}': the read-only refusal does not return 403")

    if demo_key:
        if "import hardened_headers" not in blocks[demo_key]:
            problems.append("Caddyfile DEMO host: security headers not applied")

    if studio_key:
        studio = blocks[studio_key]
        if "import hardened_headers" not in studio:
            problems.append("Caddyfile STUDIO host: security headers not applied")

    if demo_key == studio_key and demo_key is not None:
        problems.append("Caddyfile: demo and studio resolve to the same site block")

    # A single hostname for both trust levels would make the boundary meaningless.
    hosts = set(re.findall(r"hostname:\s*\$\{(\w+)\}", tunnel))
    if "DEMO_HOSTNAME" not in hosts or "STUDIO_HOSTNAME" not in hosts:
        problems.append(f"cloudflared config: expected two distinct hostnames, found {sorted(hosts)}")

    if "http_status:404" not in tunnel:
        problems.append("cloudflared config: no catch-all 404 ingress; unknown hostnames fail at startup")

    # Zero Trust must never gate the public evidence host.
    if re.search(r"access\s*:\s*true", tunnel, re.IGNORECASE):
        problems.append(
            "cloudflared config: 'access: true' present. Cloudflare Access is applied per "
            "hostname in the dashboard, not here; leaving it in this file risks it being "
            "copied onto the judge-facing hostname, which would violate the rule that the "
            "link opens without requesting access."
        )

    for path, text in ((CADDYFILE, caddy), (TUNNEL, tunnel), (COMPOSE, compose)):
        hit = CREDENTIAL_PATTERNS.search(text)
        if hit:
            problems.append(
                f"{path.relative_to(REPO)}: credential-shaped value found ({hit.group(0)[:32]}...). "
                "Tokens and credentials files stay out of the repository."
            )

    # Credentials must never be committed or zipped (submission rule 6). This checks any
    # secret-shaped key, not one specific name: cloudflared reads TUNNEL_TOKEN while the
    # repo's .env uses CLOUDFLARE_TUNNEL_TOKEN, and a check keyed to only one of those
    # names misses a token pasted into the other -- which is what this file exists to stop.
    secret_key = r"([A-Z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD)[A-Z0-9_]*)"
    for label, text in (("docker-compose.yml", compose), ("cloudflared config", tunnel), ("Caddyfile", caddy)):
        for m in re.finditer(rf"{secret_key}\s*[:=]\s*[\"']?([^\"'\s$][^\"'\s]*)", text):
            key, value = m.group(1), m.group(2)
            if value.startswith("${") or value.startswith("$"):
                continue  # environment indirection is the correct form
            if len(value) < 12:
                continue  # short non-secret values (ports, flags) are not findings
            problems.append(
                f"{label}: {key} appears to carry a literal value ({value[:12]}...). "
                "Reference the environment instead; a committed credential is a "
                "disqualification under the submission rules."
            )

    # `DEMO_HOSTNAME: ${DEMO_HOSTNAME:-}` in compose looks like the safe form and is not: it
    # puts an *empty* value in the container environment, and Caddy's `{$VAR:default}` only
    # substitutes when the variable is absent. The site address collapses to nothing and the
    # edge refuses to start. Pass-through (`- DEMO_HOSTNAME`) is the form that works.
    caddy_service = _compose_service_block(compose, "caddy") or ""
    for var in ("DEMO_HOSTNAME", "STUDIO_HOSTNAME", "CADDY_LOCAL_ADDR"):
        empty_default = r"^\s*" + var + r":\s*\$\{" + var + r":-\}\s*$"
        if re.search(empty_default, caddy_service, re.MULTILINE):
            problems.append(
                f"docker-compose.yml: {var} is injected as `${{{var}:-}}`, an empty value rather "
                f"than an absent one. Caddy then has no default address for ${{{var}}} and the "
                "site key becomes empty. List it as pass-through instead."
            )

    if "CLOUDFLARE_TUNNEL_TOKEN" not in (REPO / ".env.example").read_text(encoding="utf-8"):
        problems.append(".env.example: CLOUDFLARE_TUNNEL_TOKEN is not declared")

    # Nothing on the reproduction path may require the edge.
    if re.search(r"^\s*depends_on:.*caddy", compose, re.MULTILINE | re.IGNORECASE):
        problems.append("docker-compose.yml: the eval service must not depend on caddy")
    if "profiles" not in compose:
        problems.append("docker-compose.yml: edge services should sit behind profiles")

    # Each edge service individually must be profile-gated. Checking only that the word
    # "profiles" appears somewhere in the file would pass a compose where the tunnel has
    # been given a profile removed, which makes `docker compose up` demand a Cloudflare
    # account before the benchmark can run at all.
    for service in ("caddy", "tunnel"):
        block = _compose_service_block(compose, service)
        if block is None:
            problems.append(f"docker-compose.yml: service '{service}' is missing")
            continue
        if "profiles" not in block:
            problems.append(
                f"docker-compose.yml: service '{service}' has no profiles: entry, so it "
                "starts with the default `docker compose up` and makes reproduction depend "
                "on infrastructure a judge does not have."
            )

    return problems


def _compose_service_block(text: str, service: str) -> str | None:
    """Return the body of `services.<service>:` using indentation, or None if absent."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.rstrip() == f"  {service}:":
            start = i + 1
            break
    if start is None:
        return None
    body: list[str] = []
    for line in lines[start:]:
        if line.strip() and not line.startswith("    "):
            break
        body.append(line)
    return "\n".join(body)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check Caddy/Cloudflare edge configuration")
    ap.add_argument("--strict", action="store_true", help="non-zero exit on any problem")
    args = ap.parse_args(argv)

    problems = check()
    if problems:
        print(f"edge configuration problems ({len(problems)}):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print("edge config OK: demo host read-only, studio host separate, no Access on the "
          "judge path, no inline credentials, reproduction path independent of the edge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
