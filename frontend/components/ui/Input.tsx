"use client";

import * as React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
  /** Accessible error message id — link via aria-describedby */
  errorId?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className = "", error, errorId, type = "text", ...props }, ref) => {
    return (
      <input
        type={type}
        className={`flex w-full bg-background border rounded-xl px-4 py-3 text-sm text-foreground
          focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1
          transition-all placeholder:text-muted-foreground
          disabled:cursor-not-allowed disabled:opacity-50
          min-h-[44px]
          ${
            error
              ? "border-destructive focus:ring-destructive"
              : "border-border focus:border-primary"
          } ${className}`}
        ref={ref}
        aria-invalid={error ? "true" : undefined}
        aria-describedby={errorId}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";
