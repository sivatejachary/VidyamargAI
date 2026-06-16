"use client";

import * as React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverEffect?: boolean;
}

export function Card({ className = "", hoverEffect = false, children, ...props }: CardProps) {
  return (
    <div
      className={`bg-card text-card-foreground border border-border rounded-3xl p-6 shadow-xs ${
        hoverEffect ? "transition-all duration-200 hover:border-muted-foreground/30 hover:shadow-md" : ""
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
