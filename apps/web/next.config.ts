import type { NextConfig } from "next";

/**
 * Labelled fake-backend mode for local Lighthouse runs. Off by default; when
 * enabled, /api/* is proxied to scripts/fake-backend.mjs, which serves the
 * generated contract fixtures. No live API is contacted.
 */
const fakeBackend = process.env.NEXT_FAKE_BACKEND === "1";

const nextConfig: NextConfig = {
  ...(fakeBackend
    ? {
        async rewrites() {
          return [
            {
              source: "/api/:path*",
              destination: "http://127.0.0.1:8787/api/:path*",
            },
          ];
        },
      }
    : {}),
};

export default nextConfig;
