"use client";

import * as React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "primary" | "secondary" | "success" | "warning" | "destructive" | "outline";
}

export function Badge({ className = "", variant = "secondary", children, ...props }: BadgeProps) {
  const baseStyle = "inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold border tracking-wide select-none";
  
  const variants = {
    primary: "bg-primary/10 border-primary/20 text-primary",
    secondary: "bg-secondary border-border text-secondary-foreground",
    success: "bg-success/15 border-success/30 text-success dark:text-success",
    warning: "bg-warning/15 border-warning/30 text-warning dark:text-warning",
    destructive: "bg-destructive/10 border-destructive/20 text-destructive dark:text-destructive-foreground",
    outline: "border-border text-muted-foreground bg-transparent"
  };

  return (
    <span className={`${baseStyle} ${variants[variant]} ${className}`} {...props}>
      {children}
    </span>
  );
}
