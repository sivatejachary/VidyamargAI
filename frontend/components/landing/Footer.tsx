"use client";

import React, { useRef, useState } from "react";
import { GraduationCap, Sparkles, Mail, Phone, MapPin } from "lucide-react";
import { usePageTransition } from "./PageTransitionOverlay";

export default function Footer() {
  const { startTransition } = usePageTransition();
  const footerRef = useRef<HTMLElement>(null);
  const [mousePos, setMousePos] = useState({ x: -200, y: -200 });

  const handleMouseMove = (e: React.MouseEvent<HTMLElement>) => {
    if (!footerRef.current) return;
    const rect = footerRef.current.getBoundingClientRect();
    setMousePos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    });
  };

  const currentYear = new Date().getFullYear();

  return (
    <footer
      ref={footerRef}
      onMouseMove={handleMouseMove}
      className="relative border-t border-slate-900 bg-slate-950 py-16 overflow-hidden digital-grid-bg select-none"
    >
      {/* Mouse Light Spotlight Interaction */}
      <div
        className="absolute inset-0 pointer-events-none transition-opacity duration-300"
        style={{
          background: `radial-gradient(350px circle at ${mousePos.x}px ${mousePos.y}px, rgba(168, 85, 247, 0.05), transparent 80%)`
        }}
      />

      {/* Floating slow-moving background gradient blobs */}
      <div className="absolute bottom-0 right-0 w-80 h-80 bg-purple-600/3 rounded-full blur-[90px] pointer-events-none -z-10" />

      <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 md:grid-cols-12 gap-10 md:gap-8 relative z-10 text-left">
        
        {/* BRAND COLUMN (4 cols) */}
        <div className="md:col-span-4 flex flex-col items-start gap-4">
          <div
            onClick={() => startTransition("/")}
            className="flex items-center gap-2 cursor-pointer"
          >
            <div className="relative w-9 h-9 rounded-xl bg-gradient-to-br from-purple-600 to-blue-500 flex items-center justify-center shadow-lg animate-float-1">
              <GraduationCap className="w-4.5 h-4.5 text-white" />
              <Sparkles className="w-2.5 h-2.5 text-purple-200 absolute -top-0.5 -right-0.5" />
            </div>
            <span className="font-heading font-bold text-lg tracking-tight text-white">
              VidyaMarg <span className="text-purple-400 font-extrabold text-xs ml-0.5 border border-purple-500/20 px-1 py-0.5 rounded bg-purple-500/5">AI</span>
            </span>
          </div>
          <p className="font-sans text-xs text-slate-500 leading-relaxed max-w-sm">
            VidyaMarg AI is the most advanced, autonomous career-readiness and learning platform mapped to next-generation tech roles.
          </p>
          
          {/* Social Icons */}
          <div className="flex items-center gap-3 mt-2">
            <a href="#" className="p-2 rounded-lg bg-slate-900/60 border border-slate-800/80 hover:border-purple-500/30 hover:bg-slate-900 text-slate-500 hover:text-white transition-all clickable" aria-label="Github link">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
                <path d="M9 18c-4.51 2-5-2-7-2" />
              </svg>
            </a>
            <a href="#" className="p-2 rounded-lg bg-slate-900/60 border border-slate-800/80 hover:border-purple-500/30 hover:bg-slate-900 text-slate-500 hover:text-white transition-all clickable" aria-label="Twitter/X link">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 4s-.7 2.1-2 3.4c1.6 10-9.4 17.3-18 11.6 2.2.1 4.4-.6 6-2C3 15.5.5 9.6 3 5c2.2 2.6 5.6 4.1 9 4-.9-4.2 4-6.6 7-3.8 1.1 0 3-1.2 3-1.2z" />
              </svg>
            </a>
            <a href="#" className="p-2 rounded-lg bg-slate-900/60 border border-slate-800/80 hover:border-purple-500/30 hover:bg-slate-900 text-slate-500 hover:text-white transition-all clickable" aria-label="LinkedIn link">
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z" />
                <rect width="4" height="12" x="2" y="9" />
                <circle cx="4" cy="4" r="2" />
              </svg>
            </a>
          </div>
        </div>

        {/* ECOSYSTEM LINKS (2.5 cols) */}
        <div className="md:col-span-2.5 flex flex-col gap-3">
          <h4 className="font-heading font-extrabold text-xs uppercase tracking-widest text-slate-500">Platform</h4>
          <ul className="space-y-2">
            <li><a href="#ecosystem" className="text-xs font-sans text-slate-500 hover:text-slate-300 transition-colors">Career Ecosystem</a></li>
            <li><a href="#features" className="text-xs font-sans text-slate-500 hover:text-slate-300 transition-colors">Core Features</a></li>
            <li><a href="#preview" className="text-xs font-sans text-slate-500 hover:text-slate-300 transition-colors">Product Previews</a></li>
            <li><a href="#pricing" className="text-xs font-sans text-slate-500 hover:text-slate-300 transition-colors">Pricing Plans</a></li>
          </ul>
        </div>

        {/* GUIDES LINKS (2.5 cols) */}
        <div className="md:col-span-2.5 flex flex-col gap-3">
          <h4 className="font-heading font-extrabold text-xs uppercase tracking-widest text-slate-500">Resources</h4>
          <ul className="space-y-2">
            <li><a href="#" className="text-xs font-sans text-slate-500 hover:text-slate-300 transition-colors">ATS Templates</a></li>
            <li><a href="#" className="text-xs font-sans text-slate-500 hover:text-slate-300 transition-colors">Interview Banks</a></li>
            <li><a href="#" className="text-xs font-sans text-slate-500 hover:text-slate-300 transition-colors">Skill Syllabus</a></li>
            <li><a href="#" className="text-xs font-sans text-slate-500 hover:text-slate-300 transition-colors">Terms & Privacy</a></li>
          </ul>
        </div>

        {/* CONTACT INFO (3 cols) */}
        <div className="md:col-span-3 flex flex-col gap-3">
          <h4 className="font-heading font-extrabold text-xs uppercase tracking-widest text-slate-500">Get in Touch</h4>
          <ul className="space-y-2">
            <li className="flex items-center gap-2 text-xs font-sans text-slate-500">
              <Mail className="w-3.5 h-3.5 text-purple-400 shrink-0" />
              <span>support@vidyamargai.com</span>
            </li>
            <li className="flex items-center gap-2 text-xs font-sans text-slate-500">
              <Phone className="w-3.5 h-3.5 text-purple-400 shrink-0" />
              <span>+91 98765 43210</span>
            </li>
            <li className="flex items-center gap-2 text-xs font-sans text-slate-500">
              <MapPin className="w-3.5 h-3.5 text-purple-400 shrink-0" />
              <span>Telangana, India</span>
            </li>
          </ul>
        </div>

      </div>

      {/* Bottom Bar */}
      <div className="max-w-7xl mx-auto px-6 border-t border-slate-900/60 mt-12 pt-6 flex flex-col sm:flex-row items-center justify-between gap-4 z-10 relative">
        <p className="text-[10px] font-mono text-slate-600">
          &copy; {currentYear} VidyaMarg AI. All rights reserved. Mapped for Indian Tech Talent.
        </p>
        <div className="flex items-center gap-4 text-[10px] font-mono text-slate-600">
          <a href="#" className="hover:text-slate-400 transition-colors">Security</a>
          <a href="#" className="hover:text-slate-400 transition-colors">Privacy</a>
          <a href="#" className="hover:text-slate-400 transition-colors">Sitemap</a>
        </div>
      </div>
    </footer>
  );
}
