"use client";

import React, { useState, useEffect } from "react";
import {
  Brain, Cpu, Database, Network, Search, ShieldCheck, 
  ArrowRight, Sparkles, ChevronRight, X, Layers, Activity,
  Clock, Zap, CheckCircle2, AlertCircle, RefreshCw
} from "lucide-react";

interface Step {
  id: string;
  label: string;
  desc: string;
  tech?: string;
  icon: React.ComponentType<any>;
}

interface Workflow {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<any>;
  color: string;
  steps: Step[];
}

const WORKFLOWS: Record<string, Workflow> = {
  chat: {
    id: "chat",
    title: "AI Career Chat Workflow",
    description: "Multi-agent orchestration pipeline analyzing user intent, extracting entities, checking gaps, and executing career advice plans.",
    icon: Brain,
    color: "from-blue-600 to-indigo-600 text-blue-400 border-blue-500/20",
    steps: [
      { id: "user_q", label: "User Question", desc: "User inputs career queries or job discovery requests.", tech: "Next.js Frontend", icon: Sparkles },
      { id: "memory", label: "Conversation Memory", desc: "Retrieves short-term chat context & candidate preferences.", tech: "PostgreSQL Memory Cache", icon: Database },
      { id: "intent", label: "Intent Classifier", desc: "Classifies query into Career Advice, Resume Help, Job Search, Interview Prep, or Learning.", tech: "Gemini 1.5 Flash", icon: Brain },
      { id: "entity", label: "Entity Extraction", desc: "Extracts key search parameters: skills, company names, location, salary.", tech: "Named Entity Recognition (NER)", icon: Cpu },
      { id: "goal", label: "Goal Detection", desc: "Determines target goals and check constraints (e.g. requires resume/profile).", tech: "Agent Guardrails", icon: Layers },
      { id: "gap_check", label: "Gap Checker", desc: "Evaluates profile completeness. Triggers clarification question if crucial data is missing.", tech: "VidyaMarg Core Profile Engine", icon: ShieldCheck },
      { id: "planner", label: "Execution Planner", desc: "Creates step-by-step action plan to retrieve matching data.", tech: "LangChain ReAct / Planner", icon: Network },
      { id: "tool_select", label: "Tool Router & Selection", desc: "Routes requests to specific database search, external APIs, or learning modules.", tech: "Dynamic Tool Dispatcher", icon: Cpu },
      { id: "execution", label: "Execute Tools", desc: "Runs the actions (e.g. querying Qdrant, scanning career portals).", tech: "API Connectors & Scraping Service", icon: Search },
      { id: "reflection", label: "AI Reflection Agent", desc: "Evaluates results. If findings are sparse (e.g., <3 jobs), triggers self-correction loop to broaden search parameters.", tech: "Self-Reflection Agent Loop", icon: RefreshCw },
      { id: "response", label: "Response Builder", desc: "Summarizes matching jobs/advice, highlights missing skills, and outlines next actions.", tech: "Gemini 3.5 Flash Ingestion", icon: CheckCircle2 }
    ]
  },
  resume: {
    id: "resume",
    title: "Resume Ingestion & Intelligence",
    description: "End-to-end resume builder, OCR parser, profile mapping, and semantic vector indexing.",
    icon: Layers,
    color: "from-violet-600 to-fuchsia-600 text-violet-400 border-violet-500/20",
    steps: [
      { id: "upload", label: "Resume Upload/Update", desc: "Candidate uploads PDF/DOCX resume or uses AI builder template.", tech: "Next.js file ingestion", icon: Sparkles },
      { id: "ocr", label: "OCR & Text Parser", desc: "Extracts raw text. Uses fallback pipeline in milliseconds if OCR service is busy.", tech: "PDFJS / AWS Textract Fallback", icon: Cpu },
      { id: "parser", label: "Resume Parsing Engine", desc: "Decomposes text into structured JSON blocks: Skills, Experience, Education, Projects.", tech: "Gemini Structured Outputs", icon: Layers },
      { id: "skills", label: "Skills & DNA Mapping", desc: "Generates Career DNA, profile strength metrics, and maps to government or private pathways.", desc: "VidyaMarg Career DNA Engine", tech: "Skill Graph Indexer", icon: ShieldCheck },
      { id: "profile", label: "Candidate Profile Generation", desc: "Builds a unified candidate identity profile for job matching.", tech: "PostgreSQL Database", icon: Database },
      { id: "embeddings", label: "Embedding Generation", desc: "Converts structured profile text and skills into dense vectors (1536-dim).", tech: "OpenAI text-embedding-3-small", icon: Network },
      { id: "store", label: "Vector Database Storage", desc: "Stores candidate embeddings in Qdrant for semantic similarity searches.", tech: "Qdrant Vector DB", icon: Database }
    ]
  },
  job: {
    id: "job",
    title: "Autonomous Job Matching & Ranking",
    description: "Scans databases, career pages, ATS portals, and ranks them against the candidate's career DNA.",
    icon: Search,
    color: "from-emerald-600 to-teal-600 text-emerald-400 border-emerald-500/20",
    steps: [
      { id: "trigger", label: "Job Search Trigger", desc: "Initiates match search via scheduler or user query.", tech: "Cron scheduler / Web UI", icon: Zap },
      { id: "sources", label: "Job Discovery Engine", desc: "Scans PostgreSQL, Qdrant, Official Career Pages (Google/MS), ATS Platforms (Lever/Greenhouse), JSearch API.", tech: "VidyaMarg Web Crawlers", icon: Search },
      { id: "merge", label: "Merge & Deduplicate", desc: "Consolidates listings from all sources and removes duplicates.", tech: "String Similarity Matching", icon: Layers },
      { id: "spam", label: "Spam & Broken Link Filtering", desc: "Validates application links and screens out suspicious job listings.", tech: "Link Checker & Domain Filter", icon: ShieldCheck },
      { id: "scores", label: "Scoring Pipeline", desc: "Calculates scores: Freshness, Resume Match, Personalization, Company Quality.", tech: "VidyaMarg Scoring Engine", icon: Cpu },
      { id: "ranking", label: "Final Ranking", desc: "Orders matches and selects Top 20 best fitting roles.", tech: "Ranking algorithms", icon: Network },
      { id: "reflection_loop", label: "AI Reflection Loop", desc: "If results are too few, auto-expands search to adjacent cities, related roles, or remote listings.", tech: "Reflection Agent Loop", icon: RefreshCw }
    ]
  },
  monitor: {
    id: "monitor",
    title: "Monitoring & Automation Missions",
    description: "Scheduled automation checks that alert candidates when matching jobs open.",
    icon: Clock,
    color: "from-amber-600 to-orange-600 text-amber-400 border-amber-500/20",
    steps: [
      { id: "setup", label: "Create Monitoring Mission", desc: "User sets rule (e.g., 'Notify me when Google hires AI Engineers').", tech: "Postgres Mission Model", icon: Sparkles },
      { id: "scheduler", label: "Scheduler Engine", desc: "Triggers execution every 30 minutes in the background.", tech: "Celery / Redis Scheduler", icon: Clock },
      { id: "crawler", label: "Background Crawlers", desc: "Scours Ashby, Greenhouse, Lever, Workday, Telegram channels, and government portals.", tech: "Distributed Crawlers", icon: Search },
      { id: "normalize", label: "Normalize & Match", desc: "Ingests raw job data, matches against candidate profile DNA.", tech: "Qdrant Vector Matcher", icon: Brain },
      { id: "alert_check", label: "Match Found?", desc: "Checks if new matches meet notification thresholds.", tech: "Match Threshold Logic", icon: ShieldCheck },
      { id: "notify", label: "Notification Dispatch", desc: "Dispatches alerts via Email, Telegram Bot, or Web Dashboard.", tech: "Telegram API / SendGrid SMTP", icon: Zap }
    ]
  }
};

