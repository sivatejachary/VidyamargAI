"use client";

import React, { useEffect, useState, useRef } from "react";
import { motion, useInView } from "framer-motion";

function StatCounter({ end, suffix = "", duration = 1.8 }: { end: number; suffix?: string; duration?: number }) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-100px" });

  useEffect(() => {
    if (!isInView) return;

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
  }, [end, duration, isInView]);

  return (
    <span ref={ref} className="font-mono font-black text-4xl md:text-6xl text-white tracking-tight">
      {count.toLocaleString()}{suffix}
    </span>
  );
}

const statsData = [
  { value: 100000, suffix: "+", label: "Candidates Registered" },
  { value: 50000, suffix: "+", label: "Active Jobs" },
  { value: 500, suffix: "+", label: "Hiring Partners" },
  { value: 95, suffix: "%", label: "Success Placement Rate" }
];

export default function Stats() {
  return (
    <section className="py-20 relative overflow-hidden z-10 border-y border-slate-900 bg-slate-950/40 select-none">
      
      {/* Background Soft Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-4/5 h-[150px] bg-purple-600/3 rounded-full blur-[90px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 lg:grid-cols-4 gap-8 text-center">
        {statsData.map((stat, idx) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.5, delay: idx * 0.1 }}
            className="flex flex-col items-center select-none"
          >
            <div className="flex items-baseline justify-center bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-purple-200">
              <StatCounter end={stat.value} suffix={stat.suffix} />
            </div>
            
            <p className="text-xs md:text-sm font-heading font-semibold text-slate-500 uppercase tracking-widest mt-2">
              {stat.label}
            </p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
