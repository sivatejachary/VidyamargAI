"use client";

import * as React from "react";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
  errorId?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className = "", error, errorId, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={`flex w-full bg-background border rounded-xl px-4 py-3 text-sm text-foreground
          focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1
          transition-all placeholder:text-muted-foreground
          disabled:cursor-not-allowed disabled:opacity-50
          min-h-80 resize-y
          ${
            error
              ? "border-destructive focus:ring-destructive"
              : "border-border focus:border-primary"
          } ${className}`}
        aria-invalid={error ? "true" : undefined}
        aria-describedby={errorId}
        {...props}
      />
    );
  }
);
Textarea.displayName = "Textarea";
