"use client";

import * as React from "react";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Renders a circle (for avatars) instead of a rectangle */
  circle?: boolean;
  /** height override e.g. "h-4" */
  height?: string;
}

export function Skeleton({ className = "", circle = false, height, ...props }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-muted ${circle ? "rounded-full" : "rounded-xl"} ${height ?? "h-4"} ${className}`}
      aria-hidden="true"
      {...props}
    />
  );
}
Skeleton.displayName = "Skeleton";

/** Convenience: a flex column of skeleton lines */
export function SkeletonBlock({
  lines = 3,
  className = "",
}: {
  lines?: number;
  className?: string;
}) {
  return (
    <div className={`space-y-2 ${className}`} aria-hidden="true" aria-label="Loading…">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} height={i === 0 ? "h-5" : "h-3"} className={i === lines - 1 ? "w-3/4" : "w-full"} />
      ))}
    </div>
  );
}
