"use client";

import React, { useState, useEffect } from "react";
import { Sparkles, GraduationCap, Menu, X } from "lucide-react";
import { usePageTransition } from "./PageTransitionOverlay";
import { motion, AnimatePresence } from "framer-motion";

export default function Header() {
  const { startTransition } = usePageTransition();
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 20) {
        setIsScrolled(true);
      } else {
        setIsScrolled(false);
      }
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const navLinks = [
    { name: "Ecosystem", href: "#ecosystem" },
    { name: "Why Us", href: "#why-us" },
    { name: "Features", href: "#features" },
    { name: "Preview", href: "#preview" },
    { name: "How It Works", href: "#how-it-works" },
    { name: "Pricing", href: "#pricing" },
    { name: "FAQs", href: "#faqs" },
  ];

  const handleScrollClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    e.preventDefault();
    setMobileMenuOpen(false);
    const target = document.querySelector(href);
    if (target) {
      target.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-40 transition-all duration-500 ease-out border-b ${
        isScrolled
          ? "py-3 bg-slate-950/85 backdrop-blur-xl border-purple-500/10 shadow-[0_4px_30px_rgba(147,51,234,0.03)]"
          : "py-6 bg-transparent border-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
        {/* LOGO */}
        <div
          onClick={() => startTransition("/")}
          className={`flex items-center gap-2 cursor-pointer transition-transform duration-300 origin-left select-none ${
            isScrolled ? "scale-90" : "scale-100"
          }`}
        >
          <div className="relative w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-blue-500 flex items-center justify-center shadow-[0_0_15px_rgba(147,51,234,0.3)] animate-float-1">
            <GraduationCap className="w-5 h-5 text-white" />
            <Sparkles className="w-3 h-3 text-purple-200 absolute -top-1 -right-1 animate-pulse" />
          </div>
          <span className="font-heading font-bold text-xl tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-purple-100 to-purple-400">
            VidyaMarg <span className="text-purple-400 font-extrabold text-xs ml-1 border border-purple-500/30 px-1.5 py-0.5 rounded bg-purple-500/10">AI</span>
          </span>
        </div>

        {/* DESKTOP NAV LINKS */}
        <nav className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <a
              key={link.name}
              href={link.href}
              onClick={(e) => handleScrollClick(e, link.href)}
              className="text-sm font-sans font-medium text-slate-400 hover:text-white transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:outline-none rounded px-2 py-1"
            >
              {link.name}
            </a>
          ))}
        </nav>

        {/* DESKTOP CTAS */}
        <div className="hidden md:flex items-center gap-4">
          <button
            onClick={() => startTransition("/login")}
            className="text-sm font-heading font-semibold text-slate-300 hover:text-white transition-colors py-2 px-5 rounded-xl border border-slate-800 hover:border-slate-700 hover:bg-slate-900 focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:outline-none select-none clickable"
          >
            Login
          </button>
          
          <button
            onClick={() => startTransition("/signup")}
            className="text-sm font-heading font-semibold text-slate-950 bg-white hover:bg-slate-100 py-2.5 px-6 rounded-xl shadow-[0_4px_15px_rgba(255,255,255,0.06)] hover:scale-[1.02] active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:outline-none select-none clickable"
          >
            Get Started
          </button>
        </div>

        {/* MOBILE MENU TOGGLE */}
        <div className="md:hidden">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="text-slate-400 hover:text-white p-2 focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:outline-none rounded-lg"
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* MOBILE MENU PANEL */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="md:hidden bg-slate-950/95 border-b border-slate-900 backdrop-blur-xl overflow-hidden"
          >
            <div className="px-6 py-8 flex flex-col gap-6">
              {navLinks.map((link) => (
                <a
                  key={link.name}
                  href={link.href}
                  onClick={(e) => handleScrollClick(e, link.href)}
                  className="text-base font-sans font-semibold text-slate-300 hover:text-white transition-colors duration-200"
                >
                  {link.name}
                </a>
              ))}
              <div className="h-px bg-slate-900 my-2" />
              <div className="flex flex-col gap-4">
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    startTransition("/login");
                  }}
                  className="w-full text-center py-3 rounded-xl border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white text-sm font-heading font-semibold"
                >
                  Login
                </button>
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    startTransition("/signup");
                  }}
                  className="w-full text-center py-3 rounded-xl bg-white text-slate-950 hover:bg-slate-100 text-sm font-heading font-semibold shadow-md"
                >
                  Get Started
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
