'use client';

import { useState, useEffect, useCallback } from 'react';

const HR_AGENT_BASE = 'https://nirvahai-production.up.railway.app';
const TENANT_SLUG = 'nirvah-ai';

const STAGE_ICONS: Record<number, string> = {
  1: '📄', 2: '📝', 3: '💻', 4: '🤖', 5: '🏆',
  6: '📞', 7: '👤', 8: '📞', 9: '🏢', 10: '📞',
  11: '📋', 12: '📞', 13: '🔍', 14: '📞', 15: '🎉',
};

const STAGE_NAMES: Record<number, string> = {
  1: 'Resume Screening', 2: 'MCQ Assessment', 3: 'Coding Assessment',
  4: 'AI Technical Interview', 5: 'Hackathon / Assignment',
  6: 'AI HR Call (Post-Technical)', 7: 'Technical Interview (Human)',
  8: 'AI HR Call (Post-Interview)', 9: 'HR / Hiring Manager Round',
  10: 'AI HR Call (Pre-Offer)', 11: 'Offer Letter',
  12: 'AI HR Call (Post-Offer)', 13: 'Background Verification',
  14: 'AI HR Call (BGV Update)', 15: 'Joining & Onboarding',
};

interface StageData {
  stage_number: number;
  stage_name: string;
  status: string;
  score: number | null;
  feedback: string | null;
  scheduled_at: string | null;
  completed_at: string | null;
}

interface ApplicationData {
  hr_application_id: string;
  hr_job_id: string;
  job_title: string;
  current_status: string;
  stages: StageData[];
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    PASSED: 'bg-emerald-500/20 border-emerald-400/40 text-emerald-400',
    FAILED: 'bg-rose-500/20 border-rose-400/40 text-rose-400',
    PENDING: 'bg-amber-500/20 border-amber-400/40 text-amber-400',
    SCHEDULED: 'bg-blue-500/20 border-blue-400/40 text-blue-400',
    IN_PROGRESS: 'bg-violet-500/20 border-violet-400/40 text-violet-400',
    LOCKED: 'bg-slate-800/50 border-white/5 text-slate-600',
    SKIPPED: 'bg-slate-600/20 border-slate-400/20 text-slate-500',
  };
  return (
    <span className={`rounded border px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${colors[status] || colors.LOCKED}`}>
      {status}
    </span>
  );
}

