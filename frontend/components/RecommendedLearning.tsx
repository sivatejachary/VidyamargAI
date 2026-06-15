"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BookOpen, Award, Code, Compass, ChevronRight } from "lucide-react";

interface Recommendations {
  skills: string[];
  certifications: string[];
  projects: string[];
  roadmap: string[];
}

interface RecommendedLearningProps {
  recommendations: Recommendations;
}

type TabType = "roadmap" | "certs" | "projects";

export default function RecommendedLearning({ recommendations }: RecommendedLearningProps) {
  const [activeTab, setActiveTab] = useState<TabType>("roadmap");

  if (!recommendations) return null;

  const tabs = [
    { id: "roadmap", label: "Learning Roadmap", icon: Compass },
    { id: "certs", label: "Certifications", icon: Award },
    { id: "projects", label: "Suggested Projects", icon: Code }
  ];

  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-6">
        <div className="w-9 h-9 rounded-xl bg-indigo-50 flex items-center justify-center">
          <BookOpen className="w-5 h-5 text-indigo-600" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-slate-800">Recommended Learning Path</h3>
          <p className="text-xs text-slate-500">Curated steps, projects, and credentials to close your skill gaps</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-100 mb-6 gap-2">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabType)}
              className={`flex items-center gap-2 pb-3 px-1 text-sm font-medium border-b-2 transition-all relative ${
                isActive
                  ? "border-indigo-600 text-indigo-600"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
              {isActive && (
                <motion.div
                  layoutId="activeTabUnderline"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-600"
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Content Area */}
      <div className="min-h-[200px]">
        <AnimatePresence mode="wait">
          {activeTab === "roadmap" && (
            <motion.div
              key="roadmap"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              transition={{ duration: 0.2 }}
              className="space-y-4"
            >
              {recommendations.roadmap.map((step, idx) => {
                // Split title (e.g. "For Docker:") and the actual content
                const parts = step.split(":");
                const title = parts.length > 1 ? parts[0] + ":" : `Step ${idx + 1}:`;
                const content = parts.length > 1 ? parts.slice(1).join(":") : step;

                return (
                  <div key={idx} className="flex gap-4 p-4 rounded-xl bg-slate-50/50 border border-slate-100 hover:shadow-sm transition-all duration-200">
                    <div className="w-8 h-8 rounded-full bg-indigo-50 border border-indigo-100 flex items-center justify-center font-bold text-xs text-indigo-600 shrink-0">
                      {idx + 1}
                    </div>
                    <div>
                      <h4 className="font-bold text-slate-800 text-sm">{title}</h4>
                      <p className="text-slate-600 text-xs mt-1 leading-relaxed">{content.trim()}</p>
                    </div>
                  </div>
                );
              })}
            </motion.div>
          )}

          {activeTab === "certs" && (
            <motion.div
              key="certs"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              transition={{ duration: 0.2 }}
              className="grid gap-3 sm:grid-cols-2"
            >
              {recommendations.certifications.map((cert, idx) => (
                <div key={idx} className="p-4 rounded-xl bg-gradient-to-br from-slate-50 to-slate-100/50 border border-slate-100 flex items-center gap-3 hover:shadow-sm transition-all duration-200">
                  <div className="w-8 h-8 rounded-lg bg-amber-50 border border-amber-100 flex items-center justify-center shrink-0">
                    <Award className="w-4.5 h-4.5 text-amber-600" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-slate-800 text-xs leading-snug">{cert}</h4>
                    <span className="text-[10px] text-slate-400 mt-0.5 block">Recommended Credential</span>
                  </div>
                </div>
              ))}
            </motion.div>
          )}

          {activeTab === "projects" && (
            <motion.div
              key="projects"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 10 }}
              transition={{ duration: 0.2 }}
              className="space-y-3"
            >
              {recommendations.projects.map((proj, idx) => (
                <div key={idx} className="p-4 rounded-xl border border-slate-100 bg-slate-50/50 hover:bg-white hover:shadow-sm transition-all duration-200 flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center shrink-0 mt-0.5">
                    <Code className="w-4.5 h-4.5 text-indigo-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-semibold text-slate-800 text-sm">{proj}</h4>
                    <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                      Hands-on project designed to build real-world capability and enhance your resume portfolio.
                    </p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-300 shrink-0 self-center" />
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
