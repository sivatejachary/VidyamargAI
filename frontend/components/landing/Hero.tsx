"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { usePageTransition } from "./PageTransitionOverlay";
import { 
  Briefcase, 
  FileText, 
  Video, 
  BookOpen, 
  LayoutDashboard, 
  BarChart3,
  ArrowRight,
  TrendingUp
} from "lucide-react";

// Count Up Helper Component
function CountUpNumber({ end, suffix = "", duration = 1.5 }: { end: number; suffix?: string; duration?: number }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let start = 0;
    const increment = end / (duration * 60); // 60fps
    let current = 0;

    const timer = setInterval(() => {
      current += increment;
      if (current >= end) {
        setCount(end);
        clearInterval(timer);
      } else {
        setCount(Math.floor(current));
      }
    }, 1000 / 60);

    return () => clearInterval(timer);
  }, [end, duration]);

  return (
    <span className="font-mono font-bold tracking-tight text-3xl md:text-4xl text-foreground">
      {count.toLocaleString()}{suffix}
    </span>
  );
}

// Cards for the floating panel grid
const heroPanels = [
  { id: "jobs", title: "Job Discovery", icon: Briefcase, color: "bg-indigo-500/10 border border-indigo-500/20 text-indigo-400", desc: "Find matched jobs" },
  { id: "resume", title: "Resume Builder", icon: FileText, color: "bg-sky-500/10 border border-sky-500/20 text-sky-400", desc: "ATS optimization" },
  { id: "interview", title: "AI Mock Interviews", icon: Video, color: "bg-violet-500/10 border border-violet-500/20 text-violet-400", desc: "Real-time practice" },
  { id: "learning", title: "Learning Hub", icon: BookOpen, color: "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400", desc: "Custom skill courses" },
  { id: "dashboard", title: "Career Dashboard", icon: LayoutDashboard, color: "bg-zinc-800/40 border border-zinc-700/30 text-zinc-300", desc: "Track applications" },
  { id: "analytics", title: "Skill Analytics", icon: BarChart3, color: "bg-blue-500/10 border border-blue-500/20 text-blue-400", desc: "Visualize gap score" },
];

