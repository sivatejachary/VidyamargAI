"use client";

import React from "react";
import { motion } from "framer-motion";
import { Search, Compass, ShieldCheck, GraduationCap, Play } from "lucide-react";

const steps = [
  {
    num: "01",
    title: "Discover Your Gaps",
    desc: "Sync your target job role. VidyaMarg AI compares it against your experience, indexing specific skill gaps, knowledge deficits, and resume formatting weaknesses.",
    icon: Compass,
    color: "from-purple-500 to-indigo-500",
    shadow: "shadow-purple-500/10"
  },
  {
    num: "02",
    title: "Build Capabilities",
    desc: "Complete tailored modular courses and coding exercises. Optimize your resume with real-time ATS keyword matching and practice custom mock interviews.",
    icon: GraduationCap,
    color: "from-blue-500 to-cyan-500",
    shadow: "shadow-blue-500/10"
  },
  {
    num: "03",
    title: "Succeed at Scale",
    desc: "Let your autonomous career agent handle matching, applying, and preparing. Track active job postings, get interview calls, and negotiate offer letters.",
    icon: ShieldCheck,
    color: "from-emerald-500 to-teal-500",
    shadow: "shadow-emerald-500/10"
  }
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-24 relative overflow-hidden z-10">
      
      {/* Background Soft Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2/3 h-1/2 bg-purple-500/2 rounded-full blur-[100px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-20">
          <h2 className="text-3xl md:text-5xl font-heading font-black tracking-tight text-white mb-4">
            How <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-blue-400">VidyaMarg AI Works</span>
          </h2>
          <p className="text-slate-400 font-sans text-base md:text-lg">
            Three simple, automated phases to identify gaps, train skills, and secure your next role.
          </p>
        </div>

        {/* STEP CHRONOLOGICAL LAYOUT */}
        <div className="relative grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch select-none max-w-5xl mx-auto">
          {/* Animated Connecting Lines (Desktop only) */}
          <div className="absolute left-[30%] right-[30%] top-14 h-0.5 hidden lg:block z-0 pointer-events-none">
            <svg className="w-full h-full overflow-visible">
              <path
                d="M -30,0 L 260,0"
                fill="none"
                stroke="rgba(147, 51, 234, 0.08)"
                strokeWidth="2"
                strokeDasharray="4 6"
              />
              <motion.path
                d="M -30,0 L 260,0"
                fill="none"
                stroke="#a855f7"
                strokeWidth="2"
                strokeDasharray="4 6"
                animate={{ strokeDashoffset: [-20, 0] }}
                transition={{
                  repeat: Infinity,
                  duration: 2,
                  ease: "linear"
                }}
              />
            </svg>
          </div>

          <div className="absolute left-[65%] right-[5%] top-14 h-0.5 hidden lg:block z-0 pointer-events-none">
            <svg className="w-full h-full overflow-visible">
              <path
                d="M -30,0 L 260,0"
                fill="none"
                stroke="rgba(59, 130, 246, 0.08)"
                strokeWidth="2"
                strokeDasharray="4 6"
              />
              <motion.path
                d="M -30,0 L 260,0"
                fill="none"
                stroke="#3b82f6"
                strokeWidth="2"
                strokeDasharray="4 6"
                animate={{ strokeDashoffset: [-20, 0] }}
                transition={{
                  repeat: Infinity,
                  duration: 2,
                  ease: "linear"
                }}
              />
            </svg>
          </div>

          {steps.map((step, idx) => {
            const IconComponent = step.icon;

            return (
              <motion.div
                key={step.num}
                initial={{ opacity: 0, y: 25 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.5, delay: idx * 0.15 }}
                className="w-full group z-10"
              >
                <div className="h-full p-8 rounded-2xl border border-slate-900 bg-slate-950/50 backdrop-blur-md shadow-xl hover:border-purple-500/25 transition-colors duration-300 relative overflow-hidden flex flex-col justify-between text-left select-none">
                  
                  {/* Floating Step Number */}
                  <div className="absolute top-4 right-6 font-mono text-5xl font-black text-slate-900/40 select-none group-hover:text-purple-500/10 transition-colors">
                    {step.num}
                  </div>

                  <div className="flex flex-col gap-5">
                    {/* Glowing Icon Container */}
                    <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${step.color} flex items-center justify-center border border-white/5 ${step.shadow}`}>
                      <IconComponent className="w-5 h-5 text-white" />
                    </div>

                    <div>
                      <h3 className="font-heading font-bold text-lg text-white mb-2 group-hover:text-purple-300 transition-colors">
                        {step.title}
                      </h3>
                      <p className="font-sans text-xs md:text-sm text-slate-400 leading-relaxed">
                        {step.desc}
                      </p>
                    </div>
                  </div>

                </div>
              </motion.div>
            );
          })}
        </div>

      </div>
    </section>
  );
}
