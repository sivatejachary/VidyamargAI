"use client";

import { AlertCircle, BookOpen, Check, ExternalLink } from "lucide-react";
import Link from "next/link";

interface SkillGap {
  skill: string;
  missing_in_percentage: number;
  priority: "High" | "Medium" | "Low";
  count: number;
}

interface MissingSkillsProps {
  skillGaps: SkillGap[];
  selectedSkill?: string | null;
  onSelectSkill?: (skill: string) => void;
}

export default function MissingSkills({ skillGaps, selectedSkill = null, onSelectSkill }: MissingSkillsProps) {
  if (!skillGaps || skillGaps.length === 0) {
    return (
      <div className="bg-card rounded-2xl p-6 border border-border flex flex-col items-center justify-center text-center min-h-[300px]">
        <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center text-muted-foreground mb-3">
          <BookOpen className="w-5 h-5" />
        </div>
        <p className="text-sm font-semibold text-foreground">No missing skills identified</p>
        <p className="text-xs text-muted-foreground mt-1 max-w-[220px]">
          You have all the required skills for the matched job opportunities!
        </p>
      </div>
    );
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "High":
        return {
          bg: "hover:border-red-200 dark:hover:border-red-800 hover:bg-red-50/10 dark:hover:bg-red-950/10",
          badge: "bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-400 border-red-100 dark:border-red-900/50",
          bar: "bg-red-500",
        };
      case "Medium":
        return {
          bg: "hover:border-amber-200 dark:hover:border-amber-800 hover:bg-amber-50/10 dark:hover:bg-amber-950/10",
          badge: "bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400 border-amber-100 dark:border-amber-900/50",
          bar: "bg-amber-500",
        };
      default:
        return {
          bg: "hover:border-slate-200 dark:hover:border-slate-700 hover:bg-slate-50/20 dark:hover:bg-slate-800/20",
          badge: "bg-slate-50 dark:bg-slate-800/50 text-slate-650 dark:text-slate-300 border-slate-100 dark:border-slate-700",
          bar: "bg-slate-400",
        };
    }
  };

  return (
    <div className="bg-card rounded-2xl p-6 border border-border">
      <div className="flex items-start justify-between gap-4 mb-6">
        <div className="flex gap-3">
          <div className="w-10 h-10 rounded-xl bg-muted flex items-center justify-center text-muted-foreground border border-border shrink-0">
            <AlertCircle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-foreground">Skill Gap Analysis</h3>
            <p className="text-xs text-muted-foreground">Skills demanded in your top matches that you&apos;re missing</p>
          </div>
        </div>
        <Link
          href="/candidate/skill-lab"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/30 border border-blue-100 dark:border-blue-800/30 hover:bg-blue-100 dark:hover:bg-blue-900/40 transition shrink-0"
        >
          Learn Missing Skills <ExternalLink className="w-3 h-3" />
        </Link>
      </div>

      <div className="space-y-4">
        {skillGaps.map((gap, index) => {
          const colors = getPriorityColor(gap.priority);
          const isSelected = selectedSkill === gap.skill;
          return (
            <div
              key={gap.skill}
              onClick={() => onSelectSkill && onSelectSkill(gap.skill)}
              className={`p-4 rounded-xl border cursor-pointer transition-all duration-200 ${
                isSelected
                  ? "border-blue-500 bg-blue-50/30 dark:bg-blue-950/20 shadow-md shadow-blue-50/10 scale-[1.01]"
                  : `border-border bg-muted/30 hover:bg-card hover:shadow-md ${colors.bg}`
              }`}
            >
              <div className="flex items-start justify-between gap-4 mb-2">
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="font-semibold text-foreground text-sm">{gap.skill}</h4>
                    {isSelected && (
                      <Check className="w-3.5 h-3.5 text-blue-600 stroke-[3]" />
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Found in {gap.count} out of top matches
                  </p>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-xs font-bold border ${colors.badge}`}>
                  {gap.priority} Priority
                </span>
              </div>

              {/* Progress bar */}
              <div>
                <div className="flex justify-between items-center text-xs text-muted-foreground mb-1">
                  <span>Industry Demand</span>
                  <span className="font-bold">{gap.missing_in_percentage}%</span>
                </div>
                <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                  <div
                    style={{ width: `${gap.missing_in_percentage}%` }}
                    className={`h-full rounded-full transition-all duration-500 ${colors.bar}`}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