function PipelineGrid({ stages, applicationId }: { stages: StageData[]; applicationId: string }) {
  const allStages: StageData[] = Array.from({ length: 15 }, (_, i) => {
    const found = stages.find(s => s.stage_number === i + 1);
    return found || { stage_number: i + 1, stage_name: STAGE_NAMES[i + 1], status: 'LOCKED', score: null, feedback: null, scheduled_at: null, completed_at: null };
  });
  const passedCount = allStages.filter(s => s.status === 'PASSED').length;
  const progressPct = Math.round((passedCount / 15) * 100);
  return (
    <div>
      <div className="mb-4">
        <div className="flex justify-between text-xs mb-1.5">
          <span className="text-slate-400">{passedCount} of 15 stages completed</span>
          <span className="font-bold text-white">{progressPct}%</span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-slate-800">
          <div className="h-1.5 rounded-full bg-gradient-to-r from-violet-500 via-indigo-500 to-emerald-500 transition-all duration-700" style={{ width: `${progressPct}%` }} />
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {allStages.map(stage => {
          const isLocked = stage.status === 'LOCKED';
          const isPassed = stage.status === 'PASSED';
          const isFailed = stage.status === 'FAILED';
          const isPending = stage.status === 'PENDING';
          const borderColor = isPassed ? 'border-emerald-500/25 bg-emerald-500/5'
            : isFailed ? 'border-rose-500/25 bg-rose-500/5'
            : isPending ? 'border-amber-500/25 bg-amber-500/5'
            : 'border-white/5 bg-slate-900/30';
          return (
            <div key={stage.stage_number} className={`rounded-xl border p-3 transition-all duration-200 ${isLocked ? 'opacity-40' : ''} ${borderColor}`}>
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{isPassed ? '✅' : isFailed ? '❌' : isLocked ? '🔒' : STAGE_ICONS[stage.stage_number]}</span>
                  <div>
                    <p className="text-[10px] font-bold text-slate-500">Stage {stage.stage_number}</p>
                    <p className={`text-xs font-semibold leading-tight ${isLocked ? 'text-slate-600' : 'text-white'}`}>{stage.stage_name}</p>
                  </div>
                </div>
                <StatusBadge status={stage.status} />
              </div>
              {stage.score !== null && (
                <div className="flex items-center gap-2 mt-1.5">
                  <div className="h-1 flex-1 rounded-full bg-slate-800">
                    <div className={`h-1 rounded-full bg-gradient-to-r transition-all duration-700 ${
                      stage.score >= 70 ? 'from-emerald-500 to-emerald-400' :
                      stage.score >= 40 ? 'from-amber-500 to-amber-400' : 'from-rose-500 to-rose-400'
                    }`} style={{ width: `${Math.min(stage.score, 100)}%` }} />
                  </div>
                  <span className="text-xs font-bold text-white min-w-[32px] text-right">{stage.score.toFixed(0)}%</span>
                </div>
              )}
              {stage.scheduled_at && <p className="text-[10px] text-blue-400 mt-1.5">📅 {new Date(stage.scheduled_at).toLocaleString()}</p>}
              {stage.completed_at && <p className="text-[10px] text-slate-400 mt-1">✅ {new Date(stage.completed_at).toLocaleDateString()}</p>}
              {stage.feedback && <p className="text-[10px] text-slate-400 mt-2 leading-relaxed line-clamp-2">{stage.feedback}</p>}
              {isPending && stage.stage_number === 2 && (
                <a href={`/candidate/job-agent?tab=applications`} className="mt-2.5 flex items-center justify-center gap-1.5 w-full py-1.5 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-[11px] font-bold transition-all">
                  📝 Take MCQ Exam
                </a>
              )}
              {isPending && stage.stage_number === 3 && (
                <a href={`/candidate/job-agent?tab=applications`} className="mt-2.5 flex items-center justify-center gap-1.5 w-full py-1.5 rounded-lg bg-gradient-to-r from-fuchsia-600 to-violet-600 hover:from-fuchsia-500 hover:to-violet-500 text-white text-[11px] font-bold transition-all">
                  💻 Take Coding Exam
                </a>
              )}
              {isFailed && (
                <a href="/candidate/learning-loop" className="mt-2.5 flex items-center justify-center gap-1.5 w-full py-1.5 rounded-lg bg-gradient-to-r from-rose-600/80 to-orange-600/80 hover:from-rose-500 hover:to-orange-500 text-white text-[11px] font-bold transition-all">
                  📚 Get Personalized Coaching
                </a>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function AssessmentsPage() {
  const [applications, setApplications] = useState<ApplicationData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedApp, setExpandedApp] = useState<string | null>(null);
  const [candidateEmail, setCandidateEmail] = useState('');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    const email = typeof window !== 'undefined'
      ? (localStorage.getItem('candidate_applied_email') || localStorage.getItem('user_email') || '')
      : '';
    setCandidateEmail(email);
    if (!email) {
      setError('Please log in and apply to a job to see your assessment pipeline.');
      setLoading(false);
      return;
    }
    let apps: ApplicationData[] = [];
    try {
      const baseUrl = typeof window !== 'undefined' && !window.location.hostname.includes('localhost')
        ? 'https://vidyamargai-production-1fc2.up.railway.app/api/v1'
        : (process.env.NEXT_PUBLIC_API_URL || 'https://vidyamargai-production-1fc2.up.railway.app/api/v1');
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(`${baseUrl}/sync/stages/${encodeURIComponent(email)}`, { headers });
      if (res.ok) apps = await res.json();
    } catch (e) {
      console.warn('VidyamargAI sync failed, falling back to HR Agent direct');
    }
    if (apps.length === 0) {
      try {
        const res = await fetch(
          `${HR_AGENT_BASE}/api/v1/public/applications/status?email=${encodeURIComponent(email)}`,
          { headers: { 'X-Tenant-Slug': TENANT_SLUG } }
        );
        if (res.ok) {
          const rawApps = await res.json();
          apps = (Array.isArray(rawApps) ? rawApps : []).map((a: any) => ({
            hr_application_id: a.id || a.application_id || String(Math.random()),
            hr_job_id: a.job_id || '',
            job_title: a.job_title || 'Applied Position',
            current_status: a.status || 'APPLIED',
            stages: [
              { stage_number: 1, stage_name: 'Resume Screening', status: 'PASSED', score: a.fit_score || null, feedback: a.screening_feedback || null, scheduled_at: null, completed_at: a.created_at || null },
              { stage_number: 2, stage_name: 'MCQ Assessment', status: a.status === 'MCQ_STAGE' ? 'PENDING' : (a.status === 'CODING_STAGE' || a.status === 'INTERVIEW_STAGE' ? 'PASSED' : 'LOCKED'), score: null, feedback: null, scheduled_at: null, completed_at: null },
              { stage_number: 3, stage_name: 'Coding Assessment', status: a.status === 'CODING_STAGE' ? 'PENDING' : (a.status === 'INTERVIEW_STAGE' ? 'PASSED' : 'LOCKED'), score: null, feedback: null, scheduled_at: null, completed_at: null },
            ],
          }));
        }
      } catch (e) { console.error('HR Agent fallback failed:', e); }
    }
    setApplications(apps);
    if (apps.length > 0) setExpandedApp(apps[0].hr_application_id);
    setLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  return (
    <div className="min-h-screen bg-[#05060f] text-white">
      <div className="fixed inset-0 -z-10 bg-[radial-gradient(ellipse_at_top_left,_rgba(109,40,217,0.12),_transparent_50%),radial-gradient(ellipse_at_bottom_right,_rgba(16,185,129,0.07),_transparent_50%)]" />
      <div className="max-w-7xl mx-auto px-6 py-10">
        <div className="flex items-start justify-between mb-8">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600">
                <span className="text-xl">🎯</span>
              </div>
              <h1 className="text-2xl font-black text-white">Interview & Assessments</h1>
            </div>
            <p className="text-sm text-slate-400">Track your recruitment pipeline across all NirvahAI applications.</p>
            {candidateEmail && <p className="text-xs text-slate-500 mt-1">{candidateEmail}</p>}
          </div>
          <button onClick={loadData} className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-300 hover:bg-white/10 transition">
            ↻ Refresh
          </button>
        </div>
        {loading ? (
          <div className="flex flex-col items-center justify-center py-32 gap-4">
            <div className="w-12 h-12 border-4 border-violet-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-slate-400 text-sm">Loading your pipeline...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-24 gap-4 rounded-2xl border border-dashed border-rose-500/20 bg-rose-500/5">
            <span className="text-4xl">⚠️</span>
            <p className="text-rose-400 font-medium">{error}</p>
            <a href="/candidate/job-agent" className="text-sm text-violet-400 hover:text-violet-300 underline">Browse and apply to jobs →</a>
          </div>
        ) : applications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 gap-6 rounded-2xl border border-dashed border-white/10">
            <div className="text-6xl">🚀</div>
            <div className="text-center">
              <h2 className="text-xl font-bold text-white mb-2">No Active Applications</h2>
              <p className="text-slate-400 text-sm max-w-sm">Apply to NirvahAI jobs to start your journey and track your pipeline here.</p>
            </div>
            <a href="/candidate/job-agent?tab=feed" className="px-6 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-bold text-sm transition-all shadow-lg shadow-violet-500/20">
              Browse Jobs →
            </a>
          </div>
        ) : (
          <div className="space-y-6">
            {applications.map(app => {
              const isExpanded = expandedApp === app.hr_application_id;
              const passedCount = (app.stages || []).filter(s => s.status === 'PASSED').length;
              const progressPct = Math.round((passedCount / 15) * 100);
              const hasActive = (app.stages || []).some(s => s.status === 'PENDING' || s.status === 'SCHEDULED');
              return (
                <div key={app.hr_application_id} className={`rounded-2xl border transition-all duration-300 overflow-hidden ${
                  isExpanded ? 'border-violet-500/30 bg-violet-500/5 shadow-xl shadow-violet-500/10' : 'border-white/8 bg-white/2 hover:border-white/12'
                }`}>
                  <button onClick={() => setExpandedApp(isExpanded ? null : app.hr_application_id)} className="w-full text-left px-6 py-5">
                    <div className="flex items-center justify-between gap-4">
                      <div className="flex items-center gap-4">
                        <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500/20 to-indigo-500/30">
                          <span className="text-2xl">💼</span>
                        </div>
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <h2 className="text-base font-bold text-white">{app.job_title}</h2>
                            {hasActive && (
                              <span className="flex items-center gap-1 rounded-full bg-amber-500/20 border border-amber-500/30 px-2 py-0.5 text-[10px] font-bold text-amber-400">
                                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                                Action Required
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                            <span>Status: <span className="text-white font-medium">{app.current_status}</span></span>
                            <span>·</span>
                            <span>{passedCount}/15 stages passed</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="relative flex h-12 w-12 flex-shrink-0">
                          <svg className="h-12 w-12 -rotate-90" viewBox="0 0 36 36">
                            <circle cx="18" cy="18" r="15.5" fill="none" stroke="#1e1e2e" strokeWidth="3" />
                            <circle cx="18" cy="18" r="15.5" fill="none" stroke="#7c3aed" strokeWidth="3"
                              strokeDasharray={`${progressPct * 0.97} 100`} strokeLinecap="round" />
                          </svg>
                          <div className="absolute inset-0 flex items-center justify-center">
                            <span className="text-[10px] font-black text-white">{progressPct}%</span>
                          </div>
                        </div>
                        <span className={`text-slate-400 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}>▼</span>
                      </div>
                    </div>
                  </button>
                  {isExpanded && (
                    <div className="border-t border-white/5 px-6 pb-6 pt-4">
                      <PipelineGrid stages={app.stages || []} applicationId={app.hr_application_id} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
