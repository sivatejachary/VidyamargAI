"use client";

import * as React from "react";

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  error?: boolean;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className = "", error, children, ...props }, ref) => {
    return (
      <select
        ref={ref}
        className={`flex w-full bg-background border rounded-xl px-4 py-3 text-sm text-foreground
          focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1
          transition-all disabled:cursor-not-allowed disabled:opacity-50
          min-h-44 cursor-pointer
          ${
            error
              ? "border-destructive focus:ring-destructive"
              : "border-border focus:border-primary"
          } ${className}`}
        aria-invalid={error ? "true" : undefined}
        {...props}
      >
        {children}
      </select>
    );
  }
);
Select.displayName = "Select";
