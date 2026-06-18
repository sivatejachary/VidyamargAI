"use client";

import { BookOpen, Briefcase, AlertTriangle, TrendingUp, ArrowRight, Sparkles, ExternalLink } from "lucide-react";
import Link from "next/link";

export interface ActionCard {
  type: "course" | "job" | "resume_tip" | "career_path" | "haq";
  id?: string | number;
  title: string;
  subtitle?: string;
  action_label?: string;
  action_href?: string;
  meta?: Record<string, any>;
}

interface AIActionCardProps {
  card: ActionCard;
  onHAQComplete?: (callbackKey: string) => void;
}

const CARD_CONFIGS = {
  course: {
    icon: BookOpen,
    gradient: "from-emerald-500 to-teal-500",
    bg: "bg-emerald-50 dark:bg-emerald-950/20",
    border: "border-emerald-200 dark:border-emerald-800/30",
    badge: "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400",
    label: "Course",
  },
  job: {
    icon: Briefcase,
    gradient: "from-blue-500 to-indigo-500",
    bg: "bg-blue-50 dark:bg-blue-950/20",
    border: "border-blue-200 dark:border-blue-800/30",
    badge: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
    label: "Job",
  },
  resume_tip: {
    icon: Sparkles,
    gradient: "from-violet-500 to-purple-500",
    bg: "bg-violet-50 dark:bg-violet-950/20",
    border: "border-violet-200 dark:border-violet-800/30",
    badge: "bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-400",
    label: "Resume Tip",
  },
  career_path: {
    icon: TrendingUp,
    gradient: "from-amber-500 to-orange-500",
    bg: "bg-amber-50 dark:bg-amber-950/20",
    border: "border-amber-200 dark:border-amber-800/30",
    badge: "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400",
    label: "Career Path",
  },
  haq: {
    icon: AlertTriangle,
    gradient: "from-red-500 to-rose-500",
    bg: "bg-red-50 dark:bg-red-950/20",
    border: "border-red-200 dark:border-red-800/30",
    badge: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400",
    label: "Action Required",
  },
};

export default function AIActionCard({ card, onHAQComplete }: AIActionCardProps) {
  const config = CARD_CONFIGS[card.type] || CARD_CONFIGS.course;
  const Icon = config.icon;
  const href = card.action_href || "#";
  const label = card.action_label || "View";

  const content = (
    <div className={`
      relative flex items-start gap-3 p-3.5 rounded-xl border
      ${config.bg} ${config.border}
      hover:shadow-md hover:scale-[1.01] transition-all duration-200
      cursor-pointer overflow-hidden group
    `}>
      {/* Gradient top bar */}
      <div className={`absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r ${config.gradient} opacity-60 group-hover:opacity-100 transition-opacity`} />

      {/* Icon */}
      <div className={`mt-0.5 p-2 rounded-lg bg-gradient-to-br ${config.gradient} shrink-0`}>
        <Icon size={14} className="text-white" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2 mb-0.5">
          <span className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full ${config.badge}`}>
            {config.label}
          </span>
        </div>
        <p className="text-xs font-semibold text-foreground leading-snug line-clamp-2">{card.title}</p>
        {card.subtitle && (
          <p className="text-[10px] text-muted-foreground mt-0.5 leading-snug">{card.subtitle}</p>
        )}
      </div>

      {/* Action */}
      <div className={`shrink-0 mt-1 flex items-center gap-1 text-[10px] font-bold whitespace-nowrap`}
        style={{ color: config.gradient.includes('emerald') ? '#10b981' : config.gradient.includes('blue') ? '#3b82f6' : config.gradient.includes('violet') ? '#8b5cf6' : config.gradient.includes('amber') ? '#f59e0b' : '#ef4444' }}
      >
        {label} <ArrowRight size={10} className="group-hover:translate-x-0.5 transition-transform" />
      </div>
    </div>
  );

  if (card.type === "haq" && onHAQComplete) {
    return (
      <button onClick={() => onHAQComplete(String(card.meta?.callback_key || ""))} className="w-full text-left">
        {content}
      </button>
    );
  }

  if (href === "#") return content;

  return <Link href={href}>{content}</Link>;
}
