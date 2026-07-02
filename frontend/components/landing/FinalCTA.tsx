"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";
import { usePageTransition } from "./PageTransitionOverlay";

export default function FinalCTA() {
  const { startTransition } = usePageTransition();
  
  // Magnetic coordinates for Get Started button
  const [getStartedCoords, setGetStartedCoords] = useState({ x: 0, y: 0 });
  const handleGetStartedMouseMove = (e: React.MouseEvent<HTMLButtonElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - (rect.left + rect.width / 2);
    const y = e.clientY - (rect.top + rect.height / 2);
    setGetStartedCoords({ x: x * 0.3, y: y * 0.3 }); // Dampen movement
  };
  const handleGetStartedMouseLeave = () => {
    setGetStartedCoords({ x: 0, y: 0 });
  };

  // Magnetic coordinates for Login button
  const [loginCoords, setLoginCoords] = useState({ x: 0, y: 0 });
  const handleLoginMouseMove = (e: React.MouseEvent<HTMLButtonElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - (rect.left + rect.width / 2);
    const y = e.clientY - (rect.top + rect.height / 2);
    setLoginCoords({ x: x * 0.3, y: y * 0.3 }); // Dampen movement
  };
  const handleLoginMouseLeave = () => {
    setLoginCoords({ x: 0, y: 0 });
  };

  return (
    <section className="py-32 relative overflow-hidden z-10 select-none">
      
      {/* Background Animated Gradient Mesh / Auroras */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-purple-950/10 to-slate-950 -z-10" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-[500px] bg-gradient-to-br from-purple-900/10 via-indigo-900/10 to-blue-900/10 rounded-full blur-[140px] pointer-events-none -z-10" />

      {/* Floating particles background sweep (Layer 3 & 4) */}
      <div className="absolute inset-0 z-0 pointer-events-none opacity-30">
        <div className="absolute top-10 left-10 w-2 h-2 bg-purple-500 rounded-full animate-ping" />
        <div className="absolute bottom-20 right-20 w-3 h-3 bg-blue-500 rounded-full animate-ping" />
        <div className="absolute top-1/3 right-1/4 w-1 h-1 bg-white rounded-full animate-pulse" />
      </div>

      <div className="max-w-4xl mx-auto px-6 text-center relative z-10 flex flex-col items-center">
        
        {/* Glowing sparkles icon */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          className="mb-8 w-12 h-12 rounded-2xl bg-gradient-to-br from-purple-600 to-blue-500 flex items-center justify-center border border-white/10 shadow-[0_0_20px_rgba(168,85,247,0.3)] animate-float-1"
        >
          <Sparkles className="w-5 h-5 text-white" />
        </motion.div>

        {/* Headline */}
        <motion.h2
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-4xl md:text-6xl font-heading font-black tracking-tight leading-tight text-white mb-6"
        >
          Your Future <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-violet-300 to-blue-400">Starts Today</span>
        </motion.h2>

        {/* Subhead */}
        <motion.p
          initial={{ opacity: 0, y: 15 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="text-slate-400 font-sans text-base md:text-lg max-w-xl mb-12 leading-relaxed"
        >
          Join thousands of professionals using VidyaMarg AI to discover better opportunities, close skill gaps, and accelerate their careers.
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.3 }}
          className="flex flex-col sm:flex-row gap-4 justify-center items-center w-full sm:w-auto"
        >
          {/* Magnetic Get Started Button */}
          <motion.button
            onMouseMove={handleGetStartedMouseMove}
            onMouseLeave={handleGetStartedMouseLeave}
            animate={{ x: getStartedCoords.x, y: getStartedCoords.y }}
            onClick={() => startTransition("/signup")}
            className="group w-full sm:w-auto inline-flex items-center justify-center gap-2 text-sm font-heading font-bold text-white bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 py-4 px-10 rounded-xl shadow-[0_0_30px_rgba(147,51,234,0.3)] hover:shadow-[0_0_35px_rgba(147,51,234,0.5)] transition-all duration-200 select-none btn-magnetic clickable"
            style={{ transitionProperty: "box-shadow, background-color" }}
          >
            Get Started
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1 duration-200" />
          </motion.button>

          {/* Magnetic Login Button */}
          <motion.button
            onMouseMove={handleLoginMouseMove}
            onMouseLeave={handleLoginMouseLeave}
            animate={{ x: loginCoords.x, y: loginCoords.y }}
            onClick={() => startTransition("/login")}
            className="w-full sm:w-auto inline-flex items-center justify-center text-sm font-heading font-bold text-slate-300 hover:text-white py-4 px-10 rounded-xl border border-slate-800 hover:border-purple-500/30 hover:bg-purple-500/5 transition-all duration-200 select-none btn-magnetic clickable"
            style={{ transitionProperty: "border-color, background-color" }}
          >
            Login
          </motion.button>
        </motion.div>

      </div>
    </section>
  );
}
