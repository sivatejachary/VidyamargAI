"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  FileText, 
  Search, 
  BookOpen, 
  Video, 
  LayoutDashboard, 
  LineChart,
  ArrowRight,
  Sparkles
} from "lucide-react";

const ecosystemNodes = [
  {
    id: "resume",
    name: "Resume Builder",
    desc: "AI builds your resume to maximize your match score.",
    icon: FileText,
    color: "from-purple-500 to-indigo-500",
    shadow: "shadow-purple-500/20",
    details: "Instantly create ATS-optimized professional resumes. The AI scans job postings in real time to suggest precise industry keywords, formats, and impact metrics that bypass standard filters and catch recruiter attention."
  },
  {
    id: "jobs",
    name: "Job Discovery",
    desc: "AI-matched discovery based on skills and preferences.",
    icon: Search,
    color: "from-blue-500 to-cyan-500",
    shadow: "shadow-blue-500/20",
    details: "Bypass generic search query lists. VidyaMarg AI cross-references your current skills, projects, and career direction with thousands of active listings to suggest high-compatibility matches with transparent fit-scores."
  },
  {
    id: "learning",
    name: "Learning Hub",
    desc: "Acquire missing skills through customized courses.",
    icon: BookOpen,
    color: "from-emerald-500 to-teal-500",
    shadow: "shadow-emerald-500/20",
    details: "AI scans your target jobs, identifies your skill gaps, and unlocks tailored modular courses. Learn exactly what's required for your desired role with interactive labs, assessments, and verified skill badges."
  },
  {
    id: "interview",
    name: "AI Interview",
    desc: "Practice with custom simulated interview setups.",
    icon: Video,
    color: "from-amber-500 to-orange-500",
    shadow: "shadow-amber-500/20",
    details: "Simulate pressure-filled technical coding rounds and behavioral panels. Receive real-time facial analysis, vocal tone assessments, and AI suggestions on how to improve your answers and structure your responses."
  },
  {
    id: "dashboard",
    name: "Career Dashboard",
    desc: "Track all job search applications and milestones.",
    icon: LayoutDashboard,
    color: "from-rose-500 to-pink-500",
    shadow: "shadow-rose-500/20",
    details: "A unified cockpit for your job search. Automatically import listings, monitor candidate stages (Applied, Interviewing, Offer), set follow-up reminders, and sync with your calendar seamlessly."
  },
  {
    id: "growth",
    name: "Career Growth",
    desc: "Long term career growth trajectory and metrics.",
    icon: LineChart,
    color: "from-indigo-500 to-purple-500",
    shadow: "shadow-indigo-500/20",
    details: "Plan your career 3-5 years out. Track salary changes in your industry, map your skills to senior roles, and unlock automated suggestions on what project or certification to take next to boost your earning power."
  }
];

