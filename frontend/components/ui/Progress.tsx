"use client";

import * as React from "react";

export interface ProgressProps {
  value: number; // 0 to 100
  className?: string;
}

export function ProgressBar({ value, className = "" }: ProgressProps) {
  const clampedValue = Math.min(Math.max(value, 0), 100);
  return (
    <div className={`w-full bg-muted border border-border rounded-full h-2.5 overflow-hidden ${className}`}>
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
}

export function ProgressRing({ value, size = 80, strokeWidth = 6, className = "", statusText }: ProgressRingProps) {
  const clampedValue = Math.min(Math.max(value, 0), 100);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (clampedValue / 100) * circumference;

  return (
    <div className={`flex flex-col items-center justify-center text-center ${className}`}>
      <div className="relative flex items-center justify-center shrink-0" style={{ width: size, height: size }}>
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
        <div className="absolute text-base font-black text-foreground">{clampedValue}%</div>
      </div>
      {statusText && (
        <span className="text-[10px] font-black text-success mt-2 block uppercase tracking-wider">
          {statusText}
        </span>
      )}
    </div>
  );
}
