import type { NextConfig } from "next";

const apiOrigin = process.env.MEDSCRIBE_API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  turbopack: {
    root: process.cwd(),
  },
  async rewrites() {
    return [
      {
        source: "/consultations",
        destination: `${apiOrigin}/consultations`,
      },
      {
        source: "/consultations/:path*",
        destination: `${apiOrigin}/consultations/:path*`,
      },
      {
        source: "/health",
        destination: `${apiOrigin}/health`,
      },
    ];
  },
};

export default nextConfig;
