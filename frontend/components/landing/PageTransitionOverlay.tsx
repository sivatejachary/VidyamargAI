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

  const startTransition = (url: string) => {
    router.push(url);
  };

  return (
    <TransitionContext.Provider value={{ isTransitioning: false, startTransition }}>
      {children}
    </TransitionContext.Provider>
  );
};