export default function Ecosystem() {
  const [activeNode, setActiveNode] = useState(ecosystemNodes[0]);

  return (
    <section id="ecosystem" className="py-24 relative overflow-hidden z-10">
      
      {/* Background radial soft light */}
      <div className="absolute top-1/3 left-1/4 w-96 h-96 bg-purple-600/5 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/3 right-1/4 w-96 h-96 bg-blue-600/5 rounded-full blur-[120px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl md:text-5xl font-heading font-black tracking-tight text-white mb-4">
            The VidyaMarg AI <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-blue-400">Ecosystem</span>
          </h2>
          <p className="text-slate-400 font-sans text-base md:text-lg">
            Stop stitching together isolated tools. VidyaMarg AI combines the entire career lifecycle into one continuous, intelligent loop.
          </p>
        </div>

        {/* FLOW GRAPH (Desktop: Horizonal, Mobile: Vertical Grid) */}
        <div className="relative mb-12 flex flex-col items-center select-none">
          {/* SVG Connector Paths with flowing light dashes */}
          <div className="absolute inset-0 top-1/2 -translate-y-1/2 w-full h-16 hidden lg:block z-0 pointer-events-none">
            <svg className="w-full h-full">
              <path
                d="M 120,32 L 1050,32"
                fill="none"
                stroke="rgba(147, 51, 234, 0.1)"
                strokeWidth="4"
              />
              <motion.path
                d="M 120,32 L 1050,32"
                fill="none"
                stroke="url(#flow-beam-grad)"
                strokeWidth="4"
                strokeDasharray="15 35"
                animate={{ strokeDashoffset: [-100, 0] }}
                transition={{
                  repeat: Infinity,
                  duration: 6,
                  ease: "linear"
                }}
              />
              <defs>
                <linearGradient id="flow-beam-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#3b82f6" />
                  <stop offset="50%" stopColor="#a855f7" />
                  <stop offset="100%" stopColor="#ec4899" />
                </linearGradient>
              </defs>
            </svg>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:flex lg:flex-row items-center justify-between w-full gap-4 lg:gap-2 relative z-10">
            {ecosystemNodes.map((node, idx) => {
              const IconComponent = node.icon;
              const isActive = activeNode.id === node.id;

              return (
                <div
                  key={node.id}
                  onClick={() => setActiveNode(node)}
                  className={`flex-1 flex flex-col items-center cursor-pointer transition-all duration-300 ${
                    isActive ? "scale-105" : "hover:scale-[1.02]"
                  }`}
                  role="button"
                  tabIndex={0}
                  aria-selected={isActive}
                  aria-label={`View ecosystem step: ${node.name}`}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setActiveNode(node);
                    }
                  }}
                >
                  {/* Glowing Node Button */}
                  <div
                    className={`w-14 h-14 rounded-2xl flex items-center justify-center border transition-all duration-300 relative select-none shadow-lg ${
                      isActive
                        ? `bg-gradient-to-br ${node.color} border-white/20 text-white ${node.shadow} shadow-2xl scale-110`
                        : "bg-slate-950/70 border-slate-900 text-slate-500 hover:text-slate-300 hover:border-slate-800"
                    }`}
                  >
                    <IconComponent className="w-5 h-5" />
                    
                    {/* Active pulse */}
                    {isActive && (
                      <span className="absolute -inset-0.5 rounded-2xl bg-gradient-to-br from-purple-500 to-blue-500 -z-10 animate-ping opacity-25" />
                    )}
                  </div>

                  <span
                    className={`text-xs font-heading font-bold uppercase tracking-wider mt-4 text-center transition-colors duration-300 ${
                      isActive ? "text-purple-400" : "text-slate-500 hover:text-slate-400"
                    }`}
                  >
                    {node.name}
                  </span>

                  {/* Flow Arrow (For Desktop inside node gap, hidden on last item) */}
                  {idx < ecosystemNodes.length - 1 && (
                    <div className="hidden lg:block absolute -right-2 top-[26px] z-20 text-slate-700 pointer-events-none">
                      <ArrowRight className="w-4 h-4" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* NODE DETAIL CARD */}
        <div className="w-full max-w-4xl mx-auto select-text">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeNode.id}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
              className="p-8 md:p-10 rounded-3xl border border-slate-900 bg-slate-950/60 backdrop-blur-md shadow-2xl relative overflow-hidden flex flex-col md:flex-row gap-8 items-center"
            >
              {/* Background gradient sweep */}
              <div className={`absolute top-0 right-0 w-64 h-64 bg-gradient-to-br ${activeNode.color} opacity-[0.03] blur-[80px] pointer-events-none`} />

              {/* Icon / Decor */}
              <div className="shrink-0 flex items-center justify-center">
                <div className={`w-24 h-24 rounded-3xl bg-gradient-to-br ${activeNode.color} flex items-center justify-center shadow-lg`}>
                  {React.createElement(activeNode.icon, { className: "w-10 h-10 text-white" })}
                </div>
              </div>

              {/* Text details */}
              <div className="flex-1 flex flex-col items-start text-left">
                <div className="inline-flex items-center gap-2 mb-2">
                  <Sparkles className="w-4 h-4 text-purple-400 animate-spin-slow" />
                  <span className="text-xs font-heading font-extrabold uppercase tracking-widest text-purple-400">
                    VidyaMarg Suite
                  </span>
                </div>
                
                <h3 className="text-xl md:text-2xl font-heading font-black text-white mb-3">
                  {activeNode.name}
                </h3>
                
                <p className="text-slate-400 font-sans text-sm md:text-base leading-relaxed">
                  {activeNode.details}
                </p>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>

      </div>
    </section>
  );
}
