"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";
import Sidebar from "@/components/Sidebar";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { isAuthenticated, role, initialize } = useAuthStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    initialize();
    setMounted(true);
  }, [initialize]);

  useEffect(() => {
    if (mounted) {
      if (!isAuthenticated) {
        router.push("/");
      } else if (role !== "admin" && role !== "super_admin") {
        router.push("/candidate");
      }
    }
  }, [mounted, isAuthenticated, role, router]);

  if (!mounted || !isAuthenticated || (role !== "admin" && role !== "super_admin")) {
    return (
      <div className="min-h-screen bg-[#07070b] flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-4 border-t-purple-500 border-gray-800 animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-app-bg flex transition-colors duration-300">
      <Sidebar portal="admin" />
      <div className="flex-1 h-screen overflow-y-auto bg-app-bg text-app-text transition-colors duration-300 font-sans">
        {children}
      </div>
    </div>
  );
}
