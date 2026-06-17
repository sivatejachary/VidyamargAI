// sentry.server.config.ts — Sentry server-side initialization for Next.js
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.SENTRY_DSN || process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.ENVIRONMENT || process.env.NEXT_PUBLIC_ENVIRONMENT || "development",
  release: process.env.GIT_SHA || process.env.NEXT_PUBLIC_GIT_SHA || "local",

  // Server traces: lower sample rate to reduce overhead
  tracesSampleRate: 0.02,

  // Suppress noisy console output in development
  debug: false,

  beforeSend(event) {
    if (process.env.NODE_ENV === "development" && !process.env.SENTRY_DSN) {
      return null;
    }
    return event;
  },
});
