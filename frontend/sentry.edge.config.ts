// sentry.edge.config.ts — Sentry edge runtime initialization for Next.js
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN || process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.ENVIRONMENT || process.env.NEXT_PUBLIC_ENVIRONMENT || "development",
  tracesSampleRate: 0.02,
  debug: false,
});
