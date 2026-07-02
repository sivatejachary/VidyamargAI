"use client";

import React from "react";
import { Check, X, Sparkles } from "lucide-react";
import { motion } from "framer-motion";

const comparisonData = [
  {
    feature: "Scope & Ecosystem",
    traditional: "Only Jobs (Stiff database search)",
    vidyamarg: "Jobs + Learning (Interlocking feedback loop)",
    isSpecial: true
  },
  {
    feature: "Resume Generation",
    traditional: "Manual Resume (Difficult templates)",
    vidyamarg: "AI Resume Builder (Automated ATS-targeted builder)",
    isSpecial: false
  },
  {
    feature: "Career Guidance",
    traditional: "No Career Roadmap (Figure it out yourself)",
    vidyamarg: "Personalized Roadmap (Custom curriculum courses)",
    isSpecial: false
  },
  {
    feature: "Recommendation Accuracy",
    traditional: "Generic Recommendations (Irrelevant spam alerts)",
    vidyamarg: "AI Personalized Matching (Fit score match analytics)",
    isSpecial: false
  },
  {
    feature: "Interview Preparation",
    traditional: "No Interview Help (Go into calls blind)",
    vidyamarg: "AI Interview Practice (Real-time code rounds simulator)",
    isSpecial: false
  }
];

export default function WhyVidyaMarg() {
  return (
    <section id="why-us" className="py-24 relative overflow-hidden z-10 bg-slate-950/20">
      
      {/* Background Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-2/3 bg-blue-600/2 rounded-full blur-[120px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl md:text-5xl font-heading font-black tracking-tight text-white mb-4">
            Why Choose <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-violet-300 to-blue-400">VidyaMarg AI?</span>
          </h2>
          <p className="text-slate-400 font-sans text-base md:text-lg">
            Traditional portals only show listings and collect CVs. VidyaMarg AI guides your entire growth, preparation, and success.
          </p>
        </div>

        {/* COMPARISON TABLE */}
        <div className="w-full max-w-4xl mx-auto rounded-3xl border border-slate-900/80 bg-slate-950/40 backdrop-blur-md overflow-hidden shadow-2xl relative select-none">
          {/* Header Row */}
          <div className="grid grid-cols-12 border-b border-slate-900 py-6 px-6 md:px-8 bg-slate-950/60 font-heading font-bold text-xs uppercase tracking-wider text-slate-500">
            <div className="col-span-4 md:col-span-4 text-left">Core Capabilities</div>
            <div className="col-span-4 md:col-span-4 text-center">Traditional Portals</div>
            <div className="col-span-4 md:col-span-4 text-right pr-2 text-purple-400">VidyaMarg AI</div>
          </div>

          {/* Comparison Rows */}
          <div className="divide-y divide-slate-900/60">
            {comparisonData.map((row, idx) => (
              <motion.div
                key={row.feature}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.5, delay: idx * 0.1 }}
                className={`grid grid-cols-12 py-6 px-6 md:px-8 items-center transition-all duration-300 group hover:bg-white/[0.015] ${
                  row.isSpecial ? "bg-purple-950/5" : ""
                }`}
              >
                {/* Feature Name */}
                <div className="col-span-4 md:col-span-4 text-left">
                  <span className="font-heading font-bold text-sm md:text-base text-slate-300 group-hover:text-white transition-colors flex items-center gap-1.5">
                    {row.isSpecial && <Sparkles className="w-3.5 h-3.5 text-purple-400 animate-pulse shrink-0" />}
                    {row.feature}
                  </span>
                </div>

                {/* Traditional Portal Column */}
                <div className="col-span-4 md:col-span-4 flex flex-col md:flex-row items-center justify-center gap-2 text-center text-xs md:text-sm text-slate-500">
                  <X className="w-4 h-4 text-red-500/80 shrink-0" />
                  <span className="hidden sm:inline font-sans">{row.traditional}</span>
                </div>

                {/* VidyaMarg AI Column */}
                <div className="col-span-4 md:col-span-4 flex flex-col md:flex-row items-center justify-end gap-2 text-right text-xs md:text-sm font-semibold text-purple-300">
                  <Check className="w-4.5 h-4.5 text-emerald-400 filter drop-shadow-[0_0_4px_rgba(52,211,153,0.3)] shrink-0" />
                  <span className="hidden sm:inline font-heading">{row.vidyamarg}</span>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Table Footer Accent Line */}
          <div className="h-1.5 w-full bg-gradient-to-r from-purple-600 via-indigo-600 to-blue-500" />
        </div>

      </div>
    </section>
  );
}