export default function Hero() {
  const { startTransition } = usePageTransition();
  const [panels, setPanels] = useState(heroPanels);
  const [showLine, setShowLine] = useState(true);

  // Periodically rearrange panels and toggle line glow to create dynamic connected feel
  useEffect(() => {
    const interval = setInterval(() => {
      // Rearrange by rotating the array
      setPanels((prev) => {
        const next = [...prev];
        const first = next.shift()!;
        next.push(first);
        return next;
      });
      // Toggle glowing lines trigger
      setShowLine(false);
      setTimeout(() => setShowLine(true), 200);
    }, 8500);

    return () => clearInterval(interval);
  }, []);

  // Split text variables for Apple reveal
  const containerVariants = {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: 0.15,
      },
    },
  };

  const lineVariants = {
    hidden: { y: "100%", opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        duration: 0.8,
        ease: [0.16, 1, 0.3, 1] as any,
      },
    },
  };

  return (
    <section className="relative min-h-screen pt-32 pb-20 flex items-center overflow-hidden z-10">
      <div className="max-w-7xl mx-auto px-6 w-full grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
        
        {/* LEFT COLUMN: HERO TEXT & STATS */}
        <div className="lg:col-span-6 flex flex-col items-start text-left z-20">
          {/* Glowing badge */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="mb-6 inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-purple-500/20 bg-purple-500/10 backdrop-blur-md cursor-default select-none animate-pulse"
          >
            <TrendingUp className="w-4 h-4 text-purple-400" />
            <span className="text-xs font-heading font-semibold text-purple-300 uppercase tracking-wider">
              ✨ Next-Gen AI Career Ecosystem
            </span>
          </motion.div>

          {/* Apple-style typography reveal */}
          <motion.h1
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="text-4xl sm:text-5xl md:text-7xl font-heading font-black tracking-tight leading-[1.05] text-foreground flex flex-col mb-6"
          >
            <span className="overflow-hidden block py-1">
              <motion.span variants={lineVariants} className="block">
                One Platform
              </motion.span>
            </span>
            <span className="overflow-hidden block py-1">
              <motion.span variants={lineVariants} className="block text-muted-foreground">
                for Your Complete
              </motion.span>
            </span>
            <span className="overflow-hidden block py-1">
              <motion.span 
                variants={lineVariants} 
                className="block bg-clip-text text-transparent bg-gradient-to-r from-purple-500 via-violet-400 to-blue-500"
              >
                Career Journey
              </motion.span>
            </span>
          </motion.h1>

          {/* Subheading */}
          <motion.p
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6, ease: "easeOut" }}
            className="text-muted-foreground font-sans text-base md:text-lg leading-relaxed max-w-xl mb-10"
          >
            Find jobs, build skills, create ATS-friendly resumes, prepare for interviews, and grow your career—all in one intelligent platform.
          </motion.p>

          {/* Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.75, ease: "easeOut" }}
            className="flex flex-col sm:flex-row gap-4 mb-14 w-full sm:w-auto"
          >
            <button
              onClick={() => startTransition("/signup")}
              className="group inline-flex items-center justify-center gap-2 text-sm font-heading font-bold text-background bg-foreground hover:bg-foreground/90 py-3.5 px-8 rounded-xl shadow-[0_4px_20px_rgba(0,0,0,0.08)] hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 select-none clickable"
            >
              Get Started
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1 duration-200" />
            </button>
            <button
              onClick={() => startTransition("/login")}
              className="inline-flex items-center justify-center text-sm font-heading font-bold text-muted-foreground hover:text-foreground py-3.5 px-8 rounded-xl border border-border hover:border-border-hover hover:bg-muted transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] select-none clickable"
            >
              Login
            </button>
          </motion.div>

          {/* Statistics Grid */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.9 }}
            className="grid grid-cols-2 gap-x-8 gap-y-6 w-full border-t border-border pt-8"
          >
            <div>
              <CountUpNumber end={50000} suffix="+" />
              <p className="text-xs font-heading font-medium text-muted-foreground uppercase tracking-wider mt-1">Active Jobs</p>
            </div>
            <div>
              <CountUpNumber end={500} suffix="+" />
              <p className="text-xs font-heading font-medium text-muted-foreground uppercase tracking-wider mt-1">Hiring Companies</p>
            </div>
            <div>
              <CountUpNumber end={100000} suffix="+" />
              <p className="text-xs font-heading font-medium text-muted-foreground uppercase tracking-wider mt-1">Candidates Registered</p>
            </div>
            <div>
              <CountUpNumber end={95} suffix="%" />
              <p className="text-xs font-heading font-medium text-muted-foreground uppercase tracking-wider mt-1">Success Rate</p>
            </div>
          </motion.div>
        </div>

        {/* RIGHT COLUMN: FLOATING PANELS GRID */}
        <div className="lg:col-span-6 flex items-center justify-center relative w-full h-[500px]">
          
          {/* Connecting glowing SVG lines mapping centers of active blocks */}
          <div className="absolute inset-0 z-0 pointer-events-none">
            <svg className="w-full h-full opacity-60">
              <defs>
                <linearGradient id="glow-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#c084fc" stopOpacity="0" />
                  <stop offset="50%" stopColor="#a855f7" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
                </linearGradient>
              </defs>
              <AnimatePresence>
                {showLine && (
                  <>
                    <motion.path
                      initial={{ pathLength: 0, opacity: 0 }}
                      animate={{ pathLength: 1, opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 1.5, ease: "easeInOut" }}
                      d="M 120,120 L 320,160 M 320,160 L 220,380 M 220,380 L 150,260 M 150,260 L 350,320"
                      fill="none"
                      stroke="url(#glow-grad)"
                      strokeWidth="2.5"
                      strokeDasharray="4 4"
                      className="filter drop-shadow-[0_0_8px_rgba(168,85,247,0.5)]"
                    />
                    <motion.path
                      initial={{ pathLength: 0, opacity: 0 }}
                      animate={{ pathLength: 1, opacity: 0.8 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 2, delay: 0.5, ease: "easeInOut" }}
                      d="M 150,260 L 120,120 M 320,160 L 350,320"
                      fill="none"
                      stroke="rgba(59, 130, 246, 0.25)"
                      strokeWidth="1.5"
                    />
                  </>
                )}
              </AnimatePresence>
            </svg>
          </div>

          {/* Floating cards list with layout animations */}
          <div className="grid grid-cols-2 gap-4 w-full max-w-[420px] relative z-10">
            {panels.map((panel, idx) => {
              const IconComponent = panel.icon;
              // Add slight variations in floating speed/offsets
              const floatClass = 
                idx % 3 === 0 
                  ? "animate-float-1" 
                  : idx % 3 === 1 
                  ? "animate-float-2" 
                  : "animate-float-3";

              return (
                <motion.div
                  key={panel.id}
                  layout
                  transition={{
                    type: "spring",
                    stiffness: 85,
                    damping: 15,
                    mass: 1.2
                  }}
                  className={`w-full group ${floatClass} select-none`}
                >
                  <div className="w-full p-5 rounded-2xl border border-border bg-card/75 backdrop-blur-md shadow-[0_8px_20px_rgba(0,0,0,0.05)] dark:shadow-[0_8px_20px_rgba(0,0,0,0.6)] transition-all duration-300 hover:-translate-y-1.5 hover:border-border-hover overflow-hidden relative select-none">
                    
                    {/* Ambient light reflection shine */}
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-[100%] group-hover:translate-x-[150%] transition-transform duration-1000 ease-out pointer-events-none" />

                    <div className="flex flex-col gap-3 relative z-10">
                      {/* Floating icon */}
                      <div className={`w-9 h-9 rounded-lg ${panel.color} flex items-center justify-center shadow-sm`}>
                        <IconComponent className="w-4 h-4" />
                      </div>
                      
                      <div>
                        <h3 className="font-heading font-bold text-sm text-foreground group-hover:text-purple-500 dark:group-hover:text-purple-300 transition-colors">
                          {panel.title}
                        </h3>
                        <p className="font-sans text-xs text-muted-foreground mt-1">
                          {panel.desc}
                        </p>
                      </div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>

      </div>
    </section>
  );
}
