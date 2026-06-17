"use client";

import { AlertCircle, TrendingUp, BookOpen, Check } from "lucide-react";

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
      <div className="bg-white rounded-2xl p-6 border border-slate-100 flex flex-col items-center justify-center text-center min-h-[300px]">
        <div className="w-12 h-12 rounded-full bg-slate-50 flex items-center justify-center text-slate-400 mb-3">
          <BookOpen className="w-5 h-5" />
        </div>
        <p className="text-sm font-semibold text-slate-700">No missing skills identified</p>
        <p className="text-xs text-slate-550 mt-1 max-w-[220px]">
          You have all the required skills for the matched job opportunities!
        </p>
      </div>
    );
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "High":
        return {
          bg: "hover:border-red-200 hover:bg-red-50/10",
          badge: "bg-red-50 text-red-700 border-red-100",
          bar: "bg-red-500",
        };
      case "Medium":
        return {
          bg: "hover:border-amber-200 hover:bg-amber-50/10",
          badge: "bg-amber-50 text-amber-700 border-amber-100",
          bar: "bg-amber-500",
        };
      default:
        return {
          bg: "hover:border-slate-200 hover:bg-slate-50/20",
          badge: "bg-slate-50 text-slate-650 border-slate-100",
          bar: "bg-slate-400",
        };
    }
  };

  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-100">
      <div className="flex items-start justify-between gap-4 mb-6">
        <div className="flex gap-3">
          <div className="w-10 h-10 rounded-xl bg-slate-50 flex items-center justify-center text-slate-550 border border-slate-100 shrink-0">
            <AlertCircle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-800">Skill Gap Analysis</h3>
            <p className="text-xs text-slate-500">Skills demanded in your matches that you don&apos;t have</p>
          </div>
        </div>
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
                  ? "border-blue-500 bg-blue-50/30 shadow-md shadow-blue-50/10 scale-[1.01]"
                  : `border-slate-100 bg-slate-50/50 hover:bg-white hover:shadow-md hover:border-slate-200 ${colors.bg}`
              }`}
            >
              <div className="flex items-start justify-between gap-4 mb-2">
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="font-semibold text-slate-800 text-sm">{gap.skill}</h4>
                    {isSelected && (
                      <Check className="w-3.5 h-3.5 text-blue-600 stroke-[3]" />
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Found in {gap.count} out of top matches
                  </p>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-xs font-bold border ${colors.badge}`}>
                  {gap.priority} Priority
                </span>
              </div>

              {/* Progress bar */}
              <div>
                <div className="flex justify-between items-center text-xs text-slate-500 mb-1">
                  <span>Industry Demand</span>
                  <span className="font-bold">{gap.missing_in_percentage}%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
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
