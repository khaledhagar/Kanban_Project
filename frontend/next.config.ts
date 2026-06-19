import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Build to a static bundle (frontend/out) served by FastAPI; no Node server in prod.
  output: "export",
};

export default nextConfig;
