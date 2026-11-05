import path from "node:path";
import { fileURLToPath } from "node:url";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Self-contained server bundle for frontend/Dockerfile: the runner image copies
  // .next/standalone plus .next/static and does not need the source tree or a full
  // node_modules. Without this the image would have to ship the whole dependency graph.
  output: "standalone",
  // Pinned, and it was not optional. Next walks up from the project looking for a workspace
  // root and this machine has a stray package.json in the user's home directory, so the
  // "root" it chose was C:\\Users\\HP: standalone output came out as
  // .next/standalone/Desktop/micro1/frontend/server.js instead of .next/standalone/server.js,
  // and it had copied the home package.json into the image. Any Dockerfile written against
  // that layout would build on this machine and fail on a clean clone, which is the exact
  // failure the reproducibility criterion is about.
  outputFileTracingRoot: path.dirname(fileURLToPath(import.meta.url)),
  // The API origin is server-side only; nothing reaches the browser, so the read-only
  // boundary stays entirely in Caddy and FastAPI rather than depending on CORS.
  serverExternalPackages: [],
  experimental: {
    // Pages are rendered from the artifact API on every request. Caching a score would let
    // the dashboard disagree with a run that has since been regraded.
    ppr: false,
  },
};

export default nextConfig;
