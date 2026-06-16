"use client";

import { useEffect, useState } from "react";
import { apiService } from "@/services/api";
import { useWebSockets } from "@/hooks/useWebSockets";
import { Cpu, Terminal, Activity } from "lucide-react";
import TelegramSources from "@/components/TelegramSources";

export default function AdminAgents() {
  const [logs, setLogs] = useState<any[]>([]);
  const { addMessageListener } = useWebSockets("admin");
  const [activeTab, setActiveTab] = useState<"orchestrator" | "telegram">("orchestrator");

  const [agentStatuses, setAgentStatuses] = useState([
    { name: "Resume Collection Agent", status: "Idle", type: "collection" },
    { name: "Resume Parsing Agent", status: "Idle", type: "parsing" },
    { name: "Resume Screening Agent", status: "Idle", type: "screening" },
    { name: "Assessment Generator Agent", status: "Idle", type: "generator" },
    { name: "AI Proctoring Agent", status: "Idle", type: "proctoring" },
    { name: "Assessment Evaluation Agent", status: "Idle", type: "evaluation" },
    { name: "Tara Interview Agent", status: "Idle", type: "interview" },
    { name: "Interview Analysis Agent", status: "Idle", type: "analysis" },
    { name: "Candidate Ranking Agent", status: "Idle", type: "ranking" },
    { name: "Hiring Recommendation Agent", status: "Idle", type: "recommendation" },
    { name: "Offer Generation Agent", status: "Idle", type: "offer" },
    { name: "Onboarding Agent", status: "Idle", type: "onboarding" }
  ]);

  const [metricsData, setMetricsData] = useState<any>(null);
  const [loadingMetrics, setLoadingMetrics] = useState(true);

  useEffect(() => {
    apiService.getAdminMetrics()
      .then((data) => {
        if (data && data.agent_metrics) {
          setMetricsData(data.agent_metrics);
        }
      })
      .catch((err) => {
        console.error("Failed to load agent metrics", err);
      })
      .finally(() => {
        setLoadingMetrics(false);
      });
  }, []);

  useEffect(() => {
    const removeListener = addMessageListener((msg: any) => {
      if (msg.type === "agent_log") {
        const agentName = msg.data.agent_name;
        const agentStatus = msg.data.status;
        
        // Update status of matching agent
        setAgentStatuses((prev) => 
          prev.map((a) => a.name === agentName ? { ...a, status: agentStatus } : a)
        );

        // Add log entry
        setLogs((prev) => [
          { action: agentName, details: msg.data.message, time: msg.data.timestamp },
          ...prev.slice(0, 19)
        ]);

        // Reset status to Idle after 3.5 seconds
        setTimeout(() => {
          setAgentStatuses((prev) => 
            prev.map((a) => a.name === agentName ? { ...a, status: "Idle" } : a)
          );
        }, 3500);
      }
    });

    return () => removeListener();
  }, [addMessageListener]);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "running":
        return "bg-purple-500 border-purple-400 text-purple-300";
      case "success":
        return "bg-emerald-500 border-emerald-400 text-emerald-300";
      case "failed":
        return "bg-red-500 border-red-400 text-red-300";
      default:
        return "bg-gray-600 border-gray-500 text-gray-400";
    }
  };

  const agentMetrics = [
    {
      label: "Parsing Efficiency",
      value: metricsData?.parsing_efficiency?.value || "0.0%",
      note: metricsData?.parsing_efficiency?.note || "Not enough data available"
    },
    {
      label: "Screen Match Ratio",
      value: metricsData?.screen_match_ratio?.value || "0.0%",
      note: metricsData?.screen_match_ratio?.note || "Not enough data available"
    },
    {
      label: "Proctor Flags Ratio",
      value: metricsData?.proctor_flags_ratio?.value || "0.0%",
      note: metricsData?.proctor_flags_ratio?.note || "Not enough data available"
    },
    {
      label: "Tara Converse Adaptivity",
      value: metricsData?.tara_converse_adaptivity?.value || "0.0 turns",
      note: metricsData?.tara_converse_adaptivity?.note || "Not enough data available"
    }
  ];

  return (
    <div className="p-8 md:p-12 max-w-7xl mx-auto flex flex-col gap-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2">
          <span>AI Recruiter Control Room</span>
          <Cpu size={20} className="text-purple-400" />
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Monitor orchestration statuses, configurations, and live execution outputs for recruiter agents.
        </p>
      </div>

      {/* Tab Selectors */}
      <div className="flex gap-6 border-b border-border pb-px">
        <button
          onClick={() => setActiveTab("orchestrator")}
          className={`pb-3.5 text-xs font-bold transition-all relative cursor-pointer select-none ${
            activeTab === "orchestrator"
              ? "text-purple-400 border-b-2 border-purple-500 font-extrabold"
              : "text-gray-400 hover:text-white border-b-2 border-transparent"
          }`}
        >
          Agent Control Room
        </button>
        <button
          onClick={() => setActiveTab("telegram")}
          className={`pb-3.5 text-xs font-bold transition-all relative cursor-pointer select-none ${
            activeTab === "telegram"
              ? "text-purple-400 border-b-2 border-purple-500 font-extrabold"
              : "text-gray-400 hover:text-white border-b-2 border-transparent"
          }`}
        >
          Telegram Sources
        </button>
      </div>

      {activeTab === "orchestrator" ? (
        <>
          {/* Metrics Row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {agentMetrics.map((m, i) => (
              <div key={i} className="glass-panel p-5 rounded-xl border border-border bg-card/40">
                <span className="text-10 text-gray-500 font-bold uppercase tracking-wider block">{m.label}</span>
                <span className="text-2xl font-extrabold text-white block mt-2">{m.value}</span>
                <span className="text-10 text-purple-400/80 mt-1 block">{m.note}</span>
              </div>
            ))}
          </div>

          {/* Agent status grid and Live logs */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* Agent list */}
            <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-border bg-card/40 flex flex-col gap-5">
              <h2 className="text-sm font-bold text-white flex items-center gap-2 border-b border-border pb-3">
                <Activity size={16} className="text-purple-400 animate-pulse" />
                <span>Agent Orchestrator Node Statuses</span>
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {agentStatuses.map((a, i) => {
                  const statusClass = getStatusColor(a.status);
                  return (
                    <div key={i} className="flex justify-between items-center p-3 rounded-xl border border-border/40 bg-card/40 hover:border-border hover:bg-card/60 transition-all">
                      <span className="text-xs font-semibold text-gray-300">{a.name}</span>
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${statusClass.split(" ")[0]} animate-pulse`} />
                        <span className={`text-9 font-bold uppercase ${statusClass.split(" ")[2]}`}>
                          {a.status}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Live logs console */}
            <div className="glass-panel p-6 rounded-2xl border border-border bg-card/40 flex flex-col gap-4">
              <h2 className="text-sm font-bold text-white flex items-center gap-2">
                <Terminal size={16} className="text-purple-400" />
                <span>Agent Console</span>
              </h2>

              <div className="flex-1 bg-background border border-border rounded-xl p-4 font-mono text-10 flex flex-col gap-2 max-h-420 overflow-y-auto">
                {logs.length === 0 ? (
                  <span className="text-gray-600 italic">Listening for live execution flows...</span>
                ) : (
                  logs.map((log, i) => (
                    <div key={i} className="leading-tight text-gray-400">
                      <span className="text-purple-500 font-bold">[{new Date(log.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}]</span>{" "}
                      <span className="text-indigo-400">{log.action}:</span>{" "}
                      <span>{log.details}</span>
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>
        </>
      ) : (
        <TelegramSources />
      )}
    </div>
  );
}
