import type { NextConfig } from "next";

const backend = process.env.FASTAPI_BASE_URL ?? "http://127.0.0.1:8000";
const url = new URL(backend);
if (
  !["http:", "https:"].includes(url.protocol) ||
  url.username ||
  url.password ||
  url.search ||
  url.hash
) {
  throw new Error(
    "FASTAPI_BASE_URL must be an HTTP(S) origin without credentials or query parameters.",
  );
}
const config: NextConfig = {
  poweredByHeader: false,
  agentRules: false, // Keep development runs from generating repository instruction files.
  // The default rewrite timeout (30s) can expire during cold embeddings + grounded generation.
  experimental: { proxyTimeout: 125_000 }, // Client aborts at 120s; retries keep the request ID.
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backend.replace(/\/$/, "")}/api/v1/:path*`,
      },
    ];
  },
};
export default config;
