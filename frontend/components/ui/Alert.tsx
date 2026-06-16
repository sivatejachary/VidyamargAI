"use client";

import * as React from "react";
import { AlertCircle, AlertTriangle, CheckCircle2, Info } from "lucide-react";

export interface AlertProps {
  variant?: "success" | "error" | "warning" | "info";
  children: React.ReactNode;
  className?: string;
  /** When true, uses role="alert" (assertive). Use for errors. Default: polite announcement. */
  assertive?: boolean;
}

export function Alert({
  variant = "success",
  children,
  className = "",
  assertive,
}: AlertProps) {
  const baseStyle =
    "p-4 rounded-2xl border text-xs font-semibold flex items-start gap-2.5 animate-fadeIn";

  const variants = {
    success:
      "bg-success/5 border-success/20 text-success dark:text-success",
    error:
      "bg-destructive/5 border-destructive/20 text-destructive dark:text-destructive-foreground",
    warning:
      "bg-warning/5 border-warning/20 text-warning dark:text-warning",
    info:
      "bg-primary/5 border-primary/20 text-primary dark:text-primary",
  };

  const icons = {
    success: (
      <CheckCircle2
        size={16}
        className="text-success shrink-0 mt-0.5"
        aria-hidden="true"
      />
    ),
    error: (
      <AlertCircle
        size={16}
        className="text-destructive shrink-0 mt-0.5"
        aria-hidden="true"
      />
    ),
    warning: (
      <AlertTriangle
        size={16}
        className="text-warning shrink-0 mt-0.5"
        aria-hidden="true"
      />
    ),
    info: (
      <Info
        size={16}
        className="text-primary shrink-0 mt-0.5"
        aria-hidden="true"
      />
    ),
  };

  // role="alert" auto-announces assertively; aria-live="polite" for non-urgent
  const liveProps =
    variant === "error" || assertive
      ? { role: "alert" as const }
      : { role: "status" as const, "aria-live": "polite" as const };

  return (
    <div className={`${baseStyle} ${variants[variant]} ${className}`} {...liveProps}>
      {icons[variant]}
      <div className="flex-1 min-w-0 leading-relaxed">{children}</div>
    </div>
  );
}
