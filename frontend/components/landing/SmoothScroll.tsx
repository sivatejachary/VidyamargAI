"use client";

import React, { useEffect, useRef } from "react";
import gsap from "gsap";

export default function SmoothScroll({ children }: { children: React.ReactNode }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    let lenisInstance: any;

    // Load GSAP ScrollTrigger dynamically to avoid SSR errors
    const initScroll = async () => {
      const { default: Lenis } = await import("lenis");
      const { ScrollTrigger } = await import("gsap/ScrollTrigger");
      
      gsap.registerPlugin(ScrollTrigger);

      lenisInstance = new Lenis({
        duration: 1.2,
        easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
        smoothWheel: true,
      });

      // Synchronize ScrollTrigger with Lenis
      lenisInstance.on("scroll", ScrollTrigger.update);

      // Add custom ticker handler
      const tickHandler = (time: number) => {
        lenisInstance.raf(time * 1000);
      };

      gsap.ticker.add(tickHandler);
      gsap.ticker.lagSmoothing(0);

      // Save tick handler on instance for cleanup
      lenisInstance._tickHandler = tickHandler;
    };

    initScroll();

    return () => {
      if (lenisInstance) {
        if (lenisInstance._tickHandler) {
          gsap.ticker.remove(lenisInstance._tickHandler);
        }
        lenisInstance.destroy();
      }
    };
  }, []);

  return <div ref={containerRef} className="w-full">{children}</div>;
}
