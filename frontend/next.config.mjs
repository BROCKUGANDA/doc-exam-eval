/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
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
