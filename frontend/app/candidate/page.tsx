"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function CandidateDashboardRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.push("/candidate/chat");
  }, [router]);

  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
      <div className="w-8 h-8 rounded-full border-4 border-t-purple-500 border-gray-200 dark:border-gray-800 animate-spin" />
    </div>
  );
}
