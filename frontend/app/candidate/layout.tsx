"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import Sidebar from "@/components/Sidebar";
import HumanActionQueue from "@/components/HumanActionQueue";

export default function CandidateLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, role, initialize } = useAuthStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    initialize();
    setMounted(true);
  }, [initialize]);

  useEffect(() => {
    if (mounted && !isAuthenticated) {
      router.push("/");
    }
  }, [mounted, isAuthenticated, router]);

  if (!mounted || !isAuthenticated) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-4 border-t-primary border-muted animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-app-bg flex flex-col md:flex-row transition-colors duration-300">
      <Sidebar portal="candidate" />
      <main className="flex-1 h-[calc(100vh-4rem)] md:h-screen overflow-y-auto overflow-x-hidden bg-app-bg text-app-text transition-colors duration-300 font-sans mt-16 md:mt-0 pb-16 sm:pb-0">
        {children}
      </main>
      <HumanActionQueue />
    </div>
  );
}
