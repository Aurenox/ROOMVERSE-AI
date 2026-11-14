import type { NextConfig } from "next";

const config: NextConfig = {
  distDir: process.env.ROOMVERSE_E2E === "1" ? ".next-e2e" : ".next",
  poweredByHeader: false,
  skipTrailingSlashRedirect: true,
  async rewrites() {
    const origin = process.env.DJANGO_ORIGIN || "http://127.0.0.1:8000";
    return [
      { source: "/api", destination: `${origin}/api/` },
      { source: "/api/:path+", destination: `${origin}/api/:path+/` },
    ];
  },
};
export default config;
