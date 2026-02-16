import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // Use NEXT_PUBLIC_API_URL for production, or localhost for development
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
