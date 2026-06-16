"use client";

import * as React from "react";
import { FolderOpen } from "lucide-react";

export interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ title, description, icon, action, className = "" }: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center rounded-3xl border border-dashed border-border bg-card/20 ${className}`}>
      <div className="p-3 rounded-full bg-muted text-muted-foreground mb-4 flex items-center justify-center">
        {icon || <FolderOpen size={24} />}
      </div>
      <h3 className="text-sm font-bold text-foreground mb-1">{title}</h3>
      <p className="text-xs text-muted-foreground max-w-sm mb-5 leading-relaxed">{description}</p>
      {action}
    </div>
  );
}
