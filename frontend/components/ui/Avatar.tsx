"use client";

import * as React from "react";

export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  name: string;
  size?: "sm" | "md" | "lg";
}

export function Avatar({ className = "", name, size = "md", ...props }: AvatarProps) {
  const initial = name ? name[0].toUpperCase() : "?";
  
  const sizes = {
    sm: "w-8 h-8 text-xs font-bold",
    md: "w-12 h-12 text-base font-extrabold",
    lg: "w-24 h-24 text-3xl font-black"
  };

  return (
    <div
      className={`rounded-full overflow-hidden border border-border bg-primary/10 text-primary flex items-center justify-center select-none shrink-0 ${sizes[size]} ${className}`}
      {...props}
    >
      {initial}
    </div>
  );
}
