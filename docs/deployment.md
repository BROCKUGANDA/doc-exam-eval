# Edge deployment (optional)

Nothing in this directory is required to reproduce a benchmark result. `python
run_eval.py --validate` runs with no proxy, no tunnel, no container and no API key, and that
is the path a judge is asked to follow. This layer exists only so the Phase C platform can be
shown from a public URL during the video and review.

## The constraint that shapes the design

The submission rules require that the video link — and by extension any judge-facing URL —
opens **without requesting access**. Zero Trust Access is the opposite of that. So the edge
splits by trust level instead of protecting everything:

| Host | Mutating? | Cloudflare Access | Who uses it |
|---|---|---|---|
| `DEMO_HOSTNAME` | No — Caddy refuses `POST/PUT/PATCH/DELETE` on `/api/*` with 403 `READ_ONLY_HOST` | **Must not be enabled** | judges, finalists, the video recording |
| `STUDIO_HOSTNAME` | Yes — Task Studio, run triggering, review-queue decisions | Required | the author only |

`scripts/check_edge.py` enforces this split rather than documenting it, and
`tests/test_edge_config.py` mutation-proves the enforcement by removing each boundary and
asserting the gate goes red.

## What each piece does

**Caddy** (`infra/caddy/Caddyfile`) terminates TLS, sets HSTS/CSP/frame-deny/referrer
headers, compresses with zstd+gzip, health-checks both upstreams so a dead service produces a
clear 502 instead of a blank page during a recording, and enforces the read-only boundary at
the edge rather than trusting the application to remember which routes mutate.

**Cloudflare Tunnel** (`infra/cloudflared/config.yml`) replaces inbound ports with one
outbound connection from `cloudflared` to Cloudflare's edge. Because traffic arrives through
Cloudflare, the origin inherits managed WAF rules, DDoS protection, rate limiting, bot
management and CDN caching of the Next.js static bundle — without any port being exposed. The
`tunnel` service publishes no ports on purpose: if a `ports:` entry appears there, the tunnel
has become decoration.

The trailing `http_status:404` ingress is required by cloudflared; without it, an unlisted
hostname fails at tunnel startup instead of returning 404.

## Bringing it up

```bash
cp .env.example .env                 # set DEMO_HOSTNAME, STUDIO_HOSTNAME, CLOUDFLARE_TUNNEL_TOKEN
docker compose --profile edge up -d caddy
docker compose --profile public up -d tunnel
python scripts/check_edge.py         # must pass before anything is exposed
```

Create the tunnel once, on a machine with a Cloudflare account:

```bash
cloudflared tunnel create doc-exam-edge
cloudflared tunnel route dns doc-exam-edge "$DEMO_HOSTNAME"
cloudflared tunnel route dns doc-exam-edge "$STUDIO_HOSTNAME"
```

Then copy the token into `.env` as `CLOUDFLARE_TUNNEL_TOKEN`. The managed-token form is used
deliberately: it needs no `credentials.json` on disk, so there is no key file that could be
committed or swept into the submission ZIP.

## Cloudflare dashboard settings that are *not* in this repo

Config-as-code only covers the tunnel ingress. Set these in the dashboard:

- **WAF:** enable the managed ruleset; add a rate-limiting rule on `/api/*` for the studio
  host so a runaway run loop cannot hammer the providers.
- **Access (studio host only):** an Access application for `STUDIO_HOSTNAME` with your own
  email as the only policy. Do not attach a policy to `DEMO_HOSTNAME`.
- **Caching:** respect origin headers; the results endpoints must not be cached long enough
  for a reviewer to see a stale score after a rerun.
- **TLS:** Full (strict) once Caddy serves its own certificate.

## Creds and the ZIP

`.env`, `credentials*.json`, `*.cert` and `video/` renders are gitignored. `check_edge.py`
scans the compose file, the tunnel config and the Caddyfile for any secret-shaped key
(`*TOKEN`, `*KEY`, `*SECRET`, `*PASSWORD`) carrying a literal value, and fails on a hit —
because a committed credential in the submission archive is a disqualification, not a cleanup
task.

## Current verification status

Neither Caddy nor the tunnel has been run yet: Caddy is not installed on the authoring
machine, Docker Desktop's daemon is not running, the Phase C services it proxies do not exist,
and GitHub Actions cannot currently obtain a runner on this account to verify the container.
The configuration is therefore *checked statically* by `check_edge.py` and *mutation-proved*
by `tests/test_edge_config.py`, which is honest about what that does and does not establish.
