"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Sparkles, 
  CheckCircle2, 
  ArrowUpRight, 
  Briefcase, 
  GraduationCap, 
  UserCheck, 
  Bell,
  LineChart
} from "lucide-react";

const notificationPool = [
  { id: 1, text: "Resume score matched 94% for Google SDE role", type: "success" },
  { id: 2, text: "New React mock interview feedback ready", type: "info" },
  { id: 3, text: "Accenture shortlisting candidate files now", type: "warning" },
  { id: 4, text: "NVIDIA mock interview scheduled for Friday", type: "success" },
  { id: 5, text: "Completed System Design course module", type: "info" }
];

export default function DashboardPreview() {
  const [resumeScore, setResumeScore] = useState(78);
  const [jobsCount, setJobsCount] = useState(12);
  const [activeAlert, setActiveAlert] = useState(notificationPool[0]);
  const [loopIndex, setLoopIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setLoopIndex((prev) => {
        const next = (prev + 1) % 3;
        
        // Loop 1: Resume Score 78% -> 84% -> 91%
        if (next === 0) {
          setResumeScore(78);
          setJobsCount(12);
        } else if (next === 1) {
          setResumeScore(84);
          setJobsCount(19);
        } else {
          setResumeScore(91);
          setJobsCount(25);
        }

        // Cycle notifications
        setActiveAlert(notificationPool[(prev + 1) % notificationPool.length]);

        return next;
      });
    }, 4500);

    return () => clearInterval(interval);
  }, []);

  return (
    <section className="py-24 relative overflow-hidden z-10">
      
      {/* Background Soft Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-[350px] bg-blue-600/3 rounded-full blur-[120px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl md:text-5xl font-heading font-black tracking-tight text-white mb-4">
            Live <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-blue-400">Dashboard Preview</span>
          </h2>
          <p className="text-slate-400 font-sans text-base md:text-lg">
            See your career cockpit update in real-time as the autonomous agent matches jobs, analyzes skills, and runs optimization checks.
          </p>
        </div>

        {/* FUTURISTIC DASHBOARD FRAME */}
        <div className="w-full max-w-4xl mx-auto rounded-3xl border border-slate-900 bg-slate-950/40 backdrop-blur-md shadow-2xl relative overflow-hidden flex flex-col items-stretch p-6 md:p-8 select-none">
          
          {/* Dashboard Header Bar */}
          <div className="flex items-center justify-between border-b border-slate-900/60 pb-6 mb-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-purple-400" />
              </div>
              <div>
                <h3 className="font-heading font-bold text-sm text-white">VidyaMarg AI Cockpit</h3>
                <p className="text-[10px] font-sans text-slate-500">Autonomous processing online</p>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-widest">Live Syncing</span>
            </div>
          </div>

          {/* DASHBOARD GRID CONTENT */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-stretch">
            
            {/* LEFT 7 COLS: Metrics Grid & Analytics */}
            <div className="md:col-span-7 flex flex-col gap-6">
              
              {/* Top Row: Resume Score Card & Recommended Jobs */}
              <div className="grid grid-cols-2 gap-4">
                {/* Resume Score circular progress */}
                <div className="border border-slate-900 bg-slate-950/60 p-5 rounded-2xl flex flex-col items-center text-center justify-between relative overflow-hidden">
                  <span className="text-[10px] font-heading font-extrabold uppercase tracking-widest text-slate-500">Resume Score</span>
                  
                  <div className="relative w-28 h-28 my-4 flex items-center justify-center">
                    <svg className="w-full h-full transform -rotate-90">
                      <circle
                        cx="56"
                        cy="56"
                        r="45"
                        fill="transparent"
                        stroke="#111827"
                        strokeWidth="8"
                      />
                      <motion.circle
                        cx="56"
                        cy="56"
                        r="45"
                        fill="transparent"
                        stroke="#a855f7"
                        strokeWidth="8"
                        strokeDasharray={2 * Math.PI * 45}
                        animate={{ strokeDashoffset: (2 * Math.PI * 45) * (1 - resumeScore / 100) }}
                        transition={{ duration: 0.8, ease: "easeOut" }}
                        className="filter drop-shadow-[0_0_6px_rgba(168,85,247,0.5)]"
                      />
                    </svg>
                    <div className="absolute flex flex-col items-center">
                      <span className="font-mono text-2xl font-black text-white">{resumeScore}%</span>
                      <span className="text-[8px] font-heading text-purple-400 uppercase tracking-wider">ATS Score</span>
                    </div>
                  </div>

                  <span className="text-[10px] font-sans text-slate-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>Optimization OK</span>
                  </span>
                </div>

                {/* Jobs Match Counter */}
                <div className="border border-slate-900 bg-slate-950/60 p-5 rounded-2xl flex flex-col justify-between items-start text-left relative overflow-hidden">
                  <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mb-3">
                    <Briefcase className="w-4 h-4 text-blue-400" />
                  </div>
                  
                  <span className="text-[10px] font-heading font-extrabold uppercase tracking-widest text-slate-500">Matched Jobs</span>
                  
                  <div className="my-2">
                    <span className="font-mono text-4xl font-black text-white">+{jobsCount}</span>
                    <span className="text-xs text-emerald-400 font-mono ml-2 font-semibold">New</span>
                  </div>

                  <p className="text-[10px] font-sans text-slate-400">
                    High relevance openings matched
                  </p>
                </div>
              </div>

              {/* Bottom: Skill Progress circular/linear bars */}
              <div className="border border-slate-900 bg-slate-950/60 p-5 rounded-2xl flex flex-col text-left justify-between">
                <span className="text-[10px] font-heading font-extrabold uppercase tracking-widest text-slate-500 mb-4">Core Skill Index</span>
                
                <div className="space-y-4">
                  {/* Skill 1 */}
                  <div>
                    <div className="flex justify-between text-xs mb-1.5">
                      <span className="text-slate-300 font-medium">System Design & Patterns</span>
                      <span className="font-mono text-purple-400 font-bold">85%</span>
                    </div>
                    <div className="h-1.5 bg-slate-900 rounded overflow-hidden">
                      <motion.div 
                        animate={{ width: "85%" }} 
                        transition={{ duration: 1 }} 
                        className="h-full bg-gradient-to-r from-purple-600 to-blue-500 shadow-[0_0_8px_rgba(168,85,247,0.5)]" 
                      />
                    </div>
                  </div>

                  {/* Skill 2 */}
                  <div>
                    <div className="flex justify-between text-xs mb-1.5">
                      <span className="text-slate-300 font-medium">React 19 & Next.js 15 App Router</span>
                      <span className="font-mono text-purple-400 font-bold">92%</span>
                    </div>
                    <div className="h-1.5 bg-slate-900 rounded overflow-hidden">
                      <motion.div 
                        animate={{ width: "92%" }} 
                        transition={{ duration: 1 }} 
                        className="h-full bg-gradient-to-r from-purple-600 to-blue-500 shadow-[0_0_8px_rgba(168,85,247,0.5)]" 
                      />
                    </div>
                  </div>

                  {/* Skill 3 */}
                  <div>
                    <div className="flex justify-between text-xs mb-1.5">
                      <span className="text-slate-300 font-medium">Data Structures & SQL</span>
                      <span className="font-mono text-purple-400 font-bold">76%</span>
                    </div>
                    <div className="h-1.5 bg-slate-900 rounded overflow-hidden">
                      <motion.div 
                        animate={{ width: "76%" }} 
                        transition={{ duration: 1 }} 
                        className="h-full bg-gradient-to-r from-purple-600 to-blue-500 shadow-[0_0_8px_rgba(168,85,247,0.5)]" 
                      />
                    </div>
                  </div>
                </div>
              </div>

            </div>

            {/* RIGHT 5 COLS: Active application tracking list & Log notifications */}
            <div className="md:col-span-5 flex flex-col gap-6 justify-between items-stretch">
              
              {/* Application Tracking stage card */}
              <div className="border border-slate-900 bg-slate-950/60 p-5 rounded-2xl flex-1 flex flex-col text-left justify-between min-h-[220px]">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-[10px] font-heading font-extrabold uppercase tracking-widest text-slate-500">Active Pipelines</span>
                  <LineChart className="w-4 h-4 text-purple-400" />
                </div>

                <div className="space-y-3 flex-1 flex flex-col justify-center">
                  <div className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-900">
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                      <span className="text-xs text-slate-300">Google — SDE 1</span>
                    </div>
                    <span className="text-[9px] font-heading font-bold uppercase tracking-wider text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">Interviewing</span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-900">
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-purple-500" />
                      <span className="text-xs text-slate-300">NVIDIA — AI Eng</span>
                    </div>
                    <span className="text-[9px] font-heading font-bold uppercase tracking-wider text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">Code Round</span>
                  </div>

                  <div className="flex items-center justify-between p-2 rounded bg-slate-950 border border-slate-900">
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      <span className="text-xs text-slate-300">Microsoft — SDE 2</span>
                    </div>
                    <span className="text-[9px] font-heading font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">Applied</span>
                  </div>
                </div>
              </div>

              {/* Looping Alerts Logs */}
              <div className="border border-slate-900 bg-slate-950/60 p-4 rounded-2xl flex flex-col justify-center items-stretch overflow-hidden h-24 relative text-left">
                <div className="absolute top-3 left-4 flex items-center gap-1.5">
                  <Bell className="w-3.5 h-3.5 text-purple-400 animate-bounce" />
                  <span className="text-[9px] font-heading font-extrabold uppercase tracking-widest text-slate-500">Autonomous log</span>
                </div>
                
                <div className="mt-4">
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={activeAlert.id}
                      initial={{ opacity: 0, y: 15 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -15 }}
                      transition={{ duration: 0.35 }}
                      className="text-xs font-sans text-slate-300 pl-1 leading-relaxed"
                    >
                      {activeAlert.text}
                    </motion.div>
                  </AnimatePresence>
                </div>
              </div>

            </div>

          </div>

        </div>

      </div>
    </section>
  );
}
