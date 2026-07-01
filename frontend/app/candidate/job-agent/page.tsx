"use client";
/**
 * VidyaMarg AI — AI Job Agent Dashboard
 * Flagship feature: /candidate/job-agent
 *
 * Sections:
 *   1. Agent Overview (status bar + career DNA)
 *   2. Job Discovery Feed (real-time matches)
 *   3. Career Intelligence (paths + skill graph)
 *   4. Application Tracker (Kanban board)
 *   5. Skill Gap & Learning Roadmap
 *   6. Interview Preparation
 *   7. Market Intelligence
 *   8. Career Insights
 *   9. Notifications panel
 */

import React, { useState, useEffect, useCallback } from "react";
import { apiClient } from "@/services/api";
import AutonomousWorkflowVisualizer from "@/components/AutonomousWorkflowVisualizer";
import type {
  DashboardData,
  JobMatch,
  Application,
  SkillGap,
  CareerInsight,
  AgentNotification,
  InterviewPrep,
} from "@/types/jobAgent";

// ─────────────────────────────────────────────────────────────────────────────
// ICONS
// ─────────────────────────────────────────────────────────────────────────────

const Icon = {
  Bot: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-5 h-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1 1 .03 2.7-1.4 2.4l-4.9-1.1m-7.8-3.4L5 14.5m14.8.8-7.3-7.3" />
    </svg>
  ),
  Briefcase: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-5 h-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0" />
    </svg>
  ),
  Target: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-5 h-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
    </svg>
  ),
  Lightning: () => (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
      <path fillRule="evenodd" d="M14.615 1.595a.75.75 0 01.359.852L12.982 9.75h7.268a.75.75 0 01.548 1.262l-10.5 11.25a.75.75 0 01-1.272-.71l1.992-7.302H3.75a.75.75 0 01-.548-1.262l10.5-11.25a.75.75 0 01.913-.143z" clipRule="evenodd" />
    </svg>
  ),
  Bell: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-5 h-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
    </svg>
  ),
  Brain: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-5 h-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
    </svg>
  ),
  TrendingUp: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-5 h-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" />
    </svg>
  ),
  BookOpen: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-5 h-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
    </svg>
  ),
  Play: () => (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
      <path fillRule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.348c1.295.712 1.295 2.573 0 3.285L7.28 19.991c-1.25.687-2.779-.217-2.779-1.643V5.653z" clipRule="evenodd" />
    </svg>
  ),
  Check: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  ),
  X: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  Bookmark: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-4 h-4">
      <path strokeLinecap="round" strokeLinejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z" />
    </svg>
  ),
  Globe: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-4 h-4">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
    </svg>
  ),
};

// ─────────────────────────────────────────────────────────────────────────────
// UTILITY COMPONENTS
// ─────────────────────────────────────────────────────────────────────────────

function ScoreBadge({ score, size = "sm" }: { score: number; size?: "sm" | "lg" }) {
  const color =
    score >= 80 ? "from-emerald-500 to-green-400" :
    score >= 60 ? "from-violet-500 to-indigo-400" :
    score >= 40 ? "from-amber-500 to-yellow-400" :
    "from-red-500 to-rose-400";

  const sizeClass = size === "lg" ? "w-16 h-16 text-lg" : "w-10 h-10 text-xs";

  return (
    <div className={`${sizeClass} rounded-full bg-gradient-to-br ${color} flex items-center justify-center font-bold text-white shadow-lg flex-shrink-0`}>
      {Math.round(score)}
    </div>
  );
}