interface AutonomousWorkflowVisualizerProps {
  defaultWorkflow: "chat" | "resume" | "job" | "monitor";
  isExecuting?: boolean;
}

export default function AutonomousWorkflowVisualizer({
  defaultWorkflow,
  isExecuting = false
}: AutonomousWorkflowVisualizerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeWorkflowId, setActiveWorkflowId] = useState<string>(defaultWorkflow);
  const [animatedStepIndex, setAnimatedStepIndex] = useState<number>(-1);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Sync active workflow if default changes
  useEffect(() => {
    setActiveWorkflowId(defaultWorkflow);
  }, [defaultWorkflow]);

  // Simulate active workflow stepping when isExecuting is true
  useEffect(() => {
    if (!isExecuting) {
      setAnimatedStepIndex(-1);
      return;
    }

    const stepsCount = WORKFLOWS[activeWorkflowId]?.steps.length || 0;
    if (stepsCount === 0) return;

    setAnimatedStepIndex(0);
    const interval = setInterval(() => {
      setAnimatedStepIndex((prev) => {
        if (prev >= stepsCount - 1) {
          return 0; // Loop back
        }
        return prev + 1;
      });
    }, 1500);

    return () => clearInterval(interval);
  }, [isExecuting, activeWorkflowId]);

  const activeWorkflow = WORKFLOWS[activeWorkflowId];
  const ActiveIcon = activeWorkflow.icon;

  return (
    <>
      {/* Floating Toggle Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 z-40 flex items-center gap-2 px-4 py-3 rounded-full bg-slate-900 border border-slate-800 text-white shadow-2xl hover:bg-slate-800 hover:border-slate-700 transition-all duration-300 group cursor-pointer hover:scale-105 active:scale-95"
      >
        <span className="relative flex h-2.5 w-2.5">
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isExecuting ? "bg-emerald-400" : "bg-blue-400"}`}></span>
          <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${isExecuting ? "bg-emerald-500" : "bg-blue-500"}`}></span>
        </span>
        <Activity size={14} className={`text-slate-400 group-hover:text-white transition-colors ${isExecuting ? "animate-pulse" : ""}`} />
        <span className="text-xs font-bold tracking-tight">
          {isExecuting ? "Agent Executing..." : "Autonomous Workflow"}
        </span>
      </button>

      {/* Slide-over Drawer Panel */}
      {isOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden font-sans no-print">
          {/* Backdrop */}
          <div
            onClick={() => setIsOpen(false)}
            className="absolute inset-0 bg-slate-950/70 backdrop-blur-xs transition-opacity duration-300"
          />

          <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10 md:pl-16">
            <div className="pointer-events-auto w-screen max-w-md transform bg-slate-900/95 backdrop-blur-md border-l border-slate-800 text-slate-100 flex flex-col h-full shadow-2xl transition-all duration-300">
              {/* Header */}
              <div className="p-5 border-b border-slate-800 flex items-center justify-between shrink-0 bg-slate-950/40">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-xl bg-blue-600/10 border border-blue-500/20 text-blue-400 flex items-center justify-center">
                    <Activity size={18} className={isExecuting ? "animate-pulse" : ""} />
                  </div>
                  <div>
                    <h2 className="text-sm font-black tracking-wider uppercase text-white">System Workflow Monitor</h2>
                    <p className="text-[10px] text-slate-400 font-semibold mt-0.5">VidyaMarg Engine Diagnostics</p>
                  </div>
                </div>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
                >
                  <X size={16} />
                </button>
              </div>

              {/* Navigation Tabs */}
              <div className="flex border-b border-slate-800 shrink-0 bg-slate-950/20 overflow-x-auto custom-scrollbar">
                {Object.values(WORKFLOWS).map((wf) => {
                  const IconComp = wf.icon;
                  const isActive = activeWorkflowId === wf.id;
                  return (
                    <button
                      key={wf.id}
                      onClick={() => {
                        setActiveWorkflowId(wf.id);
                        setSelectedNodeId(null);
                      }}
                      className={`flex-1 min-w-[90px] py-3.5 px-2 text-center text-[10px] font-bold uppercase tracking-wider border-b-2 flex flex-col items-center gap-1.5 transition-all cursor-pointer ${
                        isActive
                          ? "border-blue-500 text-blue-400 bg-slate-850/30"
                          : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-850/10"
                      }`}
                    >
                      <IconComp size={14} className={isActive ? "text-blue-400" : "text-slate-400"} />
                      <span>{wf.id}</span>
                    </button>
                  );
                })}
              </div>

              {/* Workflow Details */}
              <div className="flex-1 overflow-y-auto px-5 py-6 space-y-6 custom-scrollbar">
                {/* Active Info Banner */}
                <div className="bg-slate-950/40 border border-slate-800 rounded-2xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <ActiveIcon size={16} className="text-blue-400" />
                    <h3 className="text-xs font-bold text-white uppercase tracking-wider">{activeWorkflow.title}</h3>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed font-semibold">
                    {activeWorkflow.description}
                  </p>
                  {isExecuting && (
                    <div className="mt-3 flex items-center gap-2 text-[10px] text-emerald-400 bg-emerald-950/30 border border-emerald-900/30 p-2 rounded-xl">
                      <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                      </span>
                      <span className="font-bold uppercase tracking-wider">Live Agent Active: Processing pipeline...</span>
                    </div>
                  )}
                </div>

                {/* Node Stepper */}
                <div className="relative pl-6 space-y-6 border-l border-slate-800/80 ml-2.5">
                  {activeWorkflow.steps.map((step, idx) => {
                    const StepIcon = step.icon;
                    const isAnimatedActive = animatedStepIndex === idx;
                    const isPassed = animatedStepIndex > idx;
                    const isSelected = selectedNodeId === step.id;

                    return (
                      <div
                        key={step.id}
                        onClick={() => setSelectedNodeId(isSelected ? null : step.id)}
                        className={`relative group cursor-pointer transition-all duration-300 ${
                          isAnimatedActive ? "scale-[1.02]" : ""
                        }`}
                      >
                        {/* Node Bullet */}
                        <div
                          className={`absolute -left-[35px] top-1 w-5.5 h-5.5 rounded-full border flex items-center justify-center transition-all duration-300 z-10 ${
                            isAnimatedActive
                              ? "bg-blue-600 border-blue-400 text-white shadow-[0_0_12px_rgba(59,130,246,0.6)] animate-pulse"
                              : isPassed
                              ? "bg-slate-800 border-blue-500/50 text-blue-400"
                              : "bg-slate-900 border-slate-800 text-slate-500"
                          }`}
                        >
                          <StepIcon size={10} className={isAnimatedActive ? "animate-spin-slow" : ""} />
                        </div>

                        {/* Node Card */}
                        <div
                          className={`p-3.5 rounded-xl border transition-all duration-300 ${
                            isSelected
                              ? "bg-slate-850/80 border-blue-500/40 shadow-lg"
                              : isAnimatedActive
                              ? "bg-slate-850/40 border-blue-500/20 shadow-md"
                              : "bg-slate-950/20 border-slate-850/60 hover:border-slate-800 hover:bg-slate-850/10"
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span
                              className={`text-[11px] font-bold transition-colors ${
                                isAnimatedActive
                                  ? "text-blue-400"
                                  : isPassed
                                  ? "text-slate-200"
                                  : "text-slate-350"
                              }`}
                            >
                              {step.label}
                            </span>
                            {step.tech && (
                              <span className="text-[9px] bg-slate-900 border border-slate-850 text-slate-500 font-bold px-1.5 py-0.5 rounded-md">
                                {step.tech}
                              </span>
                            )}
                          </div>
                          
                          <p className="text-[10px] text-slate-400 mt-1.5 leading-relaxed font-medium">
                            {step.desc}
                          </p>

                          {/* Node Detail Section (Expanded on Click) */}
                          {isSelected && (
                            <div className="mt-3 pt-3 border-t border-slate-800/80 text-[10px] space-y-2 text-slate-300">
                              <div>
                                <span className="text-slate-500 font-bold uppercase tracking-wider block">Diagnostics:</span>
                                <span className="font-semibold block mt-0.5">Status: {isAnimatedActive ? "Processing" : isPassed ? "Completed" : "Idle"}</span>
                              </div>
                              {step.tech && (
                                <div>
                                  <span className="text-slate-500 font-bold uppercase tracking-wider block">Underlying Tech:</span>
                                  <span className="text-blue-400 font-mono block mt-0.5">{step.tech}</span>
                                </div>
                              )}
                              <div>
                                <span className="text-slate-500 font-bold uppercase tracking-wider block">Context Scope:</span>
                                <span className="text-slate-400 block mt-0.5">Fully encapsulated autonomous sub-agent execution thread.</span>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Footer */}
              <div className="p-4 border-t border-slate-800 bg-slate-950/60 text-center shrink-0">
                <span className="text-[9px] text-slate-500 font-semibold tracking-wider uppercase block">
                  VidyaMarg Autonomous Agent Operations · v1.4
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
