"use client";

import React, { useState, useEffect } from "react";
import { Sparkles, GraduationCap, Menu, X, Sun, Moon, Monitor } from "lucide-react";
import { usePageTransition } from "./PageTransitionOverlay";
import { motion, AnimatePresence } from "framer-motion";

export default function Header() {
  const { startTransition } = usePageTransition();
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  
  const [theme, setTheme] = useState<"light" | "dark" | "system">("system");
  const [themeDropdownOpen, setThemeDropdownOpen] = useState(false);

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

  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedTheme = (localStorage.getItem("theme") as "light" | "dark" | "system") || "system";
      setTheme(savedTheme);
    }
  }, []);

  const handleThemeChange = (newTheme: "light" | "dark" | "system") => {
    setTheme(newTheme);
    localStorage.setItem("theme", newTheme);
    
    const root = document.documentElement;
    if (newTheme === "dark") {
      root.classList.add("dark");
      root.classList.remove("light-theme");
    } else if (newTheme === "light") {
      root.classList.add("light-theme");
      root.classList.remove("dark");
    } else {
      const isDarkSystem = window.matchMedia("(prefers-color-scheme: dark)").matches;
      if (isDarkSystem) {
        root.classList.add("dark");
        root.classList.remove("light-theme");
      } else {
        root.classList.add("light-theme");
        root.classList.remove("dark");
      }
    }
    
    // Notify other components (like CanvasBackground)
    window.dispatchEvent(new Event("storage"));
    setThemeDropdownOpen(false);
  };

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
          ? "py-3 bg-background/80 backdrop-blur-xl border-border shadow-[0_4px_30px_rgba(0,0,0,0.05)] dark:shadow-[0_4px_30px_rgba(255,255,255,0.01)]"
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
          <span className="font-heading font-bold text-xl tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-slate-950 dark:from-white to-purple-600 dark:to-purple-400">
            VidyaMarg <span className="text-purple-600 dark:text-purple-400 font-extrabold text-xs ml-1 border border-purple-500/30 px-1.5 py-0.5 rounded bg-purple-500/10">AI</span>
          </span>
        </div>

        {/* DESKTOP NAV LINKS */}
        <nav className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <a
              key={link.name}
              href={link.href}
              onClick={(e) => handleScrollClick(e, link.href)}
              className="text-sm font-sans font-medium text-muted-foreground hover:text-foreground transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:outline-none rounded px-2 py-1"
            >
              {link.name}
            </a>
          ))}
        </nav>

        {/* DESKTOP CTAS */}
        <div className="hidden md:flex items-center gap-4">
          {/* Theme Dropdown */}
          <div className="relative">
            <button
              onClick={() => setThemeDropdownOpen(!themeDropdownOpen)}
              className="p-2.5 rounded-xl border border-slate-800 hover:border-slate-700 bg-slate-950/20 hover:bg-slate-900 text-slate-300 hover:text-white transition-colors duration-200 select-none clickable flex items-center justify-center"
              aria-label="Theme selector"
              aria-expanded={themeDropdownOpen}
            >
              {theme === "light" && <Sun className="w-4 h-4 text-amber-500" />}
              {theme === "dark" && <Moon className="w-4 h-4 text-purple-400" />}
              {theme === "system" && <Monitor className="w-4 h-4 text-slate-400" />}
            </button>
            <AnimatePresence>
              {themeDropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  transition={{ duration: 0.2 }}
                  className="absolute right-0 mt-2 w-32 rounded-xl border border-slate-800 bg-slate-950 p-1.5 shadow-xl z-50 text-left"
                >
                  <button
                    onClick={() => handleThemeChange("light")}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-heading font-bold text-slate-400 hover:text-white hover:bg-slate-905 transition-colors duration-150 cursor-pointer"
                  >
                    <Sun className="w-3.5 h-3.5 text-amber-500" />
                    <span>Light</span>
                  </button>
                  <button
                    onClick={() => handleThemeChange("dark")}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-heading font-bold text-slate-400 hover:text-white hover:bg-slate-905 transition-colors duration-150 cursor-pointer"
                  >
                    <Moon className="w-3.5 h-3.5 text-purple-400" />
                    <span>Dark</span>
                  </button>
                  <button
                    onClick={() => handleThemeChange("system")}
                    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-heading font-bold text-slate-400 hover:text-white hover:bg-slate-905 transition-colors duration-150 cursor-pointer"
                  >
                    <Monitor className="w-3.5 h-3.5 text-slate-400" />
                    <span>System</span>
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
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
            className="md:hidden bg-background/95 border-b border-border backdrop-blur-xl overflow-hidden"
          >
            <div className="px-6 py-8 flex flex-col gap-6">
              {navLinks.map((link) => (
                <a
                  key={link.name}
                  href={link.href}
                  onClick={(e) => handleScrollClick(e, link.href)}
                  className="text-base font-sans font-semibold text-muted-foreground hover:text-foreground transition-colors duration-200"
                >
                  {link.name}
                </a>
              ))}
               {/* Mobile Theme Selector Bar */}
              <div className="flex items-center justify-between bg-muted/50 p-1 rounded-xl border border-border mb-2">
                <button
                  onClick={() => handleThemeChange("light")}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-heading font-bold transition-all ${
                    theme === "light"
                      ? "bg-background text-foreground shadow-md border border-border"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Sun className="w-3.5 h-3.5 text-amber-500" />
                  <span>Light</span>
                </button>
                <button
                  onClick={() => handleThemeChange("dark")}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-heading font-bold transition-all ${
                    theme === "dark"
                      ? "bg-background text-foreground shadow-md border border-border"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Moon className="w-3.5 h-3.5 text-purple-400" />
                  <span>Dark</span>
                </button>
                <button
                  onClick={() => handleThemeChange("system")}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-heading font-bold transition-all ${
                    theme === "system"
                      ? "bg-background text-foreground shadow-md border border-border"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Monitor className="w-3.5 h-3.5 text-slate-400" />
                  <span>System</span>
                </button>
              </div>

              <div className="h-px bg-border my-2" />
              <div className="flex flex-col gap-4">
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    startTransition("/login");
                  }}
                  className="w-full text-center py-3 rounded-xl border border-border hover:border-border-hover text-muted-foreground hover:text-foreground text-sm font-heading font-semibold"
                >
                  Login
                </button>
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    startTransition("/signup");
                  }}
                  className="w-full text-center py-3 rounded-xl bg-foreground text-background hover:bg-foreground/90 text-sm font-heading font-semibold shadow-md"
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
