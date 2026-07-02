"use client";

import { useState } from "react";
import { 
  GitFork, Bot, Sparkles, Mic, MessageSquare, Award,
  CheckCircle, ArrowRight, ShieldAlert, Cpu, BarChart3
} from "lucide-react";

interface InterviewPack {
  company: string;
  role: string;
  difficulty: "Easy" | "Medium" | "Hard";
  questions_count: number;
}

export default function InterviewWorkspace() {
  const [selectedSim, setSelectedSim] = useState<"voice" | "chat" | null>(null);

  const mockPacks: InterviewPack[] = [
    { company: "NVIDIA", role: "AI Systems Engineer", difficulty: "Hard", questions_count: 12 },
    { company: "Google", role: "Staff Backend Engineer", difficulty: "Hard", questions_count: 15 },
    { company: "Amazon", role: "Software Development Engineer II", difficulty: "Medium", questions_count: 10 }
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-6 md:p-10">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-violet-500/10 text-violet-400 border border-violet-500/20">
              AI Assessment Loop
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-violet-400 to-indigo-400 bg-clip-text text-transparent">
            Interview Workspace
          </h1>
          <p className="text-xs text-slate-400 max-w-md mt-1">
            Conduct AI-simulated interviews, measure speech/text confidence indices, and receive instant feedback.
          </p>
        </div>
        
        <div className="flex items-center gap-6 bg-slate-900/60 backdrop-blur-md border border-slate-800 p-4 rounded-2xl">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-teal-500/10 text-teal-400 border border-teal-500/20">
              <Award size={18} />
            </div>
            <div>
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block">Average Score</span>
              <span className="text-sm font-extrabold text-slate-200">82%</span>
            </div>
          </div>
          <div className="w-px h-8 bg-slate-800" />
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/20">
              <BarChart3 size={18} />
            </div>
            <div>
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block">Confidence Index</span>
              <span className="text-sm font-extrabold text-slate-200">High (0.87)</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Core Simulation Selection */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-900/40 backdrop-blur-md border border-slate-900/80 rounded-3xl p-6 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-violet-600/5 rounded-full blur-3xl pointer-events-none" />
            <h2 className="text-base font-bold text-slate-200 mb-4 flex items-center gap-2">
              <Cpu size={16} className="text-violet-400" /> Launch AI Interview Simulator
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Voice Simulator Option */}
              <div 
                onClick={() => setSelectedSim("voice")}
                className={`p-5 rounded-2xl border cursor-pointer transition-all duration-300 ${
                  selectedSim === "voice" 
                    ? "bg-violet-950/20 border-violet-500/60 shadow-[0_0_20px_rgba(139,92,246,0.15)]" 
                    : "bg-slate-900/30 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/20 text-violet-400 flex items-center justify-center mb-3">
                  <Mic size={18} />
                </div>
                <h3 className="text-sm font-bold text-slate-200 mb-1">Voice Simulator</h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">
                  Practice oral technical tests. Measures speed, confidence metrics, and language fluency.
                </p>
                <button className="flex items-center gap-1 text-[10px] font-bold text-violet-400 hover:text-violet-300">
                  Select Simulation <ArrowRight size={10} />
                </button>
              </div>

              {/* Chat Simulator Option */}
              <div 
                onClick={() => setSelectedSim("chat")}
                className={`p-5 rounded-2xl border cursor-pointer transition-all duration-300 ${
                  selectedSim === "chat" 
                    ? "bg-teal-950/20 border-teal-500/60 shadow-[0_0_20px_rgba(20,184,166,0.15)]" 
                    : "bg-slate-900/30 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div className="w-10 h-10 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400 flex items-center justify-center mb-3">
                  <MessageSquare size={18} />
                </div>
                <h3 className="text-sm font-bold text-slate-200 mb-1">Chat Simulator</h3>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">
                  Text-based coding interview. Evaluates algorithmic optimization and system design layouts.
                </p>
                <button className="flex items-center gap-1 text-[10px] font-bold text-teal-400 hover:text-teal-300">
                  Select Simulation <ArrowRight size={10} />
                </button>
              </div>
            </div>

            {selectedSim && (
              <div className="mt-6 pt-5 border-t border-slate-800 flex justify-end">
                <button className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition-all shadow-md">
                  Start Simulator ({selectedSim === "voice" ? "Voice" : "Chat"})
                </button>
              </div>
            )}
          </div>

          {/* Active Evaluations Logs */}
          <div className="bg-slate-900/40 backdrop-blur-md border border-slate-900/80 rounded-3xl p-6">
            <h2 className="text-base font-bold text-slate-200 mb-4 flex items-center gap-2">
              <CheckCircle size={16} className="text-teal-400" /> Completed Assessments History
            </h2>

            <div className="space-y-3">
              <div className="flex items-center justify-between p-4 rounded-xl bg-slate-900/30 border border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center">
                    <CheckCircle size={14} />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-slate-200">System Design (Google Mock)</h3>
                    <span className="text-[10px] text-slate-500">Completed 3 days ago</span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs font-bold text-emerald-400">88%</span>
                </div>
              </div>

              <div className="flex items-center justify-between p-4 rounded-xl bg-slate-900/30 border border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center">
                    <CheckCircle size={14} />
                  </div>
                  <div>
                    <h3 className="text-xs font-bold text-slate-200">Data Structures & Algorithms (NVIDIA Mock)</h3>
                    <span className="text-[10px] text-slate-500">Completed 1 week ago</span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs font-bold text-emerald-400">76%</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Company Interview Packs */}
        <div className="bg-slate-900/40 backdrop-blur-md border border-slate-900/80 rounded-3xl p-6 h-fit">
          <h2 className="text-base font-bold text-slate-200 mb-4 flex items-center gap-2">
            <Sparkles size={16} className="text-violet-400" /> Company Packs
          </h2>

          <div className="space-y-3">
            {mockPacks.map((pack) => (
              <div 
                key={pack.company}
                className="p-4 rounded-xl bg-slate-900/30 border border-slate-800 hover:border-slate-700 transition-colors"
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-xs font-extrabold text-slate-200">{pack.company}</h3>
                  <span className={`px-2 py-0.5 rounded text-[8px] font-extrabold uppercase ${
                    pack.difficulty === "Hard" 
                      ? "bg-red-500/10 text-red-400 border border-red-500/20" 
                      : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                  }`}>
                    {pack.difficulty}
                  </span>
                </div>
                <p className="text-[10px] text-slate-400 mb-3">{pack.role}</p>
                <div className="flex items-center justify-between">
                  <span className="text-[9px] text-slate-500">{pack.questions_count} Questions</span>
                  <button className="text-[9px] font-bold text-blue-400 hover:text-blue-300 flex items-center gap-0.5">
                    Start Pack <ArrowRight size={8} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
