"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";

const TransitionContext = createContext<{
  isTransitioning: boolean;
  startTransition: (url: string) => void;
} | null>(null);

export const usePageTransition = () => {
  const context = useContext(TransitionContext);
  if (!context) throw new Error("usePageTransition must be used within a PageTransitionProvider");
  return context;
};

export const PageTransitionProvider = ({ children }: { children: React.ReactNode }) => {
  const router = useRouter();
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [pendingUrl, setPendingUrl] = useState("");

  const startTransition = (url: string) => {
    // If the target is the current page, skip the transition
    if (typeof window !== "undefined" && window.location.pathname === url) return;
    setPendingUrl(url);
    setIsTransitioning(true);
  };

  useEffect(() => {
    if (isTransitioning && pendingUrl) {
      const timer = setTimeout(() => {
        router.push(pendingUrl);
        // Wait a bit, then remove the overlay curtain
        const exitTimer = setTimeout(() => {
          setIsTransitioning(false);
        }, 500);
        return () => clearTimeout(exitTimer);
      }, 650); // Matches the slide-up animation duration
      return () => clearTimeout(timer);
    }
  }, [isTransitioning, pendingUrl, router]);

  return (
    <TransitionContext.Provider value={{ isTransitioning, startTransition }}>
      {children}
      <AnimatePresence mode="wait">
        {isTransitioning && (
          <motion.div
            initial={{ y: "100%" }}
            animate={{ y: "0%" }}
            exit={{ y: "-100%" }}
            transition={{ duration: 0.65, ease: [0.16, 1, 0.3, 1] }}
            className="fixed inset-0 bg-slate-950 z-[9999] flex flex-col items-center justify-center pointer-events-auto"
            role="dialog"
            aria-modal="true"
            aria-label="Loading page transition"
          >
            <div className="flex flex-col items-center gap-5">
              <div className="w-10 h-10 rounded-full border-2 border-purple-500 border-t-transparent animate-spin" />
              <div className="text-purple-400 font-medium tracking-wide font-heading text-lg">
                VidyaMarg AI
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </TransitionContext.Provider>
  );
};
