"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Star, Quote, ChevronLeft, ChevronRight } from "lucide-react";

const testimonials = [
  {
    name: "Aishwarya Sen",
    role: "Software Engineer",
    company: "Google",
    rating: 5,
    quote: "VidyaMarg AI mapped my skill gaps perfectly. In 3 weeks, I completed the recommended System Design lessons, optimized my resume ATS score, and landed my first interview call!",
    gradient: "from-purple-500 to-indigo-500",
    initialRotation: -1.5
  },
  {
    name: "Rahul Nair",
    role: "Backend Engineer",
    company: "Amazon",
    rating: 5,
    quote: "The mock coding rounds simulator was a lifesaver. It simulated high-pressure questions and gave granular advice on my vocal speed, tone, and keyword usage.",
    gradient: "from-blue-500 to-cyan-500",
    initialRotation: 1.5
  },
  {
    name: "Priya Das",
    role: "AI Dev Analyst",
    company: "NVIDIA",
    rating: 5,
    quote: "The true autonomous agent found listings I couldn't see elsewhere. It matches skills, ranks fits, and auto-runs optimizations. An absolute game-changer.",
    gradient: "from-emerald-500 to-teal-500",
    initialRotation: -1.0
  },
  {
    name: "Karan Johar",
    role: "Cloud Specialist",
    company: "Oracle",
    rating: 5,
    quote: "The roadmap module suggested database courses I didn't know I lacked. Having jobs, lessons, and interview prep in one feedback loop speeds up placements.",
    gradient: "from-amber-500 to-orange-500",
    initialRotation: 1.2
  }
];

export default function Testimonials() {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % testimonials.length);
    }, 6000);
    return () => clearInterval(timer);
  }, []);

  const handlePrev = () => {
    setActiveIndex((prev) => (prev - 1 + testimonials.length) % testimonials.length);
  };

  const handleNext = () => {
    setActiveIndex((prev) => (prev + 1) % testimonials.length);
  };

  return (
    <section id="testimonials" className="py-24 relative overflow-hidden z-10">
      
      {/* Background Soft Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2/3 h-1/2 bg-blue-600/2 rounded-full blur-[100px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl md:text-5xl font-heading font-black tracking-tight text-white mb-4">
            Candidate <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-blue-400">Success Stories</span>
          </h2>
          <p className="text-slate-400 font-sans text-base md:text-lg">
            Hear from our alumni who used VidyaMarg AI to pinpoint skills gaps, master coding challenges, and secure tech placements.
          </p>
        </div>

        {/* CAROUSEL SHELF */}
        <div className="relative w-full max-w-3xl mx-auto flex flex-col items-center">
          
          <div className="w-full relative min-h-[280px] md:min-h-[220px] flex items-center justify-center">
            <AnimatePresence mode="wait">
              {testimonials.map((test, idx) => {
                if (idx !== activeIndex) return null;

                return (
                  <motion.div
                    key={test.name}
                    initial={{ opacity: 0, scale: 0.95, y: 15 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: -15 }}
                    transition={{ duration: 0.45 }}
                    className="w-full"
                  >
                    <div
                      className="p-8 rounded-2xl border border-slate-900 bg-slate-950/50 backdrop-blur-md shadow-2xl relative select-none animate-float-2 group text-left"
                      style={{
                        transform: `perspective(1000px) rotate(${test.initialRotation}deg)`,
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = "perspective(1000px) rotate(0deg) scale(1.025)";
                        e.currentTarget.style.borderColor = "rgba(168, 85, 247, 0.35)";
                        e.currentTarget.style.boxShadow = "0 20px 40px rgba(147, 51, 234, 0.1)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = `perspective(1000px) rotate(${test.initialRotation}deg) scale(1)`;
                        e.currentTarget.style.borderColor = "rgba(15, 23, 42, 1)";
                        e.currentTarget.style.boxShadow = "none";
                      }}
                    >
                      {/* Quote mark decorator */}
                      <Quote className="absolute top-6 right-8 w-12 h-12 text-slate-800/60 pointer-events-none" />

                      <div className="flex flex-col gap-6 relative z-10">
                        {/* Rating */}
                        <div className="flex items-center gap-1">
                          {[...Array(test.rating)].map((_, i) => (
                            <Star key={i} className="w-4 h-4 fill-amber-400 text-amber-400" />
                          ))}
                        </div>

                        {/* Quote Text */}
                        <p className="font-sans text-slate-300 text-sm md:text-base leading-relaxed italic">
                          &quot;{test.quote}&quot;
                        </p>

                        {/* Author info */}
                        <div className="flex items-center gap-4 border-t border-slate-900/60 pt-4">
                          <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${test.gradient} flex items-center justify-center font-heading font-bold text-white text-sm shadow-md`}>
                            {test.name.split(" ").map(n => n[0]).join("")}
                          </div>
                          <div>
                            <h4 className="font-heading font-bold text-sm text-white">{test.name}</h4>
                            <p className="text-slate-500 font-sans text-xs mt-0.5">
                              {test.role} — <span className="text-purple-400 font-medium">{test.company}</span>
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>

          {/* CONTROLS */}
          <div className="flex items-center gap-4 mt-8">
            <button
              onClick={handlePrev}
              className="p-2 rounded-xl border border-slate-900 bg-slate-950/60 hover:bg-slate-900 text-slate-400 hover:text-white transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:outline-none clickable"
              aria-label="Previous testimonial"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="font-mono text-xs text-slate-500">
              {activeIndex + 1} / {testimonials.length}
            </span>
            <button
              onClick={handleNext}
              className="p-2 rounded-xl border border-slate-900 bg-slate-950/60 hover:bg-slate-900 text-slate-400 hover:text-white transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:outline-none clickable"
              aria-label="Next testimonial"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>

        </div>

      </div>
    </section>
  );
}
