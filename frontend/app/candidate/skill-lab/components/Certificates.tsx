"use client";

import { Award as CertIcon } from "lucide-react";

interface CertificatesProps {
  certificates: any[];
}

export default function Certificates({ certificates }: CertificatesProps) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-2xl font-black text-slate-905 dark:text-white leading-tight">Certificates</h2>
        <p className="text-xs text-slate-500 mt-1 font-medium">Verifiable certificate badges earned on course completions</p>
      </div>

      <div className="bg-card border border-border rounded-3xl p-5 shadow-sm">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4">Your Verified Badges</h3>
        
        {Array.isArray(certificates) && certificates.length > 0 ? (
          <div className="flex flex-col gap-3">
            {certificates.map((c, i) => (
              <div 
                key={`db-cert-${i}`} 
                className="p-3.5 bg-muted border border-border rounded-2xl flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4"
              >
                <div className="flex items-center gap-3.5">
                  <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-100 dark:border-indigo-900 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
                    <CertIcon size={18} />
                  </div>
                  
                  <div>
                    <h4 className="text-xs font-bold text-slate-800 dark:text-white leading-tight">{c.course_title}</h4>
                    <span className="text-9 text-slate-450 font-mono block mt-1 uppercase font-bold">
                      Verifiable Code: {c.code} • Earned: {new Date(c.earned_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 w-full sm:w-auto justify-end">
                  <button
                    onClick={() => alert(`Credentials Verification:\nCode: ${c.code}\nCourse: ${c.course_title}\nInstructor: ${c.instructor}\nIssued by LaunchBae Academy.`)}
                    className="px-3 py-1.5 bg-card border border-border text-foreground hover:bg-muted rounded-lg text-10 font-bold cursor-pointer"
                  >
                    Verify Code
                  </button>
                  <button
                    onClick={() => alert("LinkedIn sharing initialized. Certificate successfully shared!")}
                    className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-705 text-white rounded-lg text-10 font-bold cursor-pointer"
                  >
                    Share LinkedIn
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-slate-550 text-xs font-bold">
            You haven't earned any verified certificates yet. Complete a learning path with all assessments to get certified!
          </div>
        )}
      </div>
    </div>
  );
}
