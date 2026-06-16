"use client";

import * as React from "react";

export interface TooltipProps {
  content: string;
  children: React.ReactNode;
  className?: string;
}

export const Tooltip = React.forwardRef<HTMLDivElement, TooltipProps>(
  ({ content, children, className = "" }, ref) => {
    const id = React.useId();
    return (
      <div
        ref={ref}
        className={`relative group inline-block ${className}`}
        aria-describedby={id}
      >
        {children}
        <div
          id={id}
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 rounded-lg bg-card text-card-foreground text-10 font-bold border border-border shadow-md opacity-0 pointer-events-none group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity duration-200 z-50 whitespace-nowrap"
        >
          {content}
        </div>
      </div>
    );
  }
);
Tooltip.displayName = "Tooltip";

