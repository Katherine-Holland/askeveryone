// next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow Gitpod preview origin to access /_next/* in dev
  allowedDevOrigins: [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    // Your Gitpod preview origin (match what you see in the warning)
    "https://https://3000--019b7f77-37c4-737a-96d1-5ce84b3396f8.eu-central-1-01.gitpod.dev/",
  ],
};

export default nextConfig;
