# Examination console. Multi-stage so the runtime image carries no source tree, no dev
# dependencies and no node_modules beyond what Next traced — that is what
# `output: "standalone"` in next.config.mjs is for.
#
# The tracing root is pinned in the config, not inferred: on the authoring machine Next
# walked out of the project into a stray package.json in the user's home directory and
# produced .next/standalone/Desktop/micro1/frontend/server.js. A Dockerfile written against
# that layout builds on one machine and fails everywhere else.

FROM node:22-alpine AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
# `npm ci` from the lockfile, so the image is built from pinned bytes rather than from
# whatever the registry resolves today.
RUN npm ci --no-audit --no-fund

FROM node:22-alpine AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY frontend ./
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000 \
    # The API origin stays server-side: the browser never learns it and cannot bypass Caddy
    # by calling the API directly.
    DOCX_BACKEND_URL=http://api:8010

# Next's postinstall telemetry switch runs nothing at container start.
USER node

COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
# `public/` is NOT inlined into standalone output — Next only traces code-referenced
# assets. Without this copy, robots.txt, llms.txt, the icons and og-image.png 404 in the
# container while working perfectly under `next dev`, which is how the SEO layer looked done
# and was not.
COPY --from=build --chown=node:node /app/public ./public

EXPOSE 3000

HEALTHCHECK --interval=20s --timeout=4s --start-period=15s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3000/').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"]

CMD ["node", "server.js"]
