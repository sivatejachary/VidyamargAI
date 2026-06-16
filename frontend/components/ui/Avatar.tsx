"use client";

import * as React from "react";

export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  src?: string;
  alt?: string;
  fallback?: string;
  size?: "xs" | "sm" | "md" | "lg" | "xl";
}

export function Avatar({
  src,
  alt = "",
  fallback,
  size = "md",
  className = "",
  ...props
}: AvatarProps) {
  const [imgError, setImgError] = React.useState(false);

  const sizes = {
    xs: "w-6 h-6 text-[9px]",
    sm: "w-8 h-8 text-xs",
    md: "w-10 h-10 text-sm",
    lg: "w-12 h-12 text-base",
    xl: "w-16 h-16 text-lg",
  };

  const initials = fallback
    ? fallback.slice(0, 2).toUpperCase()
    : alt
    ? alt
        .split(" ")
        .map((w) => w[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "?";

  return (
    <div
      className={`relative inline-flex items-center justify-center rounded-full overflow-hidden bg-muted border border-border shrink-0 ${sizes[size]} ${className}`}
      aria-label={alt || fallback || "Avatar"}
      {...props}
    >
      {src && !imgError ? (
        <img
          src={src}
          alt={alt}
          className="w-full h-full object-cover"
          onError={() => setImgError(true)}
        />
      ) : (
        <span className="font-bold text-muted-foreground select-none" aria-hidden="true">
          {initials}
        </span>
      )}
    </div>
  );
}
Avatar.displayName = "Avatar";
