import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  allowedDevOrigins: ["localhost", "127.0.0.1", "192.168.1.7"],
  env: {
    // Hardcode Railway backend URL so Vercel picks it up without manual dashboard setup
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "https://vidyamargai-production.up.railway.app/api/v1",
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || "wss://vidyamargai-production.up.railway.app/ws",
  },
  images: {
    formats: ["image/avif", "image/webp"],
    remotePatterns: [
      {
        // MinIO / local object storage
        protocol: "http",
        hostname: "localhost",
        port: "9000",
        pathname: "/**",
      },
      {
        // Railway MinIO service
        protocol: "https",
        hostname: "*.railway.app",
        pathname: "/**",
      },
      {
        // Any HTTPS host (e.g. course thumbnail CDN, Cloudinary, etc.)
        protocol: "https",
        hostname: "**",
      },
    ],
    minimumCacheTTL: 86400,  // 24h browser cache for optimized images
  },
  async headers() {
    return [
      {
        // Long-lived cache for static assets
        source: "/_next/static/:path*",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
    ];
  },
};

// Enable bundle analyzer if ANALYZE env is true
const bundleAnalyzed = process.env.ANALYZE === "true"
  ? require("@next/bundle-analyzer")({ enabled: true })(nextConfig)
  : nextConfig;

// Sentry Next.js plugin — wraps config to upload source maps and inject SDK auto-wiring
// https://docs.sentry.io/platforms/javascript/guides/nextjs/
let config: NextConfig = bundleAnalyzed;
try {
  const { withSentryConfig } = require("@sentry/nextjs");
  config = withSentryConfig(bundleAnalyzed, {
    // Org and project are picked up from SENTRY_ORG / SENTRY_PROJECT env vars
    silent: true,                // Suppress build-time noise
    disableClientWebpackPlugin: !process.env.SENTRY_DSN, // Skip upload if no DSN
    disableServerWebpackPlugin: !process.env.SENTRY_DSN,
    widenClientFileUpload: true, // Upload additional client files
    transpileClientSDK: true,
    hideSourceMaps: true,        // Do not ship source maps to browser
    dryRun: !process.env.SENTRY_DSN,
  });
} catch {
  // @sentry/nextjs not installed — that's fine, skip wrapping
}

export default config;



