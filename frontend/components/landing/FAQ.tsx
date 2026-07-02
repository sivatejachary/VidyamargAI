"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, HelpCircle } from "lucide-react";

const faqs = [
  {
    q: "What is VidyaMarg AI?",
    a: "VidyaMarg AI is an AI-powered career platform designed for tech talent. Instead of using isolated tools, VidyaMarg AI provides a single, unified loop: building ATS-targeted resumes, analyzing skill gaps, delivering tailored courses to fill those gaps, conducting simulated mock interviews, and deploying autonomous career agents to find and apply for jobs."
  },
  {
    q: "How does the AI Resume Builder optimize my resume?",
    a: "Our builder analyzes target job specifications and scans your current resume. It calculates an ATS match score based on keyword relevance, formatting rules, and impact phrasing. It suggestions exact replacements, formats, and action verbs to ensure your CV passes HR filters."
  },
  {
    q: "How do the custom mock interviews work?",
    a: "You select a target company and role. The AI generates custom technical coding challenges or behavioral questions based on that company's real interview logs. You answer on video/mic, and receive instant feedback on your code correctness, speech pace, and keywords match density."
  },
  {
    q: "What is included in the Free Learning Tier?",
    a: "The Free Learning Tier is free forever. It provides full access to our LMS Learning Hub course listings, public career roadmaps, and basic quizzes. It is built to help talent learn skills without barriers."
  },
  {
    q: "How does the true Autonomous AI Agent help my career?",
    a: "Available on our Pro tier, the Autonomous Career Agent acts as your dedicated recruiter. It monitors job boards 24/7, scores matching listing compatibility, optimizes your resume for high-fit jobs, prepares custom practice questions, and helps track applications from start to offer."
  },
  {
    q: "Can I cancel my Pro Career membership anytime?",
    a: "Yes. You can cancel your monthly Pro Career subscription at any point from your dashboard settings. You will retain access to your Pro tools until the end of your billing cycle, after which your account reverts to the Free Learning Tier."
  }
];

export default function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const toggleFAQ = (index: number) => {
    setOpenIndex((prev) => (prev === index ? null : index));
  };

  return (
    <section id="faqs" className="py-24 relative overflow-hidden z-10">
      
      {/* Background Soft Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2/3 h-1/2 bg-purple-600/2 rounded-full blur-[100px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-3xl md:text-5xl font-heading font-black tracking-tight text-white mb-4">
            Frequently Asked <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-blue-400">Questions</span>
          </h2>
          <p className="text-slate-400 font-sans text-base md:text-lg">
            Have questions about subscriptions, features, or how our AI matching works? Here are direct answers.
          </p>
        </div>

        {/* ACCORDION SHELF */}
        <div className="w-full max-w-3xl mx-auto flex flex-col gap-4 select-none">
          {faqs.map((faq, idx) => {
            const isOpen = openIndex === idx;

            return (
              <div
                key={faq.q}
                className="rounded-2xl border border-slate-900 bg-slate-950/45 backdrop-blur-md overflow-hidden transition-all duration-300"
                style={{
                  borderColor: isOpen ? "rgba(168, 85, 247, 0.2)" : "rgba(15, 23, 42, 1)"
                }}
              >
                {/* Accordion Trigger Header */}
                <button
                  onClick={() => toggleFAQ(idx)}
                  className="w-full py-5 px-6 flex items-center justify-between text-left hover:bg-white/[0.01] transition-colors focus-visible:ring-2 focus-visible:ring-purple-500/80 focus-visible:outline-none"
                  aria-expanded={isOpen}
                >
                  <span className="font-heading font-bold text-sm md:text-base text-white flex items-center gap-2.5">
                    <HelpCircle className="w-4 h-4 text-purple-400 shrink-0" />
                    {faq.q}
                  </span>
                  <ChevronDown
                    className={`w-4.5 h-4.5 text-slate-500 transition-transform duration-300 ${
                      isOpen ? "rotate-180 text-purple-400" : ""
                    }`}
                  />
                </button>

                {/* Accordion Answer Content */}
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                      className="overflow-hidden"
                    >
                      <div className="pb-6 pt-1 px-6 border-t border-slate-900/40 text-xs md:text-sm font-sans text-slate-400 leading-relaxed pl-12 text-left">
                        {faq.a}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>

      </div>
    </section>
  );
}
