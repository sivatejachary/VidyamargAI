"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, Sparkles, AlertCircle } from "lucide-react";
import { usePageTransition } from "./PageTransitionOverlay";

export default function Pricing() {
  const { startTransition } = usePageTransition();
  const [isAnnual, setIsAnnual] = useState(false);

  const plans = [
    {
      name: "Free Learning",
      priceMonthly: 0,
      priceAnnual: 0,
      desc: "Unlock core educational courses and mapping guides.",
      features: [
        "Access to basic LMS Learning Hub",
        "Public career path roadmaps",
        "Basic skill assessment quizzes",
        "Community support access"
      ],
      cta: "Start Learning",
      action: () => startTransition("/signup"),
      popular: false,
      glow: "border-slate-900"
    },
    {
      name: "Pro Career",
      priceMonthly: 49,
      priceAnnual: 39,
      desc: "The complete AI-powered job search engine and agent loop.",
      features: [
        "All Free Learning features",
        "Unlimited AI Resume Builder & score checks",
        "AI Job Discovery & matching fits analysis",
        "AI Mock Interviews (unlimited simulations)",
        "True Autonomous AI Agent career assistant",
        "Priority queue response & coach support"
      ],
      cta: "Join Pro Career",
      action: () => startTransition("/signup"),
      popular: true,
      glow: "border-purple-500/30 shadow-[0_0_30px_rgba(147,51,234,0.15)]"
    },
    {
      name: "Enterprise Placement",
      priceMonthly: 199,
      priceAnnual: 159,
      desc: "Custom tooling for training institutions and headhunters.",
      features: [
        "All Pro Career capabilities",
        "Hiring manager screening dashboard",
        "Institution cohort analytical progress logs",
        "Custom branding & course uploading",
        "Direct HR APIs & ATS exports",
        "Dedicated account placement manager"
      ],
      cta: "Contact Sales",
      action: () => startTransition("/signup"), // Redirects to signup/contact
      popular: false,
      glow: "border-slate-900"
    }
  ];

  return (
    <section id="pricing" className="py-24 relative overflow-hidden z-10">
      
      {/* Background Soft Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-[300px] bg-purple-600/3 rounded-full blur-[110px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-12">
          <h2 className="text-3xl md:text-5xl font-heading font-black tracking-tight text-white mb-4">
            Simple, Transparent <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-blue-400">Pricing</span>
          </h2>
          <p className="text-slate-400 font-sans text-base md:text-lg">
            Choose the tier that maps to your immediate needs. Free learning forever, or premium Pro capabilities to secure placements fast.
          </p>
        </div>

        {/* BILLING TOGGLE CONTAINER */}
        <div className="flex justify-center items-center gap-3 mb-16 select-none">
          <span className={`text-xs font-heading font-bold uppercase tracking-wider ${!isAnnual ? "text-white" : "text-slate-500"}`}>
            Monthly
          </span>
          
          <button
            onClick={() => setIsAnnual(!isAnnual)}
            className="w-12 h-6.5 rounded-full bg-slate-900 p-1 flex items-center cursor-pointer transition-colors relative border border-slate-800 focus:outline-none focus:ring-1 focus:ring-purple-500"
            role="switch"
            aria-checked={isAnnual}
            aria-label="Toggle annual billing"
          >
            <motion.div
              layout
              className="w-4.5 h-4.5 rounded-full bg-purple-500 shadow-md"
              animate={{ x: isAnnual ? 20 : 0 }}
              transition={{ type: "spring", stiffness: 500, damping: 30 }}
            />
          </button>

          <div className="flex items-center gap-1.5">
            <span className={`text-xs font-heading font-bold uppercase tracking-wider ${isAnnual ? "text-white" : "text-slate-500"}`}>
              Yearly
            </span>
            <span className="text-[10px] font-heading font-extrabold uppercase tracking-widest text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              Save 20%
            </span>
          </div>
        </div>

        {/* PLANS GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch select-none max-w-5xl mx-auto">
          {plans.map((plan, idx) => {
            const price = isAnnual ? plan.priceAnnual : plan.priceMonthly;

            return (
              <motion.div
                key={plan.name}
                initial={{ opacity: 0, y: 25 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-100px" }}
                transition={{ duration: 0.5, delay: idx * 0.15 }}
                className={`w-full relative flex flex-col justify-between p-8 rounded-2xl border ${
                  plan.popular ? "bg-slate-950 border-purple-500/30" : "bg-slate-950/40 border-slate-900"
                } ${plan.glow} backdrop-blur-md select-none`}
              >
                {/* Popular Ribbon/Badge */}
                {plan.popular && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-gradient-to-r from-purple-600 to-blue-600 text-white text-[10px] font-heading font-black uppercase tracking-widest px-4 py-1.5 rounded-full border border-purple-500/20 shadow-md flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5 animate-spin-slow" />
                    <span>Most Popular</span>
                  </div>
                )}

                <div className="text-left">
                  {/* Plan Name */}
                  <h3 className="font-heading font-bold text-lg text-white mb-2">{plan.name}</h3>
                  <p className="font-sans text-xs text-slate-500 leading-relaxed mb-6">{plan.desc}</p>
                  
                  {/* Price display */}
                  <div className="flex items-baseline gap-1 border-b border-slate-900/60 pb-6 mb-6">
                    <span className="font-mono text-4xl md:text-5xl font-black text-white">${price}</span>
                    <span className="text-xs text-slate-500 font-sans">/ month</span>
                  </div>

                  {/* Feature Checklist */}
                  <ul className="space-y-4 mb-8">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-2.5 text-xs text-slate-400 text-left">
                        <Check className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* CTA Action Button */}
                <button
                  onClick={plan.action}
                  className={`w-full py-3.5 rounded-xl font-heading font-bold text-xs uppercase tracking-wider transition-all duration-300 select-none clickable ${
                    plan.popular
                      ? "bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 text-white shadow-lg shadow-purple-500/10 hover:scale-[1.02] active:scale-[0.98]"
                      : "bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 hover:border-slate-700 active:scale-[0.98]"
                  }`}
                >
                  {plan.cta}
                </button>
              </motion.div>
            );
          })}
        </div>

      </div>
    </section>
  );
}
