import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  allowedDevOrigins: ["localhost", "127.0.0.1", "192.168.1.7"],
  env: {
    // Hardcode Railway backend URL so Vercel picks it up without manual dashboard setup
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "https://vidyamargai-production.up.railway.app/api/v1",
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || "wss://vidyamargai-production.up.railway.app/ws",
  },
};

// Enable bundle analyzer if ANALYZE env is true
const config = process.env.ANALYZE === "true"
  ? require("@next/bundle-analyzer")({ enabled: true })(nextConfig)
  : nextConfig;

export default config;

