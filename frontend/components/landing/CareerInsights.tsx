"use client";

import React from "react";
import { motion } from "framer-motion";
import { ArrowUpRight, Clock, FileText, Cpu, LineChart } from "lucide-react";

// Stylized SVG illustrations to act as premium card covers
function ATSIllustration() {
  return (
    <div className="w-full h-full bg-slate-950 flex items-center justify-center relative overflow-hidden group-hover:scale-105 transition-transform duration-500">
      <div className="absolute inset-0 bg-radial-gradient from-purple-500/10 to-transparent pointer-events-none" />
      <div className="border border-slate-900 bg-slate-950 p-4 rounded-lg w-3/4 flex flex-col gap-2 relative z-10 shadow-lg">
        <div className="flex items-center justify-between border-b border-slate-900 pb-2">
          <span className="text-[9px] font-mono text-purple-400">ats_scanner_v2.log</span>
          <span className="text-[9px] font-mono text-emerald-400 font-bold">MATCH 94%</span>
        </div>
        <div className="h-2 bg-slate-900 rounded w-1/2" />
        <div className="h-1.5 bg-slate-900 rounded w-5/6" />
        <div className="h-1.5 bg-slate-900 rounded w-3/4" />
        <div className="h-1.5 bg-slate-900/60 rounded w-2/3" />
      </div>
    </div>
  );
}

function SkillsIllustration() {
  return (
    <div className="w-full h-full bg-slate-950 flex items-center justify-center relative overflow-hidden group-hover:scale-105 transition-transform duration-500">
      <div className="absolute inset-0 bg-radial-gradient from-blue-500/10 to-transparent pointer-events-none" />
      <div className="relative z-10 flex gap-2 items-center justify-center">
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center font-heading font-extrabold text-white text-xs shadow-lg">React</div>
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center font-heading font-extrabold text-white text-xs shadow-lg">TS</div>
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-600 to-teal-600 flex items-center justify-center font-heading font-extrabold text-white text-xs shadow-lg">Docker</div>
      </div>
    </div>
  );
}

function SDEIllustration() {
  return (
    <div className="w-full h-full bg-slate-950 flex items-center justify-center relative overflow-hidden group-hover:scale-105 transition-transform duration-500">
      <div className="absolute inset-0 bg-radial-gradient from-emerald-500/10 to-transparent pointer-events-none" />
      <div className="w-2/3 h-1/2 border border-slate-900 bg-slate-950 rounded-lg p-4 flex flex-col justify-end gap-3 relative z-10 shadow-lg">
        <div className="flex items-baseline gap-1">
          <span className="text-[10px] text-slate-500 font-sans">L4 Target Salary</span>
          <span className="font-mono text-base font-bold text-white ml-auto">₹35LPA</span>
        </div>
        <div className="h-1.5 bg-slate-900 rounded overflow-hidden">
          <div className="h-full bg-emerald-400 w-[78%]" />
        </div>
      </div>
    </div>
  );
}

const articles = [
  {
    title: "Cracking the ATS in 2026: The AI Screening Rules",
    desc: "Understand how modern HR parsers screen candidate resumes. Read tips on keyword density, template formatting, and metrics targeting.",
    illustration: ATSIllustration,
    readTime: "5 mins read",
    tag: "Resume Tips"
  },
  {
    title: "Top 10 High-Income Developer Skills in Demand",
    desc: "Discover the specific tools and platforms hiring teams are prioritizing. Map your skill path to React 19, Go, and system architectural patterns.",
    illustration: SkillsIllustration,
    readTime: "8 mins read",
    tag: "Skill Gaps"
  },
  {
    title: "Scaling to SDE-2 in India: Salary & Interview Guides",
    desc: "Access salary benchmarking logs and technical questions commonly asked in SDE-2 rounds at Google, Amazon, and leading Indian startups.",
    illustration: SDEIllustration,
    readTime: "6 mins read",
    tag: "Career Guide"
  }
];

export default function CareerInsights() {
  return (
    <section className="py-24 relative overflow-hidden z-10 bg-slate-950/20">
      
      {/* Background Soft Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-[300px] bg-blue-600/2 rounded-full blur-[110px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl md:text-5xl font-heading font-black tracking-tight text-white mb-4">
            Latest <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-blue-400">Career Insights</span>
          </h2>
          <p className="text-slate-400 font-sans text-base md:text-lg">
            Stay ahead with benchmark guides, technical tutorials, and resume advice compiled by our team of recruiters.
          </p>
        </div>

        {/* ARTICLES GRID */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch select-none max-w-5xl mx-auto">
          {articles.map((art, idx) => (
            <motion.div
              key={art.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.5, delay: idx * 0.15 }}
              className="w-full flex flex-col justify-between rounded-2xl border border-slate-900 bg-slate-950/40 backdrop-blur-md overflow-hidden hover:border-purple-500/25 transition-colors duration-300 group select-none cursor-pointer"
            >
              <div className="select-none">
                {/* Illustration Cover */}
                <div className="h-44 w-full border-b border-slate-900 overflow-hidden relative">
                  {React.createElement(art.illustration)}
                  {/* Sweep shine */}
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-[100%] group-hover:translate-x-[150%] transition-transform duration-1000 ease-out pointer-events-none" />
                </div>

                <div className="p-6 text-left">
                  {/* Category Tag & Read Time */}
                  <div className="flex items-center gap-3 text-[10px] font-heading font-extrabold uppercase tracking-widest text-purple-400 mb-3">
                    <span>{art.tag}</span>
                    <span className="w-1.5 h-1.5 rounded-full bg-slate-800" />
                    <span className="text-slate-500 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {art.readTime}
                    </span>
                  </div>

                  {/* Title */}
                  <h3 className="font-heading font-bold text-base text-white group-hover:text-purple-300 transition-colors leading-tight mb-2">
                    {art.title}
                  </h3>

                  {/* Desc */}
                  <p className="font-sans text-xs text-slate-500 leading-relaxed">
                    {art.desc}
                  </p>
                </div>
              </div>

              {/* View Read Link */}
              <div className="px-6 pb-6 pt-2 flex items-center justify-start text-[10px] font-heading font-bold uppercase tracking-widest text-slate-400 group-hover:text-white transition-colors gap-1">
                <span>Read Article</span>
                <ArrowUpRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 duration-200" />
              </div>
            </motion.div>
          ))}
        </div>

      </div>
    </section>
  );
}
