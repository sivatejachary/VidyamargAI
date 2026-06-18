"use client";

import { useEffect, useState, useCallback } from "react";
import { Zap, BookOpen, Briefcase, FileText, Brain, TrendingUp, Clock, RefreshCw } from "lucide-react";
import { apiService } from "@/services/api";

interface ActivityItem {
  id: number;
  agent_name: string;
  action: string;
  detail: string;
  meta?: Record<string, any>;
  created_at: string;
}

const AGENT_ICONS: Record<string, any> = {
  "Job Agent":       Briefcase,
  "Skill Gap Agent": TrendingUp,
  "Resume Agent":    FileText,
  "Learning Agent":  BookOpen,
  "skill-lab Agent": BookOpen,
  "resume Agent":    FileText,
  "job-agent Agent": Briefcase,
  "general Agent":   Brain,
};

const AGENT_COLORS: Record<string, string> = {
  "Job Agent":       "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/30",
  "Skill Gap Agent": "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30",
  "Resume Agent":    "text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-950/30",
  "Learning Agent":  "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30",
  "skill-lab Agent": "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30",
  "resume Agent":    "text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-950/30",
  "job-agent Agent": "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/30",
  "general Agent":   "text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-950/30",
};

interface AgentActivityFeedProps {
  className?: string;
  maxItems?: number;
  showRefresh?: boolean;
}

export default function AgentActivityFeed({ className = "", maxItems = 10, showRefresh = true }: AgentActivityFeedProps) {
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchActivity = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const data = await apiService.getAgentActivity(maxItems);
      if (Array.isArray(data)) setActivities(data);
    } catch {
      // Silently fail
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [maxItems]);

  useEffect(() => {
    fetchActivity();
    const interval = setInterval(() => fetchActivity(), 30000);
    return () => clearInterval(interval);
  }, [fetchActivity]);

  const getTimeAgo = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  if (loading) {
    return (
      <div className={`flex flex-col gap-2 ${className}`}>
        {[1, 2, 3].map(i => (
          <div key={i} className="flex items-center gap-2 p-2.5 rounded-lg bg-muted/30 animate-pulse">
            <div className="w-7 h-7 rounded-lg bg-muted" />
            <div className="flex-1">
              <div className="h-2.5 bg-muted rounded w-3/4 mb-1.5" />
              <div className="h-2 bg-muted rounded w-1/2" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (activities.length === 0) {
    return (
      <div className={`flex flex-col items-center justify-center py-6 text-center ${className}`}>
        <div className="w-10 h-10 rounded-xl bg-muted/50 flex items-center justify-center mb-2">
          <Zap size={18} className="text-muted-foreground" />
        </div>
        <p className="text-xs font-semibold text-muted-foreground">No agent activity yet</p>
        <p className="text-[10px] text-muted-foreground/70 mt-0.5">Start a chat to see AI actions here</p>
      </div>
    );
  }

  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      {showRefresh && (
        <div className="flex items-center justify-between mb-1">
          <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
            <Zap size={9} /> Agent Activity
          </p>
          <button
            onClick={() => fetchActivity(true)}
            disabled={refreshing}
            className="p-1 rounded-md hover:bg-muted/50 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            <RefreshCw size={10} className={refreshing ? "animate-spin" : ""} />
          </button>
        </div>
      )}
      {activities.map((item) => {
        const IconComp = AGENT_ICONS[item.agent_name] || Brain;
        const colorClass = AGENT_COLORS[item.agent_name] || AGENT_COLORS["general Agent"];
        return (
          <div
            key={item.id}
            className="flex items-start gap-2.5 p-2.5 rounded-lg hover:bg-muted/20 transition-colors group"
          >
            <div className={`p-1.5 rounded-lg shrink-0 ${colorClass}`}>
              <IconComp size={12} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[11px] font-semibold text-foreground leading-tight line-clamp-2">{item.detail}</p>
              <div className="flex items-center gap-1 mt-0.5">
                <Clock size={9} className="text-muted-foreground" />
                <span className="text-[9px] text-muted-foreground">{getTimeAgo(item.created_at)}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
