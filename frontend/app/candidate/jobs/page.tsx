"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function RedirectToJobAgentWorkspace() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/candidate/job-agent?tab=hr-jobs");
  }, [router]);

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0a0a0f", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ color: "#a78bfa", fontFamily: "Inter, sans-serif", fontSize: 16 }}>
        Redirecting to Jobs Workspace...
      </div>
    </div>
  );
}