function SkillTag({ skill, variant = "default" }: { skill: string; variant?: "default" | "missing" | "highlight" }) {
  const classes = {
    default: "bg-violet-500/20 text-violet-300 border border-violet-500/30",
    missing: "bg-red-500/20 text-red-300 border border-red-500/30",
    highlight: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${classes[variant]}`}>{skill}</span>
  );
}

function SectionHeader({ icon, title, count, action }: { icon: React.ReactNode; title: string; count?: number; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        <span className="text-violet-400">{icon}</span>
        <h2 className="text-base font-semibold text-white">{title}</h2>
        {count !== undefined && (
          <span className="bg-violet-500/20 text-violet-300 text-xs font-medium px-2 py-0.5 rounded-full">{count}</span>
        )}
      </div>
      {action}
    </div>
  );
}

function LoadingPulse() {
  return (
    <div className="animate-pulse space-y-3">
      {[1, 2, 3].map(i => (
        <div key={i} className="h-24 bg-white/5 rounded-xl" />
      ))}
    </div>
  );
}

function AgentStatusPill({ status }: { status: string }) {
  const config: Record<string, { color: string; label: string; pulse?: boolean }> = {
    running: { color: "text-blue-400 bg-blue-500/20 border-blue-500/30", label: "Running", pulse: true },
    active: { color: "text-emerald-400 bg-emerald-500/20 border-emerald-500/30", label: "Active" },
    completed: { color: "text-green-400 bg-green-500/20 border-green-500/30", label: "Complete" },
    failed: { color: "text-red-400 bg-red-500/20 border-red-500/30", label: "Failed" },
    paused: { color: "text-amber-400 bg-amber-500/20 border-amber-500/30", label: "Paused" },
    not_initialized: { color: "text-slate-400 bg-slate-500/20 border-slate-500/30", label: "Not Started" },
  };
  const cfg = config[status] || config.active;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${cfg.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full bg-current ${cfg.pulse ? "animate-pulse" : ""}`} />
      {cfg.label}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// JOB CARD
// ─────────────────────────────────────────────────────────────────────────────

function JobCard({ job, onSave, onApply, onHide, onViewPrep, selected, onClick }: {
  job: JobMatch;
  onSave: (id: number) => void;
  onApply: (job: JobMatch) => void;
  onHide: (id: number) => void;
  onViewPrep: (job: JobMatch) => void;
  selected: boolean;
  onClick: () => void;
}) {
  const match = job.match;
  const score = match?.overall_score ?? 0;

  return (
    <div
      onClick={onClick}
      className={`group relative rounded-xl border transition-all duration-200 cursor-pointer p-4 ${
        selected
          ? "border-violet-500/60 bg-violet-500/10 shadow-violet-500/20 shadow-lg"
          : "border-white/10 bg-white/5 hover:border-violet-500/40 hover:bg-white/8"
      }`}
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        {/* Company avatar */}
        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-violet-500/30 to-indigo-500/30 flex items-center justify-center text-sm font-bold text-violet-300 border border-violet-500/20 flex-shrink-0">
          {job.company_name?.[0] || "?"}
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-white truncate">{job.title}</p>
          <p className="text-xs text-slate-400 truncate">{job.company_name}</p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            {job.is_remote && (
              <span className="text-xs text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">Remote</span>
            )}
            {job.location && !job.is_remote && (
              <span className="text-xs text-slate-400">{job.city || job.location}</span>
            )}
            {job.seniority && (
              <span className="text-xs text-slate-500 capitalize">{job.seniority}</span>
            )}
          </div>
        </div>

        {match && <ScoreBadge score={score} />}
      </div>

      {/* Skills */}
      {(job.required_skills?.length ?? 0) > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {job.required_skills.slice(0, 4).map(s => <SkillTag key={s} skill={s} />)}
          {job.required_skills.length > 4 && (
            <span className="text-xs text-slate-500">+{job.required_skills.length - 4}</span>
          )}
        </div>
      )}

      {/* Match reasons */}
      {match?.match_reasons?.[0] && (
        <p className="mt-2 text-xs text-slate-400 line-clamp-1">
          <span className="text-emerald-400">✓</span> {match.match_reasons[0]}
        </p>
      )}

      {/* Salary */}
      {(job.salary_min || job.salary_raw) && (
        <p className="mt-1 text-xs text-amber-400">
          {job.salary_raw || `${job.salary_currency} ${job.salary_min?.toLocaleString()}${job.salary_max ? `–${job.salary_max.toLocaleString()}` : "+"}`}
        </p>
      )}

      {/* Actions */}
      <div className="mt-3 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={e => { e.stopPropagation(); onApply(job); }}
          className="flex-1 bg-violet-600 hover:bg-violet-500 text-white text-xs font-medium py-1.5 rounded-lg transition-colors"
        >
          Apply
        </button>
        <button
          onClick={e => { e.stopPropagation(); onSave(job.id); }}
          className={`p-1.5 rounded-lg border transition-colors ${match?.is_saved ? "bg-amber-500/20 border-amber-500/30 text-amber-400" : "border-white/10 text-slate-400 hover:text-white"}`}
        >
          <Icon.Bookmark />
        </button>
        <button
          onClick={e => { e.stopPropagation(); onViewPrep(job); }}
          className="p-1.5 rounded-lg border border-white/10 text-slate-400 hover:text-violet-400 transition-colors"
          title="Interview Prep"
        >
          <Icon.BookOpen />
        </button>
        <button
          onClick={e => { e.stopPropagation(); onHide(job.id); }}
          className="p-1.5 rounded-lg border border-white/10 text-slate-500 hover:text-red-400 transition-colors"
        >
          <Icon.X />
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// APPLICATION KANBAN
// ─────────────────────────────────────────────────────────────────────────────

const APP_STATUSES = [
  { key: "saved", label: "Saved", color: "border-slate-500/30 bg-slate-500/10", dot: "bg-slate-400" },
  { key: "applied", label: "Applied", color: "border-blue-500/30 bg-blue-500/10", dot: "bg-blue-400" },
  { key: "interview_scheduled", label: "Interview", color: "border-violet-500/30 bg-violet-500/10", dot: "bg-violet-400" },
  { key: "offer_received", label: "Offer", color: "border-emerald-500/30 bg-emerald-500/10", dot: "bg-emerald-400" },
  { key: "rejected", label: "Rejected", color: "border-red-500/30 bg-red-500/10", dot: "bg-red-400" },
];

function KanbanBoard({ applications, onStatusChange }: {
  applications: Application[];
  onStatusChange: (appId: number, status: string) => void;
}) {
  return (
    <div className="grid grid-cols-5 gap-3 min-w-[900px]">
      {APP_STATUSES.map(col => {
        const apps = applications.filter(a => a.status === col.key);
        return (
          <div key={col.key} className={`rounded-xl border ${col.color} p-3`}>
            <div className="flex items-center gap-2 mb-3">
              <span className={`w-2 h-2 rounded-full ${col.dot}`} />
              <span className="text-xs font-semibold text-white">{col.label}</span>
              <span className="ml-auto text-xs text-slate-400 bg-white/5 px-1.5 py-0.5 rounded">{apps.length}</span>
            </div>
            <div className="space-y-2">
              {apps.map(app => (
                <div key={app.id} className="bg-white/5 rounded-lg p-2.5 border border-white/5">
                  <p className="text-xs font-medium text-white truncate">{app.job_title}</p>
                  <p className="text-xs text-slate-400 truncate">{app.company_name}</p>
                  {app.applied_at && (
                    <p className="text-xs text-slate-500 mt-1">{new Date(app.applied_at).toLocaleDateString()}</p>
                  )}
                </div>
              ))}
              {apps.length === 0 && (
                <p className="text-xs text-slate-500 text-center py-4">No applications</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SKILL GRAPH VISUALIZATION
// ─────────────────────────────────────────────────────────────────────────────

function SkillGraph({ skillGraph }: { skillGraph: Record<string, any> }) {
  const skills = Object.entries(skillGraph || {}).slice(0, 20);
  const levelOrder = { expert: 4, advanced: 3, intermediate: 2, beginner: 1 };
  const sorted = skills.sort(([, a], [, b]) => (levelOrder[b.level as keyof typeof levelOrder] || 0) - (levelOrder[a.level as keyof typeof levelOrder] || 0));

  const levelColors: Record<string, string> = {
    expert: "from-violet-500 to-purple-400",
    advanced: "from-blue-500 to-indigo-400",
    intermediate: "from-teal-500 to-cyan-400",
    beginner: "from-slate-400 to-slate-500",
  };

  const demandColors: Record<string, string> = {
    high: "text-emerald-400",
    medium: "text-amber-400",
    low: "text-slate-400",
  };

  return (
    <div className="space-y-2">
      {sorted.map(([skill, data]) => (
        <div key={skill} className="flex items-center gap-3">
          <div className="w-32 text-xs text-slate-300 truncate">{skill}</div>
          <div className="flex-1 bg-white/5 rounded-full h-2 overflow-hidden">
            <div
              className={`h-full rounded-full bg-gradient-to-r ${levelColors[data.level] || levelColors.beginner}`}
              style={{ width: `${(levelOrder[data.level as keyof typeof levelOrder] || 1) * 25}%` }}
            />
          </div>
          <div className="w-20 flex items-center gap-1">
            <span className="text-xs text-slate-400 capitalize">{data.level}</span>
            {data.demand && (
              <span className={`text-xs ${demandColors[data.demand]}`}>• {data.demand}</span>
            )}
          </div>
        </div>
      ))}
      {skills.length === 0 && (
        <p className="text-slate-500 text-sm">No skill graph data yet. Run the agent to generate.</p>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// CAREER PATH GRAPH
// ─────────────────────────────────────────────────────────────────────────────

function CareerPathCard({ path }: { path: any }) {
  const stageColors: Record<string, string> = {
    current: "bg-violet-500 border-violet-400",
    next: "bg-blue-500/80 border-blue-400",
    growth: "bg-teal-500/60 border-teal-400",
    leadership: "bg-amber-500/50 border-amber-400",
  };

  return (
    <div className="bg-white/5 rounded-xl border border-white/10 p-4">
      <div className="flex items-center gap-2 mb-4">
        <span className={`text-xs px-2 py-0.5 rounded-full border ${
          path.path_type === "vertical" ? "text-violet-300 bg-violet-500/20 border-violet-500/30" :
          path.path_type === "leadership" ? "text-amber-300 bg-amber-500/20 border-amber-500/30" :
          "text-teal-300 bg-teal-500/20 border-teal-500/30"
        }`}>{path.path_type}</span>
        <h3 className="text-sm font-semibold text-white">{path.path_name}</h3>
      </div>

      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {(path.roles || []).map((role: any, idx: number) => (
          <React.Fragment key={idx}>
            <div className="flex-shrink-0 text-center">
              <div className={`${stageColors[role.stage] || stageColors.current} border rounded-lg px-3 py-2 mb-1`}>
                <p className="text-xs font-medium text-white whitespace-nowrap">{role.title}</p>
              </div>
              <p className="text-xs text-slate-500">{role.timeline}</p>
              {role.match_score && (
                <p className="text-xs text-violet-400">{role.match_score}%</p>
              )}
            </div>
            {idx < (path.roles || []).length - 1 && (
              <div className="flex-shrink-0 text-slate-600">→</div>
            )}
          </React.Fragment>
        ))}
      </div>

      {(path.required_skills_to_progress?.length ?? 0) > 0 && (
        <div className="mt-3">
          <p className="text-xs text-slate-400 mb-1">Skills to progress:</p>
          <div className="flex flex-wrap gap-1">
            {path.required_skills_to_progress.slice(0, 5).map((s: string) => (
              <SkillTag key={s} skill={s} variant="missing" />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// INTERVIEW PREP PANEL
// ─────────────────────────────────────────────────────────────────────────────

function InterviewPrepPanel({ prep }: { prep: InterviewPrep }) {
  const [activeTab, setActiveTab] = useState<"technical" | "hr" | "behavioral" | "study">("technical");

  if (prep.status === "generating") {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="w-16 h-16 rounded-full border-4 border-violet-500 border-t-transparent animate-spin mb-4" />
        <p className="text-slate-400 text-sm">Generating interview preparation...</p>
        <p className="text-slate-500 text-xs mt-1">This takes about 30 seconds</p>
      </div>
    );
  }

  const tabs = [
    { id: "technical" as const, label: "Technical", count: prep.technical_questions?.length },
    { id: "hr" as const, label: "HR", count: prep.hr_questions?.length },
    { id: "behavioral" as const, label: "Behavioral", count: prep.behavioral_questions?.length },
    { id: "study" as const, label: "Study Topics", count: prep.study_topics?.length },
  ];

  return (
    <div>
      <div className="mb-4">
        <h3 className="text-base font-semibold text-white">{prep.job_title}</h3>
        <p className="text-sm text-slate-400">{prep.company_name}</p>
        <div className="flex items-center gap-3 mt-2">
          {prep.estimated_prep_hours && (
            <span className="text-xs text-amber-400">⏱ {prep.estimated_prep_hours}h prep</span>
          )}
          {prep.difficulty_level && (
            <span className={`text-xs capitalize ${prep.difficulty_level === "hard" ? "text-red-400" : prep.difficulty_level === "medium" ? "text-amber-400" : "text-green-400"}`}>
              {prep.difficulty_level} difficulty
            </span>
          )}
        </div>
      </div>

      {/* Company Analysis */}
      {prep.company_analysis?.overview && (
        <div className="bg-violet-500/10 border border-violet-500/20 rounded-xl p-4 mb-4">
          <p className="text-xs font-semibold text-violet-300 mb-1">Company Overview</p>
          <p className="text-xs text-slate-300">{prep.company_analysis.overview}</p>
          {prep.company_analysis.interview_style && (
            <p className="text-xs text-slate-400 mt-2"><span className="text-violet-400">Interview style:</span> {prep.company_analysis.interview_style}</p>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-4 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              activeTab === tab.id
                ? "bg-violet-600 text-white"
                : "text-slate-400 hover:text-white bg-white/5"
            }`}
          >
            {tab.label} {tab.count ? `(${tab.count})` : ""}
          </button>
        ))}
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {activeTab === "technical" && (prep.technical_questions || []).map((q, i) => (
          <div key={i} className="bg-white/5 rounded-lg p-3 border border-white/5">
            <p className="text-sm font-medium text-white">{q.question}</p>
            {q.hint && <p className="text-xs text-slate-400 mt-1">💡 {q.hint}</p>}
            {q.topic && <span className="text-xs text-violet-400 mt-1 inline-block">#{q.topic}</span>}
          </div>
        ))}
        {activeTab === "hr" && (prep.hr_questions || []).map((q, i) => (
          <div key={i} className="bg-white/5 rounded-lg p-3 border border-white/5">
            <p className="text-sm font-medium text-white">{q.question}</p>
            {q.ideal_answer_structure && <p className="text-xs text-slate-400 mt-1">{q.ideal_answer_structure}</p>}
          </div>
        ))}
        {activeTab === "behavioral" && (prep.behavioral_questions || []).map((q, i) => (
          <div key={i} className="bg-white/5 rounded-lg p-3 border border-white/5">
            <p className="text-sm font-medium text-white">{q.question}</p>
            {q.star_framework && (
              <div className="mt-2 grid grid-cols-2 gap-2">
                {Object.entries(q.star_framework).map(([k, v]) => (
                  <div key={k} className="bg-white/5 rounded-lg p-2">
                    <p className="text-xs font-medium text-violet-400 capitalize">{k}</p>
                    <p className="text-xs text-slate-400">{v as string}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {activeTab === "study" && (prep.study_topics || []).map((t, i) => (
          <div key={i} className="flex items-start gap-3 bg-white/5 rounded-lg p-3 border border-white/5">
            <span className={`text-xs px-2 py-0.5 rounded border flex-shrink-0 ${t.importance === "critical" ? "text-red-300 bg-red-500/20 border-red-500/30" : t.importance === "high" ? "text-amber-300 bg-amber-500/20 border-amber-500/30" : "text-slate-300 bg-slate-500/20 border-slate-500/30"}`}>
              {t.importance}
            </span>
            <div>
              <p className="text-sm text-white">{t.topic}</p>
              <p className="text-xs text-slate-500">{t.estimated_hours}h</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN PAGE
// ─────────────────────────────────────────────────────────────────────────────

type TabId = "feed" | "career" | "applications" | "skills" | "interview" | "market" | "insights";

export default function JobAgentPage() {
  const [activeTab, setActiveTab] = useState<TabId>("feed");
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [jobs, setJobs] = useState<JobMatch[]>([]);
  const [selectedJob, setSelectedJob] = useState<JobMatch | null>(null);
  const [jobDetail, setJobDetail] = useState<JobMatch | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [skillGap, setSkillGap] = useState<SkillGap | null>(null);
  const [interviewPrep, setInterviewPrep] = useState<InterviewPrep | null>(null);
  const [insights, setInsights] = useState<CareerInsight[]>([]);
  const [notifications, setNotifications] = useState<AgentNotification[]>([]);
  const [agentInitialized, setAgentInitialized] = useState(false);
  const [loading, setLoading] = useState(true);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [initializing, setInitializing] = useState(false);
  const [runningAgent, setRunningAgent] = useState(false);
  const [jobPage, setJobPage] = useState(1);
  const [jobTotal, setJobTotal] = useState(0);
  const [careerData, setCareerData] = useState<any>(null);
  const [showNotifications, setShowNotifications] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [fastMode, setFastMode] = useState(false);

  // Load dashboard
  const loadDashboard = useCallback(async () => {
    try {
      const status = await apiClient.getAgentStatus();
      if (status?.initialized) {
        setAgentInitialized(true);
        const data = await apiClient.getJobAgentDashboard();
        setDashboard(data);
        setInsights(data.career_insights || []);
        setNotifications(data.notifications || []);
      } else {
        setAgentInitialized(false);
      }
    } catch (e: any) {
      setErrorMsg(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load jobs feed
  const loadJobs = useCallback(async (page = 1) => {
    setJobsLoading(true);
    try {
      const data = await apiClient.getJobFeed({ page, page_size: 20 });
      setJobs(page === 1 ? data.jobs : prev => [...prev, ...data.jobs]);
      setJobTotal(data.total);
      setJobPage(page);
    } catch (e: any) {
      console.error("Jobs load error:", e);
    } finally {
      setJobsLoading(false);
    }
  }, []);

  // Load section data on tab change
  const loadTabData = useCallback(async (tab: TabId) => {
    try {
      if (tab === "applications") {
        const data = await apiClient.getApplications();
        setApplications(data.applications || []);
      } else if (tab === "skills") {
        const data = await apiClient.getSkillGaps();
        setSkillGap(data);
      } else if (tab === "career") {
        const data = await apiClient.getJobAgentCareerPaths();
        setCareerData(data);
      } else if (tab === "insights" || tab === "market") {
        const data = await apiClient.getCareerInsights();
        setInsights(data?.insights || []);
      }
    } catch (e) {
      console.error("Tab data load error:", e);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    if (agentInitialized && activeTab === "feed") {
      loadJobs(1);
    } else if (agentInitialized) {
      loadTabData(activeTab);
    }
  }, [activeTab, agentInitialized, loadJobs, loadTabData]);

  // Initialize agent
  const handleInitialize = async () => {
    setInitializing(true);
    setErrorMsg(null);
    try {
      await apiClient.initializeJobAgent();
      setAgentInitialized(true);
      await loadDashboard();
      await loadJobs(1);
    } catch (e: any) {
      setErrorMsg(e.message);
    } finally {
      setInitializing(false);
    }
  };

  // Trigger agent run
  const handleRunAgent = async () => {
    setRunningAgent(true);
    try {
      await apiClient.triggerAgentRun("full", fastMode);
      setTimeout(() => {
        loadDashboard();
        loadJobs(1);
        setRunningAgent(false);
      }, 2000);
    } catch (e: any) {
      setErrorMsg(e.message);
      setRunningAgent(false);
    }
  };

  // Job actions
  const handleSaveJob = async (jobId: number) => {
    await apiClient.reactToJob(jobId, "saved");
    setJobs(prev => prev.map(j => j.id === jobId ? { ...j, match: { ...j.match!, is_saved: true } } : j));
  };

  const handleHideJob = async (jobId: number) => {
    await apiClient.reactToJob(jobId, "hidden");
    setJobs(prev => prev.filter(j => j.id !== jobId));
  };

  const handleApplyJob = async (job: JobMatch) => {
    try {
      await apiClient.createApplication({ job_id: job.id, status: "applied" });
      setJobs(prev => prev.map(j => j.id === job.id ? { ...j, application: { id: 0, status: "applied" } } : j));
      if (job.apply_url) window.open(job.apply_url, "_blank");
    } catch (e) {
      if (job.apply_url) window.open(job.apply_url, "_blank");
    }
  };

  const handleViewInterviewPrep = async (job: JobMatch) => {
    setSelectedJob(job);
    setActiveTab("interview");
    setInterviewPrep(null);
    try {
      const data = await apiClient.getInterviewPrep(job.id);
      setInterviewPrep(data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSelectJob = async (job: JobMatch) => {
    setSelectedJob(job);
    try {
      const detail = await apiClient.getJobDetail(job.id);
      setJobDetail(detail);
    } catch (e) {
      setJobDetail(job as any);
    }
  };

  const handleAppStatusChange = async (appId: number, newStatus: string) => {
    await apiClient.updateApplication(appId, { status: newStatus });
    setApplications(prev => prev.map(a => a.id === appId ? { ...a, status: newStatus } : a));
  };

  const handleMarkAllRead = async () => {
    await apiClient.markAllNotificationsRead();
    setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
  };

  // ── TAB DEFINITIONS ──────────────────────────────────────────────────────
  const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: "feed", label: "Job Feed", icon: <Icon.Briefcase /> },
    { id: "career", label: "Career Intel", icon: <Icon.Brain /> },
    { id: "applications", label: "Applications", icon: <Icon.Check /> },
    { id: "skills", label: "Skill Gaps", icon: <Icon.Target /> },
    { id: "interview", label: "Interview Prep", icon: <Icon.BookOpen /> },
    { id: "market", label: "Market Intel", icon: <Icon.TrendingUp /> },
    { id: "insights", label: "Insights", icon: <Icon.Lightning /> },
  ];

  const unreadCount = notifications.filter(n => !n.is_read).length;

  // ── NOT INITIALIZED STATE ─────────────────────────────────────────────────
  if (!loading && !agentInitialized) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center p-6">
        <div className="max-w-lg w-full text-center">
          <div className="w-24 h-24 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center shadow-2xl shadow-violet-500/30">
            <span className="text-white scale-150"><Icon.Bot /></span>
          </div>
          <h1 className="text-3xl font-bold text-white mb-3">AI Job Agent</h1>
          <p className="text-slate-400 mb-8 leading-relaxed">
            Your personal AI career assistant — discovers jobs 24/7, scores matches,
            identifies skill gaps, and prepares you for interviews. All automatically.
          </p>
          <div className="grid grid-cols-2 gap-3 mb-8 text-left">
            {[
              { icon: "🔍", title: "Continuous Discovery", desc: "Scans 100s of job sources automatically" },
              { icon: "🎯", title: "Smart Matching", desc: "Scores every job against your profile" },
              { icon: "📈", title: "Career Planning", desc: "Maps your growth trajectory" },
              { icon: "🎤", title: "Interview Prep", desc: "Generates prep guides per company" },
            ].map(f => (
              <div key={f.title} className="bg-white/5 rounded-xl p-4 border border-white/10">
                <div className="text-2xl mb-2">{f.icon}</div>
                <p className="text-sm font-semibold text-white">{f.title}</p>
                <p className="text-xs text-slate-400 mt-1">{f.desc}</p>
              </div>
            ))}
          </div>
          {errorMsg && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl p-3 mb-4 text-sm">{errorMsg}</div>
          )}
          <button
            id="initialize-agent-btn"
            onClick={handleInitialize}
            disabled={initializing}
            className="w-full bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 disabled:opacity-50 text-white font-semibold py-4 rounded-xl transition-all shadow-xl shadow-violet-500/30 flex items-center justify-center gap-2"
          >
            {initializing ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Initializing Agent...
              </>
            ) : (
              <>
                <Icon.Bot />
                Activate AI Job Agent
              </>
            )}
          </button>
          <p className="text-xs text-slate-500 mt-3">First run takes 1-2 minutes to analyze your profile</p>
        </div>
      </div>
    );
  }

  // ── LOADING ───────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-violet-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-slate-400 text-sm">Loading AI Job Agent...</p>
        </div>
      </div>
    );
  }

  const agent = dashboard?.agent;
  const careerDNA = agent?.career_dna || {};

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      {/* ── HEADER ─────────────────────────────────────────────────────── */}
      <div className="border-b border-white/10 bg-[#0a0a0f]/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center gap-4">
          {/* Agent Status */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-500/30">
              <Icon.Bot />
            </div>
            <div>
              <p className="text-sm font-semibold text-white">AI Job Agent</p>
              <div className="flex items-center gap-2">
                <AgentStatusPill status={dashboard?.last_run?.status || agent?.status || "active"} />
              </div>
            </div>
          </div>

          {/* Stats pills */}
          <div className="hidden md:flex items-center gap-2 ml-2">
            {[
              { label: "Discovered", value: agent?.total_jobs_discovered || 0, color: "text-blue-400" },
              { label: "Matched", value: dashboard?.total_matches || 0, color: "text-violet-400" },
              { label: "New", value: dashboard?.new_matches || 0, color: "text-emerald-400" },
              { label: "Applied", value: dashboard?.applications_summary?.applied || 0, color: "text-amber-400" },
            ].map(s => (
              <div key={s.label} className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 flex items-center gap-2">
                <span className={`text-sm font-bold ${s.color}`}>{s.value.toLocaleString()}</span>
                <span className="text-xs text-slate-400">{s.label}</span>
              </div>
            ))}
          </div>

          {/* Career DNA pill */}
          {careerDNA.archetype && (
            <div className="hidden lg:flex items-center gap-2 ml-auto bg-violet-500/10 border border-violet-500/20 rounded-lg px-3 py-1.5">
              <span className="text-xs text-violet-400">🧬 {careerDNA.archetype}</span>
            </div>
          )}

          <div className="flex items-center gap-3 ml-auto">
            {/* Fast Mode Toggle */}
            <label className="flex items-center gap-2 text-xs select-none cursor-pointer bg-white/5 border border-white/10 rounded-lg py-1.5 px-3 hover:bg-white/10 transition-colors">
              <input
                type="checkbox"
                checked={fastMode}
                onChange={(e) => setFastMode(e.target.checked)}
                className="rounded border-slate-700 bg-slate-900 text-violet-600 focus:ring-violet-500"
              />
              <span className="font-medium text-slate-300">⚡ Instant Mode</span>
            </label>

            {/* Refresh agent */}
            <button
              id="run-agent-btn"
              onClick={handleRunAgent}
              disabled={runningAgent}
              className="flex items-center gap-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-xs font-medium px-3 py-2 rounded-lg transition-colors"
            >
              {runningAgent ? (
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : <Icon.Play />}
              {runningAgent ? "Running..." : "Run Agent"}
            </button>

            {/* Notifications */}
            <div className="relative">
              <button
                id="notifications-btn"
                onClick={() => setShowNotifications(!showNotifications)}
                className="relative p-2 text-slate-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg transition-colors border border-white/10"
              >
                <Icon.Bell />
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 bg-violet-500 text-white text-xs rounded-full flex items-center justify-center font-bold">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </button>

              {/* Notifications dropdown */}
              {showNotifications && (
                <div className="absolute right-0 top-10 w-80 bg-[#13131a] border border-white/10 rounded-xl shadow-2xl z-50 overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
                    <p className="text-sm font-semibold text-white">Notifications</p>
                    {unreadCount > 0 && (
                      <button onClick={handleMarkAllRead} className="text-xs text-violet-400 hover:text-violet-300">
                        Mark all read
                      </button>
                    )}
                  </div>
                  <div className="max-h-80 overflow-y-auto">
                    {notifications.length === 0 ? (
                      <p className="text-slate-500 text-sm p-4 text-center">No notifications</p>
                    ) : notifications.map(n => (
                      <div key={n.id} className={`px-4 py-3 border-b border-white/5 ${!n.is_read ? "bg-violet-500/5" : ""}`}>
                        <p className="text-xs font-medium text-white">{n.title}</p>
                        <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">{n.body}</p>
                        <p className="text-xs text-slate-600 mt-1">
                          {n.created_at ? new Date(n.created_at).toLocaleDateString() : ""}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="max-w-[1600px] mx-auto px-6 flex gap-1 overflow-x-auto">
          {TABS.map(tab => (
            <button
              key={tab.id}
              id={`tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium whitespace-nowrap border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-violet-500 text-violet-400"
                  : "border-transparent text-slate-400 hover:text-white"
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── MAIN CONTENT ───────────────────────────────────────────────── */}
      <div className="max-w-[1600px] mx-auto px-6 py-6">
        {errorMsg && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl p-3 mb-4 text-sm flex items-center justify-between">
            {errorMsg}
            <button onClick={() => setErrorMsg(null)} className="text-red-400 hover:text-red-300"><Icon.X /></button>
          </div>
        )}

        {/* ── JOB FEED TAB ─────────────────────────────────────────────── */}
        {activeTab === "feed" && (
          <div className="grid grid-cols-12 gap-6">
            {/* Left: Job list */}
            <div className="col-span-12 lg:col-span-4 xl:col-span-3">
              <SectionHeader
                icon={<Icon.Briefcase />}
                title="Job Matches"
                count={jobTotal}
                action={
                  <select className="bg-white/5 border border-white/10 text-xs text-slate-400 rounded-lg px-2 py-1">
                    <option value="">All Jobs</option>
                    <option value="remote">Remote Only</option>
                    <option value="senior">Senior+</option>
                  </select>
                }
              />

              {jobsLoading && jobs.length === 0 ? (
                <LoadingPulse />
              ) : jobs.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-slate-400 text-sm">No matches yet</p>
                  <p className="text-slate-500 text-xs mt-1">Run the agent to discover jobs</p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[calc(100vh-200px)] overflow-y-auto pr-1">
                  {jobs.map(job => (
                    <JobCard
                      key={job.id}
                      job={job}
                      selected={selectedJob?.id === job.id}
                      onClick={() => handleSelectJob(job)}
                      onSave={handleSaveJob}
                      onApply={handleApplyJob}
                      onHide={handleHideJob}
                      onViewPrep={handleViewInterviewPrep}
                    />
                  ))}
                  {jobs.length < jobTotal && (
                    <button
                      onClick={() => loadJobs(jobPage + 1)}
                      disabled={jobsLoading}
                      className="w-full py-2 text-xs text-slate-400 hover:text-violet-400 bg-white/5 rounded-xl border border-white/10 transition-colors"
                    >
                      {jobsLoading ? "Loading..." : `Load more (${jobTotal - jobs.length} remaining)`}
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Center: Job detail */}
            <div className="col-span-12 lg:col-span-5 xl:col-span-6">
              {selectedJob ? (
                <div className="bg-white/5 rounded-xl border border-white/10 p-6 sticky top-28">
                  <div className="flex items-start gap-4 mb-4">
                    <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-violet-500/30 to-indigo-500/30 flex items-center justify-center text-xl font-bold text-violet-300 border border-violet-500/20">
                      {selectedJob.company_name?.[0] || "?"}
                    </div>
                    <div className="flex-1">
                      <h2 className="text-lg font-bold text-white">{selectedJob.title}</h2>
                      <p className="text-slate-400">{selectedJob.company_name}</p>
                      <div className="flex items-center gap-2 mt-1 flex-wrap">
                        <span className="text-xs text-slate-400">{selectedJob.location || (selectedJob.is_remote ? "Remote" : "")}</span>
                        {selectedJob.seniority && <span className="text-xs text-slate-500 capitalize">• {selectedJob.seniority}</span>}
                        {selectedJob.industry && <span className="text-xs text-slate-500">• {selectedJob.industry}</span>}
                      </div>
                    </div>
                    {selectedJob.match && <ScoreBadge score={selectedJob.match.overall_score} size="lg" />}
                  </div>

                  {/* Score breakdown */}
                  {selectedJob.match && (
                    <div className="grid grid-cols-3 gap-2 mb-4">
                      {[
                        { label: "Skills", score: selectedJob.match.skill_score },
                        { label: "Experience", score: selectedJob.match.experience_score },
                        { label: "Location", score: selectedJob.match.location_score },
                      ].map(s => (
                        <div key={s.label} className="bg-white/5 rounded-lg p-2 text-center">
                          <p className="text-xs text-slate-400">{s.label}</p>
                          <p className="text-sm font-bold text-white">{Math.round(s.score)}%</p>
                          <div className="mt-1 bg-white/5 rounded-full h-1">
                            <div className="bg-violet-500 h-full rounded-full" style={{ width: `${s.score}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Match reasons */}
                  {(selectedJob.match?.match_reasons?.length ?? 0) > 0 && (
                    <div className="mb-4">
                      <p className="text-xs font-semibold text-slate-400 mb-2">WHY THIS MATCHES</p>
                      {selectedJob.match?.match_reasons?.map((r, i) => (
                        <div key={i} className="flex items-start gap-2 mb-1">
                          <span className="text-emerald-400 flex-shrink-0 mt-0.5"><Icon.Check /></span>
                          <span className="text-xs text-slate-300">{r}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Missing skills */}
                  {(selectedJob.match?.missing_skills?.length ?? 0) > 0 && (
                    <div className="mb-4">
                      <p className="text-xs font-semibold text-slate-400 mb-2">SKILL GAPS</p>
                      <div className="flex flex-wrap gap-1">
                        {selectedJob.match?.missing_skills?.map(s => <SkillTag key={s} skill={s} variant="missing" />)}
                      </div>
                    </div>
                  )}

                  {/* Description */}
                  {(jobDetail?.description || selectedJob.description_summary) && (
                    <div className="mb-4">
                      <p className="text-xs font-semibold text-slate-400 mb-2">DESCRIPTION</p>
                      <div className="text-xs text-slate-300 leading-relaxed max-h-40 overflow-y-auto bg-white/3 rounded-lg p-3 border border-white/5">
                        {jobDetail?.description || selectedJob.description_summary}
                      </div>
                    </div>
                  )}

                  {/* Skills */}
                  {(selectedJob.required_skills?.length ?? 0) > 0 && (
                    <div className="mb-4">
                      <p className="text-xs font-semibold text-slate-400 mb-2">REQUIRED SKILLS</p>
                      <div className="flex flex-wrap gap-1">
                        {selectedJob.required_skills?.map(s => <SkillTag key={s} skill={s} />)}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-3">
                    <a
                      href={selectedJob.apply_url || selectedJob.job_url || "#"}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={() => handleApplyJob(selectedJob)}
                      className="flex-1 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-semibold py-3 rounded-xl transition-all text-center text-sm"
                    >
                      Apply Now
                    </a>
                    <button
                      onClick={() => handleViewInterviewPrep(selectedJob)}
                      className="px-4 py-3 bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 hover:text-white rounded-xl transition-colors text-sm"
                    >
                      Prep
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-64 text-slate-600 text-sm rounded-xl border border-white/5">
                  ← Select a job to view details
                </div>
              )}
            </div>

            {/* Right: Quick stats panel */}
            <div className="col-span-12 lg:col-span-3 xl:col-span-3 space-y-4">
              {/* Career DNA */}
              {careerDNA.archetype && (
                <div className="bg-gradient-to-br from-violet-500/10 to-indigo-500/10 rounded-xl border border-violet-500/20 p-4">
                  <p className="text-xs font-semibold text-violet-400 mb-2">🧬 CAREER DNA</p>
                  <p className="text-sm font-bold text-white">{careerDNA.archetype}</p>
                  {careerDNA.value_proposition && (
                    <p className="text-xs text-slate-400 mt-1 leading-relaxed">{careerDNA.value_proposition}</p>
                  )}
                  {(careerDNA.core_strengths?.length ?? 0) > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1">
                      {careerDNA.core_strengths?.map((s: string) => (
                        <SkillTag key={s} skill={s} variant="highlight" />
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Application Pipeline */}
              <div className="bg-white/5 rounded-xl border border-white/10 p-4">
                <p className="text-xs font-semibold text-slate-400 mb-3">APPLICATION PIPELINE</p>
                <div className="space-y-2">
                  {Object.entries(dashboard?.applications_summary || {}).map(([status, count]) => (
                    <div key={status} className="flex items-center justify-between">
                      <span className="text-xs text-slate-400 capitalize">{status.replace(/_/g, " ")}</span>
                      <span className="text-xs font-semibold text-white bg-white/5 px-2 py-0.5 rounded">{count as number}</span>
                    </div>
                  ))}
                  {Object.keys(dashboard?.applications_summary || {}).length === 0 && (
                    <p className="text-slate-500 text-xs">No applications yet</p>
                  )}
                </div>
              </div>

              {/* Quick Insights */}
              {insights.slice(0, 2).map(insight => (
                <div key={insight.id} className={`rounded-xl border p-4 ${insight.is_positive !== false ? "bg-emerald-500/5 border-emerald-500/20" : "bg-red-500/5 border-red-500/20"}`}>
                  <p className="text-xs font-semibold text-slate-400 mb-1 uppercase tracking-wide">{insight.category.replace(/_/g, " ")}</p>
                  <p className="text-xs font-medium text-white">{insight.title}</p>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2">{insight.content}</p>
                </div>
              ))}

              {/* Skill Gap Summary */}
              {dashboard?.skill_gap && (
                <div className="bg-amber-500/5 rounded-xl border border-amber-500/20 p-4">
                  <p className="text-xs font-semibold text-amber-400 mb-2">⚡ SKILL GAPS</p>
                  <div className="flex flex-wrap gap-1">
                    {(dashboard.skill_gap.missing_skills || []).slice(0, 6).map((s) => (
                      <SkillTag key={s as string} skill={s as string} variant="missing" />
                    ))}
                  </div>
                  {dashboard.skill_gap.estimated_upskill_months && (
                    <p className="text-xs text-slate-400 mt-2">
                      ~{dashboard.skill_gap.estimated_upskill_months} months to close gaps
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── CAREER INTELLIGENCE TAB ──────────────────────────────────── */}
        {activeTab === "career" && (
          <div className="space-y-6">
            {/* Career DNA */}
            {careerDNA.archetype && (
              <div className="bg-gradient-to-br from-violet-500/10 to-indigo-500/10 rounded-xl border border-violet-500/20 p-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <p className="text-xs font-semibold text-violet-400 mb-2">ARCHETYPE</p>
                    <p className="text-xl font-bold text-white">{careerDNA.archetype}</p>
                    <p className="text-sm text-slate-400 mt-1">{careerDNA.specialty}</p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-violet-400 mb-2">VALUE PROPOSITION</p>
                    <p className="text-sm text-slate-300">{careerDNA.value_proposition}</p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-violet-400 mb-2">CORE STRENGTHS</p>
                    <div className="flex flex-wrap gap-1">
                      {(careerDNA.core_strengths || []).map((s: string) => <SkillTag key={s} skill={s} variant="highlight" />)}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Career Paths */}
            <div>
              <SectionHeader icon={<Icon.TrendingUp />} title="Career Paths" />
              {(careerData?.career_paths?.length ?? 0) > 0 ? (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {careerData.career_paths?.map((path: any, i: number) => (
                    <CareerPathCard key={i} path={path} />
                  ))}
                </div>
              ) : (
                <div className="bg-white/5 rounded-xl border border-white/10 p-8 text-center text-slate-500">
                  Career paths not generated yet. Run the agent to build your career intelligence.
                </div>
              )}
            </div>

            {/* Skill Graph */}
            <div>
              <SectionHeader icon={<Icon.Brain />} title="Skill Graph" count={Object.keys(agent?.skill_graph || {}).length} />
              <div className="bg-white/5 rounded-xl border border-white/10 p-6">
                <SkillGraph skillGraph={agent?.skill_graph || careerData?.skill_graph || {}} />
              </div>
            </div>

            {/* Target Roles */}
            {(agent?.target_roles || careerData?.target_roles || []).length > 0 && (
              <div>
                <SectionHeader icon={<Icon.Target />} title="Target Roles" />
                <div className="flex flex-wrap gap-2">
                  {(agent?.target_roles || careerData?.target_roles || []).map((role: string) => (
                    <span key={role} className="bg-violet-500/10 border border-violet-500/20 text-violet-300 px-3 py-1.5 rounded-lg text-sm">
                      {role}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── APPLICATIONS TAB ─────────────────────────────────────────── */}
        {activeTab === "applications" && (
          <div>
            <SectionHeader
              icon={<Icon.Check />}
              title="Application Tracker"
              count={applications.length}
            />
            <div className="overflow-x-auto">
              <KanbanBoard applications={applications} onStatusChange={handleAppStatusChange} />
            </div>
          </div>
        )}

        {/* ── SKILL GAPS TAB ───────────────────────────────────────────── */}
        {activeTab === "skills" && (
          <div className="max-w-4xl space-y-6">
            <SectionHeader icon={<Icon.Target />} title="Skill Gap Analysis" />

            {!skillGap?.gap_available ? (
              <div className="bg-white/5 rounded-xl border border-white/10 p-8 text-center">
                <p className="text-slate-400">{skillGap?.message || "Running skill gap analysis..."}</p>
              </div>
            ) : (
              <>
                {/* Overview */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-white/5 rounded-xl border border-white/10 p-4 text-center">
                    <p className="text-3xl font-bold text-amber-400">{Math.round(skillGap.overall_gap_score || 0)}%</p>
                    <p className="text-xs text-slate-400 mt-1">Gap Score</p>
                  </div>
                  <div className="bg-white/5 rounded-xl border border-white/10 p-4 text-center">
                    <p className="text-3xl font-bold text-red-400">{skillGap.missing_skills?.length || 0}</p>
                    <p className="text-xs text-slate-400 mt-1">Missing Skills</p>
                  </div>
                  <div className="bg-white/5 rounded-xl border border-white/10 p-4 text-center">
                    <p className="text-3xl font-bold text-blue-400">{skillGap.estimated_upskill_months?.toFixed(1) || "?"}</p>
                    <p className="text-xs text-slate-400 mt-1">Months to Bridge</p>
                  </div>
                </div>

                {/* Missing Skills */}
                {(skillGap.missing_skills?.length ?? 0) > 0 && (
                  <div className="bg-white/5 rounded-xl border border-white/10 p-6">
                    <p className="text-sm font-semibold text-white mb-3">Missing Skills</p>
                    <div className="flex flex-wrap gap-2">
                      {skillGap.missing_skills?.map(s => <SkillTag key={s as string} skill={s as string} variant="missing" />)}
                    </div>
                  </div>
                )}

                {/* Learning Roadmap */}
                {(skillGap.learning_roadmap || []).length > 0 && (
                  <div className="bg-white/5 rounded-xl border border-white/10 p-6">
                    <p className="text-sm font-semibold text-white mb-4">Learning Roadmap</p>
                    <div className="space-y-3">
                      {skillGap.learning_roadmap!.map((item, i) => (
                        <div key={i} className="flex items-start gap-4 p-3 bg-white/5 rounded-lg border border-white/5">
                          <div className="w-8 h-8 rounded-full bg-violet-500/20 border border-violet-500/30 flex items-center justify-center text-xs font-bold text-violet-400 flex-shrink-0">
                            {item.month || i + 1}
                          </div>
                          <div>
                            <p className="text-sm font-medium text-white">{item.focus || item.skill}</p>
                            <p className="text-xs text-slate-400 mt-0.5">{item.goals?.join(", ")}</p>
                            {item.career_impact && (
                              <span className={`text-xs mt-1 inline-block ${item.career_impact === "high" ? "text-amber-400" : "text-slate-400"}`}>
                                Impact: {item.career_impact}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Current skills */}
                {(skillGap.current_skills?.length ?? 0) > 0 && (
                  <div className="bg-white/5 rounded-xl border border-white/10 p-6">
                    <p className="text-sm font-semibold text-white mb-3">Your Current Skills</p>
                    <div className="flex flex-wrap gap-2">
                      {skillGap.current_skills?.map(s => <SkillTag key={s as string} skill={s as string} variant="highlight" />)}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ── INTERVIEW PREP TAB ───────────────────────────────────────── */}
        {activeTab === "interview" && (
          <div className="max-w-3xl">
            <SectionHeader icon={<Icon.BookOpen />} title="Interview Preparation" />

            {!selectedJob && !interviewPrep ? (
              <div className="bg-white/5 rounded-xl border border-white/10 p-8 text-center">
                <p className="text-slate-400 text-sm">Select a job from the Job Feed tab to generate interview preparation</p>
                <button
                  onClick={() => setActiveTab("feed")}
                  className="mt-4 px-4 py-2 bg-violet-600 text-white text-sm rounded-lg hover:bg-violet-500"
                >
                  Browse Jobs
                </button>
              </div>
            ) : interviewPrep ? (
              <div className="bg-white/5 rounded-xl border border-white/10 p-6">
                <InterviewPrepPanel prep={interviewPrep} />
              </div>
            ) : (
              <div className="flex items-center justify-center h-40">
                <div className="w-8 h-8 border-4 border-violet-500 border-t-transparent rounded-full animate-spin" />
              </div>
            )}
          </div>
        )}

        {/* ── MARKET INTELLIGENCE TAB ──────────────────────────────────── */}
        {activeTab === "market" && (
          <div className="max-w-4xl">
            <SectionHeader icon={<Icon.Globe />} title="Market Intelligence" />
            {insights.filter(i => ["market_demand", "salary_trend"].includes(i.category)).length === 0 ? (
              <div className="bg-white/5 rounded-xl border border-white/10 p-8 text-center text-slate-500">
                Market intelligence will be generated on the next agent run.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {insights.map(insight => (
                  <div key={insight.id} className={`rounded-xl border p-5 ${insight.is_positive !== false ? "bg-emerald-500/5 border-emerald-500/20" : "bg-red-500/5 border-red-500/20"}`}>
                    <div className="flex items-start gap-3">
                      <span className="text-xl">{insight.is_positive !== false ? "📈" : "📉"}</span>
                      <div>
                        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">{insight.category.replace(/_/g, " ")}</p>
                        <p className="text-sm font-bold text-white">{insight.title}</p>
                        <p className="text-xs text-slate-300 mt-2 leading-relaxed">{insight.content}</p>
                        {(insight.actionable_steps?.length ?? 0) > 0 && (
                          <div className="mt-3">
                            <p className="text-xs font-semibold text-slate-400 mb-1">Action Steps</p>
                            <ul className="space-y-1">
                              {insight.actionable_steps?.map((step, i) => (
                                <li key={i} className="text-xs text-slate-400 flex items-start gap-1.5">
                                  <span className="text-violet-400 flex-shrink-0">→</span> {step}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── INSIGHTS TAB ─────────────────────────────────────────────── */}
        {activeTab === "insights" && (
          <div className="max-w-4xl space-y-4">
            <SectionHeader icon={<Icon.Lightning />} title="Career Insights" count={insights.length} />
            {insights.length === 0 ? (
              <div className="bg-white/5 rounded-xl border border-white/10 p-8 text-center text-slate-500">
                No insights yet. The agent will generate personalized career insights on its next run.
              </div>
            ) : insights.map(insight => (
              <div key={insight.id} className="bg-white/5 rounded-xl border border-white/10 p-5">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <span className="text-xs font-semibold text-violet-400 uppercase tracking-wide">{insight.category.replace(/_/g, " ")}</span>
                    <h3 className="text-sm font-bold text-white mt-0.5">{insight.title}</h3>
                  </div>
                  <span className="text-xl">{insight.is_positive !== false ? "✅" : "⚠️"}</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">{insight.content}</p>
                {(insight.actionable_steps?.length ?? 0) > 0 && (
                  <div className="mt-3 pl-3 border-l-2 border-violet-500/30">
                    {insight.actionable_steps?.map((step, i) => (
                      <p key={i} className="text-xs text-slate-400 mb-1">→ {step}</p>
                    ))}
                  </div>
                )}
                {insight.created_at && (
                  <p className="text-xs text-slate-600 mt-3">{new Date(insight.created_at).toLocaleDateString()}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      <AutonomousWorkflowVisualizer defaultWorkflow="job" isExecuting={runningAgent || initializing} />
    </div>
  );
}
