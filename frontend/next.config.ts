import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      // Enable Banking sends the OAuth code to the redirect URL registered
      // in the control panel (/connect/callback). We transparently forward it
      // to the actual callback handler at /banking/callback, preserving all
      // query params (including ?code=xxx).
      {
        source: "/connect/callback",
        destination: "/banking/callback",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
