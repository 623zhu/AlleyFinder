import type { NextConfig } from "next";

const API = process.env.ALLEYFINDER_API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
