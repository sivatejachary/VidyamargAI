"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, Cpu, Video, CheckCircle, Award, Terminal, Play, BarChart2 } from "lucide-react";

const previewTabs = [
  {
    id: "resume",
    label: "Resume Builder",
    icon: FileText,
    title: "ATS-Optimized Resume Editor",
    description: "Write details with real-time feedback. The editor highlights density issues, suggests action verbs, and computes your live matching score against your target jobs.",
    mockupType: "resume"
  },
  {
    id: "skills",
    label: "Skill Lab",
    icon: Cpu,
    title: "Personalized LMS & Skill Paths",
    description: "Learn missing skills required for your target positions. Study tailored modular lessons, complete coding challenges in an integrated editor, and earn verified skill badges.",
    mockupType: "skills"
  },
  {
    id: "interview",
    label: "AI Interviewer",
    icon: Video,
    title: "Simulated Interview Simulator",
    description: "Face a simulated AI interviewer. Speak into your microphone and camera to answer custom technical and behavioral questions, receiving direct feedback on your speech and code.",
    mockupType: "interview"
  }
];

export default function PlatformScreenshots() {
  const [activeTab, setActiveTab] = useState(previewTabs[0]);

  return (
    <section id="preview" className="py-24 relative overflow-hidden z-10 bg-slate-950/10">
      
      {/* Background Soft Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-[300px] bg-purple-600/3 rounded-full blur-[110px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl md:text-5xl font-heading font-black tracking-tight text-white mb-4">
            Interactive <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-blue-400">Product Preview</span>
          </h2>
          <p className="text-slate-400 font-sans text-base md:text-lg">
            Sneak peek into the core modules candidate dashboard. Sleek developer layouts, live scoring counters, and real-time feedback loops.
          </p>
        </div>

        {/* TAB SELECTORS */}
        <div className="flex justify-center gap-2 md:gap-4 mb-12">
          {previewTabs.map((tab) => {
            const IconComp = tab.icon;
            const isActive = activeTab.id === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab)}
                className={`flex items-center gap-2 py-2.5 px-4 md:px-6 rounded-xl text-xs md:text-sm font-heading font-bold uppercase tracking-wider transition-all duration-300 relative select-none clickable border ${
                  isActive
                    ? "bg-slate-950 border-purple-500/20 text-purple-400 shadow-[0_0_15px_rgba(147,51,234,0.08)] scale-[1.03]"
                    : "bg-slate-950/20 border-slate-900 text-slate-500 hover:text-slate-300 hover:border-slate-800"
                }`}
                role="tab"
                aria-selected={isActive}
              >
                <IconComp className="w-4 h-4" />
                <span>{tab.label}</span>
                {isActive && (
                  <motion.div
                    layoutId="activeTabUnderline"
                    className="absolute -bottom-1 left-2 right-2 h-0.5 bg-purple-500"
                  />
                )}
              </button>
            );
          })}
        </div>

        {/* INTERACTIVE PREVIEW VIEWPORT */}
        <div className="w-full max-w-5xl mx-auto rounded-2xl border border-slate-900 bg-slate-950/60 backdrop-blur-md overflow-hidden shadow-2xl relative select-none min-h-[460px]">
          
          {/* Top Window Chrome Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-slate-900 bg-slate-950/85">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-500/60" />
              <span className="w-3 h-3 rounded-full bg-yellow-500/60" />
              <span className="w-3 h-3 rounded-full bg-green-500/60" />
            </div>
            <div className="text-xs font-mono text-slate-600 bg-slate-950 px-4 py-1 rounded border border-slate-900/60 uppercase tracking-widest">
              vidyamargai.app/{activeTab.id}
            </div>
            <div className="w-12" />
          </div>

          {/* VIEWPORT CONTENT CONTAINER */}
          <div className="p-6 md:p-8 flex flex-col lg:flex-row gap-8 items-stretch justify-center h-full">
            {/* Left Info Panel */}
            <div className="lg:w-1/3 flex flex-col justify-center text-left items-start">
              <h3 className="text-lg md:text-xl font-heading font-black text-white mb-3">
                {activeTab.title}
              </h3>
              <p className="text-slate-400 font-sans text-xs md:text-sm leading-relaxed mb-6">
                {activeTab.description}
              </p>
              
              <div className="flex flex-col gap-3 w-full">
                <div className="flex items-center gap-2 text-xs font-sans text-slate-500">
                  <CheckCircle className="w-4 h-4 text-purple-500 shrink-0" />
                  <span>Real-time local data sync</span>
                </div>
                <div className="flex items-center gap-2 text-xs font-sans text-slate-500">
                  <CheckCircle className="w-4 h-4 text-purple-500 shrink-0" />
                  <span>Interactive assessment metrics</span>
                </div>
              </div>
            </div>

            {/* Right Mockup Display Panel */}
            <div className="lg:w-2/3 flex items-center justify-center relative min-h-[300px]">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeTab.id}
                  initial={{ opacity: 0, scale: 0.96, x: 20 }}
                  animate={{ opacity: 1, scale: 1, x: 0 }}
                  exit={{ opacity: 0, scale: 0.96, x: -20 }}
                  transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                  className="w-full h-full bg-slate-950/70 border border-slate-900 rounded-xl p-5 shadow-inner"
                >
                  {/* RESUME BUILDER MOCKUP */}
                  {activeTab.mockupType === "resume" && (
                    <div className="flex flex-col md:flex-row gap-4 h-full">
                      {/* Left: Resume Editor preview */}
                      <div className="flex-1 border border-slate-900 bg-slate-950 p-4 rounded-lg flex flex-col gap-3">
                        <div className="h-4 bg-slate-900 rounded w-1/3" />
                        <div className="h-2 bg-slate-900 rounded w-1/2" />
                        <hr className="border-slate-900 my-1" />
                        <div className="space-y-2">
                          <div className="h-2.5 bg-slate-900 rounded w-full" />
                          <div className="h-2.5 bg-slate-900 rounded w-5/6" />
                          <div className="h-2.5 bg-slate-900 rounded w-4/5" />
                        </div>
                        <div className="mt-4 space-y-2">
                          <div className="h-4 bg-slate-900 rounded w-1/4" />
                          <div className="h-2.5 bg-slate-900 rounded w-full" />
                          <div className="h-2.5 bg-slate-900 rounded w-11/12" />
                        </div>
                      </div>
                      {/* Right: ATS Checklist */}
                      <div className="w-full md:w-56 flex flex-col gap-3 border border-slate-900 bg-slate-950/80 p-4 rounded-lg">
                        <span className="text-[10px] font-heading font-extrabold uppercase tracking-widest text-slate-500">ATS Checklist</span>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-400">Match score</span>
                          <span className="text-emerald-400 font-mono font-bold">92%</span>
                        </div>
                        <div className="h-1 bg-slate-900 rounded overflow-hidden">
                          <div className="h-full bg-emerald-400 w-[92%]" />
                        </div>
                        
                        <div className="space-y-2 mt-2">
                          <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
                            <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                            <span>Action verbs count OK</span>
                          </div>
                          <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
                            <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                            <span>Correct job title keywords</span>
                          </div>
                          <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
                            <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                            <span>PDF format verified</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* SKILL LAB MOCKUP */}
                  {activeTab.mockupType === "skills" && (
                    <div className="flex flex-col gap-4 h-full">
                      {/* Course listing */}
                      <div className="flex items-center justify-between bg-slate-950 border border-slate-900 p-3 rounded-lg">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center text-xs text-white">JS</div>
                          <div>
                            <div className="text-xs font-heading font-bold text-white">Next.js 15 & React 19 Core</div>
                            <div className="text-[10px] text-slate-500 mt-0.5">Lesson 14/20: Server Components</div>
                          </div>
                        </div>
                        <span className="text-[10px] font-mono text-slate-500">70% done</span>
                      </div>
                      
                      {/* Code editor preview */}
                      <div className="flex-1 border border-slate-900 bg-slate-950 p-4 rounded-lg font-mono text-[10px] text-slate-400 flex flex-col gap-2 relative">
                        <div className="flex items-center justify-between border-b border-slate-900 pb-2 mb-1">
                          <div className="flex items-center gap-1 text-[9px] text-slate-500">
                            <Terminal className="w-3.5 h-3.5" />
                            <span>page.tsx</span>
                          </div>
                          <Play className="w-3 h-3 text-emerald-400 cursor-pointer" />
                        </div>
                        <div className="text-purple-400">export default async function Page() &#123;</div>
                        <div className="pl-4 text-slate-500">// Fetch job matching data asynchronously</div>
                        <div className="pl-4"><span className="text-blue-400">const</span> res = <span className="text-purple-400">await</span> fetch(<span className="text-amber-300">&apos;/api/jobs&apos;</span>);</div>
                        <div className="pl-4"><span className="text-blue-400">const</span> data = <span className="text-purple-400">await</span> res.json();</div>
                        <div className="pl-4"><span className="text-purple-400">return</span> &lt;<span className="text-blue-400">JobContainer</span> data=&#123;data&#125; /&gt;;</div>
                        <div className="text-purple-400">&#125;</div>
                      </div>
                    </div>
                  )}

                  {/* AI INTERVIEWER MOCKUP */}
                  {activeTab.mockupType === "interview" && (
                    <div className="flex flex-col md:flex-row gap-4 h-full">
                      {/* Video feedback simulation */}
                      <div className="flex-1 border border-slate-900 bg-slate-950 rounded-lg flex items-center justify-center relative overflow-hidden min-h-[160px]">
                        {/* Simulated webcam video gradient drift */}
                        <div className="absolute inset-0 bg-gradient-to-br from-indigo-950 via-slate-950 to-purple-950 animate-pulse opacity-80" />
                        
                        <div className="absolute top-3 left-3 bg-red-600/20 text-red-400 px-2 py-0.5 rounded text-[9px] font-mono border border-red-500/20 flex items-center gap-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping" />
                          <span>REC FEED</span>
                        </div>
                        
                        <div className="relative z-10 flex flex-col items-center gap-1 text-center px-4">
                          <Video className="w-8 h-8 text-slate-500 animate-bounce" />
                          <span className="text-[10px] text-slate-500">Camera and Mic Connected</span>
                          <span className="text-xs font-heading font-medium text-slate-300 mt-2 italic">&quot;Explain closures in JavaScript and how you use them.&quot;</span>
                        </div>
                      </div>

                      {/* Real time speech to text metrics */}
                      <div className="w-full md:w-52 border border-slate-900 bg-slate-950/80 p-4 rounded-lg flex flex-col gap-3">
                        <span className="text-[10px] font-heading font-extrabold uppercase tracking-widest text-slate-500">AI Speech Check</span>
                        
                        <div className="space-y-3 mt-1">
                          <div>
                            <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                              <span>Vocal Confidence</span>
                              <span className="font-mono font-bold text-purple-300">92%</span>
                            </div>
                            <div className="h-1 bg-slate-900 rounded overflow-hidden">
                              <div className="h-full bg-purple-400 w-[92%]" />
                            </div>
                          </div>

                          <div>
                            <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                              <span>Grammar / Pace</span>
                              <span className="font-mono font-bold text-blue-300">88%</span>
                            </div>
                            <div className="h-1 bg-slate-900 rounded overflow-hidden">
                              <div className="h-full bg-blue-400 w-[88%]" />
                            </div>
                          </div>

                          <div>
                            <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                              <span>Keyword Density</span>
                              <span className="font-mono font-bold text-amber-300">76%</span>
                            </div>
                            <div className="h-1 bg-slate-900 rounded overflow-hidden">
                              <div className="h-full bg-amber-400 w-[76%]" />
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </div>

      </div>
    </section>
  );
}
