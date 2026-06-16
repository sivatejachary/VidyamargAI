"use client";

import * as React from "react";
import { AlertCircle, AlertTriangle, CheckCircle2 } from "lucide-react";

export interface AlertProps {
  variant?: "success" | "error" | "warning";
  children: React.ReactNode;
  className?: string;
}

export function Alert({ variant = "success", children, className = "" }: AlertProps) {
  const baseStyle = "p-4 rounded-2xl border text-xs font-semibold flex items-start gap-2.5 animate-fadeIn";
  
  const variants = {
    success: "bg-success/5 border-success/20 text-success dark:text-success",
    error: "bg-destructive/5 border-destructive/20 text-destructive dark:text-destructive-foreground",
    warning: "bg-warning/5 border-warning/20 text-warning dark:text-warning"
  };

  const icons = {
    success: <CheckCircle2 size={16} className="text-success shrink-0 mt-0.5" />,
    error: <AlertCircle size={16} className="text-destructive shrink-0 mt-0.5" />,
    warning: <AlertTriangle size={16} className="text-warning shrink-0 mt-0.5" />
  };

  return (
    <div className={`${baseStyle} ${variants[variant]} ${className}`}>
      {icons[variant]}
      <div className="flex-1 min-w-0 leading-relaxed">{children}</div>
    </div>
  );
}
