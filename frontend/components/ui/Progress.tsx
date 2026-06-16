"use client";

import * as React from "react";

export interface ProgressProps {
  value: number; // 0 to 100
  className?: string;
  label?: string; // accessible label e.g. "Upload progress"
}

export function ProgressBar({ value, className = "", label }: ProgressProps) {
  const clampedValue = Math.min(Math.max(value, 0), 100);
  return (
    <div
      className={`w-full bg-muted border border-border rounded-full h-2.5 overflow-hidden ${className}`}
      role="progressbar"
      aria-valuenow={clampedValue}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label ?? "Progress"}
    >
      <div
        className="bg-primary h-full transition-all duration-300 ease-out"
        style={{ width: `${clampedValue}%` }}
      />
    </div>
  );
}

export interface ProgressRingProps {
  value: number;
  size?: number;
  strokeWidth?: number;
  className?: string;
  statusText?: string;
  label?: string;
}

export function ProgressRing({
  value,
  size = 80,
  strokeWidth = 6,
  className = "",
  statusText,
  label,
}: ProgressRingProps) {
  const clampedValue = Math.min(Math.max(value, 0), 100);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (clampedValue / 100) * circumference;

  const sizeClasses: Record<number, string> = {
    72: "w-72-px h-72-px",
    80: "w-80-px h-80-px",
    96: "w-96-px h-96-px",
  };
  const sizeClass = sizeClasses[size] || "w-80-px h-80-px";

  return (
    <div
      className={`flex flex-col items-center justify-center text-center ${className}`}
      role="progressbar"
      aria-valuenow={clampedValue}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label ?? statusText ?? "Progress"}
    >
      <div
        className={`relative flex items-center justify-center shrink-0 ${sizeClass}`}
        aria-hidden="true"
      >
        <svg width={size} height={size} className="transform -rotate-90">
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-muted"
          />
          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="text-success transition-all duration-700 ease-out"
          />
        </svg>
        <div className="absolute text-base font-black text-foreground">
          {clampedValue}%
        </div>
      </div>
      {statusText && (
        <span className="text-10 font-black text-success mt-2 block uppercase tracking-wider">
          {statusText}
        </span>
      )}
    </div>
  );
}
