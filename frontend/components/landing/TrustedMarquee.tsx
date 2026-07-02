"use client";

import React from "react";
import { motion } from "framer-motion";

const companies = [
  { name: "Google", color: "hover:text-red-400" },
  { name: "Microsoft", color: "hover:text-blue-400" },
  { name: "Amazon", color: "hover:text-amber-400" },
  { name: "Apple", color: "hover:text-slate-200" },
  { name: "NVIDIA", color: "hover:text-green-400" },
  { name: "Adobe", color: "hover:text-red-500" },
  { name: "Oracle", color: "hover:text-red-600" },
  { name: "Infosys", color: "hover:text-blue-500" },
  { name: "TCS", color: "hover:text-teal-400" },
  { name: "Accenture", color: "hover:text-purple-400" },
];

export default function TrustedMarquee() {
  // Duplicate array to enable seamless looping scroll
  const duplicatedCompanies = [...companies, ...companies, ...companies, ...companies];

  return (
    <section className="py-16 relative overflow-hidden bg-slate-950/20 z-10 border-y border-slate-900/60 select-none">
      
      {/* Background Soft Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-1/2 bg-purple-500/2 rounded-full blur-[100px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6 mb-8 text-center">
        <p className="text-xs font-heading font-semibold text-slate-500 uppercase tracking-widest">
          Trusted by candidates and alumni at world-class companies
        </p>
      </div>

      {/* Ticker Lane 1: Left to Right */}
      <div className="flex overflow-hidden w-full select-none py-3 relative">
        {/* Soft edge gradients */}
        <div className="absolute left-0 top-0 bottom-0 w-24 bg-gradient-to-r from-slate-950 to-transparent z-10 pointer-events-none" />
        <div className="absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-slate-950 to-transparent z-10 pointer-events-none" />

        <motion.div
          className="flex gap-16 whitespace-nowrap cursor-pointer shrink-0"
          animate={{ x: [0, -1200] }}
          transition={{
            repeat: Infinity,
            repeatType: "loop",
            duration: 25,
            ease: "linear",
          }}
          whileHover={{ animationPlayState: "paused" }}
        >
          {duplicatedCompanies.map((company, idx) => (
            <span
              key={`lane1-${company.name}-${idx}`}
              className={`font-heading font-bold text-2xl md:text-3xl tracking-tight text-slate-600 transition-colors duration-300 ${company.color}`}
            >
              {company.name}
            </span>
          ))}
        </motion.div>
      </div>

      {/* Ticker Lane 2: Right to Left */}
      <div className="flex overflow-hidden w-full select-none py-3 mt-4 relative">
        {/* Soft edge gradients */}
        <div className="absolute left-0 top-0 bottom-0 w-24 bg-gradient-to-r from-slate-950 to-transparent z-10 pointer-events-none" />
        <div className="absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-slate-950 to-transparent z-10 pointer-events-none" />

        <motion.div
          className="flex gap-16 whitespace-nowrap cursor-pointer shrink-0"
          animate={{ x: [-1200, 0] }}
          transition={{
            repeat: Infinity,
            repeatType: "loop",
            duration: 20, // slightly faster
            ease: "linear",
          }}
          whileHover={{ animationPlayState: "paused" }}
        >
          {duplicatedCompanies.map((company, idx) => (
            <span
              key={`lane2-${company.name}-${idx}`}
              className={`font-heading font-bold text-2xl md:text-3xl tracking-tight text-slate-600 transition-colors duration-300 ${company.color}`}
            >
              {company.name}
            </span>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
