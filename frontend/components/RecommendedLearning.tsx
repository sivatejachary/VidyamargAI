"use client";

import { useState } from "react";
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
    { id: "projects", label: "Project Sandbox", icon: Code }
  ];

  return (
    <div className="bg-white dark:bg-slate-900 rounded-3xl p-6 border border-border/80 shadow-sm flex flex-col gap-6">
      
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-2xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-100 dark:border-indigo-900/60 flex items-center justify-center text-indigo-650 dark:text-indigo-400">
          <BookOpen className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-base font-black text-foreground">Upskilling Recommendations</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Custom learning pathways to cover matched job gaps</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-border/60">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabType)}
              className={`flex items-center gap-2 pb-3 px-1 text-sm font-bold border-b-2 transition-all relative cursor-pointer ${
                isActive
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
              {isActive && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
              )}
            </button>
          );
        })}
      </div>

      {/* Content Area */}
      <div className="min-h-200">
        {activeTab === "roadmap" && (
          <div className="space-y-4">
            {recommendations.roadmap.map((step, idx) => {
              const parts = step.split(":");
              const title = parts.length > 1 ? parts[0] + ":" : `Step ${idx + 1}:`;
              const content = parts.length > 1 ? parts.slice(1).join(":") : step;

              return (
                <div key={idx} className="flex gap-4 p-4 rounded-2xl bg-muted/20 dark:bg-muted/10 border border-border hover:shadow-md transition-all duration-205">
                  <div className="w-8 h-8 rounded-full bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-150 dark:border-indigo-850 flex items-center justify-center font-bold text-xs text-indigo-600 dark:text-indigo-400 shrink-0">
                    {idx + 1}
                  </div>
                  <div>
                    <h4 className="font-bold text-foreground text-sm">{title}</h4>
                    <p className="text-muted-foreground text-xs mt-1 leading-relaxed">{content.trim()}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === "certs" && (
          <div className="grid gap-3 sm:grid-cols-2">
            {recommendations.certifications.map((cert, idx) => (
              <div key={idx} className="p-4 rounded-2xl bg-muted/20 dark:bg-muted/10 border border-border flex items-center gap-3 hover:shadow-md transition-all duration-205">
                <div className="w-8 h-8 rounded-lg bg-amber-50 dark:bg-amber-955/40 border border-amber-150 dark:border-amber-850 flex items-center justify-center shrink-0">
                  <Award className="w-4.5 h-4.5 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <h4 className="font-bold text-foreground text-xs leading-snug">{cert}</h4>
                  <span className="text-10 text-muted-foreground mt-0.5 block">Recommended Credential</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === "projects" && (
          <div className="space-y-3">
            {recommendations.projects.map((proj, idx) => (
              <div key={idx} className="p-4 rounded-2xl border border-border bg-muted/20 dark:bg-muted/10 hover:bg-muted/30 hover:shadow-md transition-all duration-205 flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-150 dark:border-indigo-850 flex items-center justify-center shrink-0 mt-0.5">
                  <Code className="w-4.5 h-4.5 text-indigo-600 dark:text-indigo-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-bold text-foreground text-sm">{proj}</h4>
                  <p className="text-11 text-muted-foreground mt-1 leading-relaxed">
                    Hands-on project designed to build real-world capability and enhance your resume portfolio.
                  </p>
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0 self-center" />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
