"use client";

import { motion } from "framer-motion";
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
    return null;
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "High":
        return {
          badge: "bg-red-50 text-red-700 border-red-200",
          bar: "bg-gradient-to-r from-red-500 to-rose-600",
          bg: "hover:border-red-200"
        };
      case "Medium":
        return {
          badge: "bg-amber-50 text-amber-700 border-amber-200",
          bar: "bg-gradient-to-r from-amber-500 to-yellow-600",
          bg: "hover:border-amber-200"
        };
      default:
        return {
          badge: "bg-sky-50 text-sky-700 border-sky-200",
          bar: "bg-gradient-to-r from-sky-500 to-blue-600",
          bg: "hover:border-sky-200"
        };
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 rounded-xl bg-violet-50 flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-violet-600" />
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
            <motion.div
              key={gap.skill}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
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
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${gap.missing_in_percentage}%` }}
                    transition={{ duration: 0.6, delay: index * 0.08, ease: "easeOut" }}
                    className={`h-full rounded-full ${colors.bar}`}
                  />
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
