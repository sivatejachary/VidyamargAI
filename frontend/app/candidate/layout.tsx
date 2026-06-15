"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import Sidebar from "@/components/Sidebar";

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
      <div className="min-h-screen bg-[#07070b] flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-4 border-t-purple-500 border-gray-800 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-app-bg flex flex-col md:flex-row transition-colors duration-300">
      <Sidebar portal="candidate" />
      <div className="flex-1 h-[calc(100vh-4rem)] md:h-screen overflow-y-auto bg-app-bg text-app-text transition-colors duration-300 font-sans mt-16 md:mt-0">
        {children}
      </div>
    </div>
  );
}
