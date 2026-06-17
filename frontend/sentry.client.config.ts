// sentry.client.config.ts — Sentry browser-side initialization
// This file is loaded automatically by Next.js when @sentry/nextjs is installed.
import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_ENVIRONMENT || "development",
  release: process.env.NEXT_PUBLIC_GIT_SHA || "local",

  // Performance monitoring
  tracesSampleRate: 0.05,      // 5% of transactions
  profilesSampleRate: 0.02,    // 2% profiling (requires profiling addon)

  // Session replays (only on errors)
  replaysSessionSampleRate: 0.0,
  replaysOnErrorSampleRate: 1.0,

  integrations: [
    Sentry.replayIntegration({
      maskAllText: true,
      blockAllMedia: false,
    }),
    Sentry.browserTracingIntegration(),
  ],

  // Ignore common noise
  ignoreErrors: [
    "ResizeObserver loop limit exceeded",
    "Non-Error exception captured",
    "Network request failed",
    /^AbortError/,
    /^ChunkLoadError/,
  ],

  beforeSend(event) {
    // Drop events in development (unless SENTRY_DSN is explicitly set)
    if (
      process.env.NODE_ENV === "development" &&
      !process.env.NEXT_PUBLIC_SENTRY_DSN
    ) {
      return null;
    }
    return event;
  },
});
