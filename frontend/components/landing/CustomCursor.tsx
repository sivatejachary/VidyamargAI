"use client";

import React, { useEffect, useState } from "react";

export default function CustomCursor() {
  const [position, setPosition] = useState({ x: -100, y: -100 });
  const [hidden, setHidden] = useState(true);
  const [hovered, setHovered] = useState(false);

  useEffect(() => {
    // Only run on desktop devices with a mouse
    const isMobile = window.matchMedia("(pointer: coarse)").matches;
    if (isMobile) return;

    const handleMouseMove = (e: MouseEvent) => {
      setPosition({ x: e.clientX, y: e.clientY });
      if (hidden) setHidden(false);
    };

    const handleMouseLeave = () => setHidden(true);
    const handleMouseEnter = () => setHidden(false);

    const handleMouseOver = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target) return;

      const isClickable = 
        target.tagName === "BUTTON" || 
        target.tagName === "A" || 
        target.closest("button") || 
        target.closest("a") || 
        target.classList.contains("clickable") || 
        target.closest(".clickable") ||
        target.getAttribute("role") === "button";

      setHovered(!!isClickable);
    };

    window.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseleave", handleMouseLeave);
    document.addEventListener("mouseenter", handleMouseEnter);
    window.addEventListener("mouseover", handleMouseOver);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseleave", handleMouseLeave);
      document.removeEventListener("mouseenter", handleMouseEnter);
      window.removeEventListener("mouseover", handleMouseOver);
    };
  }, [hidden]);

  if (hidden) return null;

  return (
    <>
      {/* Outer ring */}
      <div
        className="fixed top-0 left-0 w-8 h-8 rounded-full border border-purple-500/40 pointer-events-none z-50 -translate-x-1/2 -translate-y-1/2 mix-blend-screen transition-transform duration-300 ease-out"
        style={{
          transform: `translate3d(${position.x}px, ${position.y}px, 0) scale(${hovered ? 1.8 : 1})`,
          backgroundColor: hovered ? "rgba(168, 85, 247, 0.08)" : "rgba(168, 85, 247, 0)",
          boxShadow: hovered ? "0 0 20px rgba(168, 85, 247, 0.4)" : "none",
        }}
      />
      {/* Inner dot */}
      <div
        className="fixed top-0 left-0 w-2 h-2 bg-purple-500 rounded-full pointer-events-none z-50 -translate-x-1/2 -translate-y-1/2"
        style={{
          transform: `translate3d(${position.x}px, ${position.y}px, 0)`,
        }}
      />
    </>
  );
}
