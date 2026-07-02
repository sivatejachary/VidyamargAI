"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";

// Core modules and sections
import SmoothScroll from "@/components/landing/SmoothScroll";
import CanvasBackground from "@/components/landing/CanvasBackground";
import { PageTransitionProvider } from "@/components/landing/PageTransitionOverlay";
import Header from "@/components/landing/Header";
import Hero from "@/components/landing/Hero";
import TrustedMarquee from "@/components/landing/TrustedMarquee";
import Ecosystem from "@/components/landing/Ecosystem";
import WhyVidyaMarg from "@/components/landing/WhyVidyaMarg";
import Features from "@/components/landing/Features";
import PlatformScreenshots from "@/components/landing/PlatformScreenshots";
import DashboardPreview from "@/components/landing/DashboardPreview";
import HowItWorks from "@/components/landing/HowItWorks";
import Stats from "@/components/landing/Stats";
import Testimonials from "@/components/landing/Testimonials";
import Pricing from "@/components/landing/Pricing";
import CareerInsights from "@/components/landing/CareerInsights";
import FAQ from "@/components/landing/FAQ";
import FinalCTA from "@/components/landing/FinalCTA";
import Footer from "@/components/landing/Footer";

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, role, initialize } = useAuthStore();
  const [checkingAuth, setCheckingAuth] = useState(true);

  // Initialize and check active user session
  useEffect(() => {
    const checkSession = async () => {
      await initialize();
      setCheckingAuth(false);
    };
    checkSession();
  }, [initialize]);

  // Handle auto-redirection for active sessions
  useEffect(() => {
    if (!checkingAuth && isAuthenticated) {
      if (role === "admin" || role === "super_admin") {
        router.push("/admin");
      } else {
        router.push("/candidate");
      }
    }
  }, [isAuthenticated, role, router, checkingAuth]);

  // Prevent flashing landing page if user session is being validated
  if (checkingAuth) {
    return (
      <main className="min-h-screen bg-slate-950 flex flex-col items-center justify-center font-heading text-white">
        <div className="flex flex-col items-center gap-5">
          <div className="w-10 h-10 rounded-full border-2 border-purple-500 border-t-transparent animate-spin" />
          <span className="text-purple-400 font-medium tracking-wide">Connecting to VidyaMarg AI...</span>
        </div>
      </main>
    );
  }

  return (
    <PageTransitionProvider>
      <SmoothScroll>
        <main className="relative min-h-screen bg-slate-950 text-slate-100 overflow-x-hidden dark font-sans antialiased selection:bg-purple-500/30 selection:text-white">
          {/* Animated 6-layer background canvas */}
          <CanvasBackground />

          {/* Transparent sticky header */}
          <Header />

          {/* Section flow */}
          <div className="relative w-full">
            <Hero />
            
            <Ecosystem />
            
            <WhyVidyaMarg />
            
            <Features />
            
            <PlatformScreenshots />
            
            <DashboardPreview />
            
            <HowItWorks />
            
            <Stats />
            
            <Testimonials />
            
            <Pricing />
            
            <CareerInsights />
            
            <FAQ />
            
            <TrustedMarquee />
            
            <FinalCTA />
          </div>

          {/* Footnotes grid */}
          <Footer />
        </main>
      </SmoothScroll>
    </PageTransitionProvider>
  );
}
