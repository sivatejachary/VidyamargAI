"use client";

import { useEffect, useState } from "react";
import { apiService } from "@/services/api";
import { useWebSockets } from "@/hooks/useWebSockets";
import { Users, FileText, Terminal, Sparkles, Activity, Video } from "lucide-react";

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState<any>({
    total_candidates: 0,
    total_resumes: 0,
    parsing_efficiency: "0.0%"
  });
  const [logs, setLogs] = useState<any[]>([]);
  const [videoAnalytics, setVideoAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Connect websocket for live logs & system alerts
  const { addMessageListener } = useWebSockets("admin");

  const loadData = async () => {
    try {
      const data = await apiService.getAdminMetrics();
      setMetrics(data.metrics);
      setLogs(data.logs);
      setVideoAnalytics(data.video_analytics);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    // Listen to real-time logs from system runs
    const removeListener = addMessageListener((msg: any) => {
      if (msg.type === "agent_log") {
        setLogs((prev) => [
          { action: msg.data.agent_name, details: msg.data.message, time: msg.data.timestamp },
          ...prev.slice(0, 14)
        ]);
        loadData(); // Reload numbers
      } else if (msg.type === "proctor_alert") {
        setLogs((prev) => [
          { action: "System Alert", details: `${msg.data.candidate_name}: ${msg.data.event_type} - ${msg.data.details}`, time: msg.data.timestamp },
          ...prev.slice(0, 14)
        ]);
        loadData();
      }
    });

    return () => removeListener();
  }, [addMessageListener]);

  if (loading) {
    return (
      <div className="p-8 max-w-7xl mx-auto text-gray-500">
        Loading admin console...
      </div>
    );
  }

  return (
    <div className="p-8 md:p-12 max-w-7xl mx-auto flex flex-col gap-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-gray-800 pb-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <span>Vidyamarg Admin Dashboard</span>
            <Sparkles size={20} className="text-purple-400" />
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            System administration metrics, candidate resume processing status, and LMS content distribution logs.
          </p>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { label: "Registered Students", value: metrics.total_candidates, icon: Users, color: "text-purple-400" },
          { label: "Resumes Uploaded", value: metrics.total_resumes, icon: FileText, color: "text-blue-400" },
          { label: "AI Parsing Efficiency", value: metrics.parsing_efficiency, icon: Activity, color: "text-emerald-400" }
        ].map((c, i) => {
          const Icon = c.icon;
          return (
            <div key={i} className="glass-panel p-6 rounded-xl border border-gray-800 flex flex-col justify-between gap-4 bg-card/40">
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-400 font-bold uppercase tracking-wider">{c.label}</span>
                <Icon size={20} className={c.color} />
              </div>
              <span className="text-3xl font-bold text-white">{c.value}</span>
            </div>
          );
        })}
      </div>

      {/* Video Streaming & Delivery Performance Monitoring */}
      {videoAnalytics && (
        <div className="glass-panel p-6 rounded-2xl border border-gray-800 bg-card/40 flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Video size={16} className="text-indigo-400" />
              <span>Video Playback & CDN Performance</span>
            </h2>
            <span className="text-[10px] font-mono text-gray-400 bg-gray-900 border border-gray-800 px-2 py-0.5 rounded uppercase font-bold tracking-wider">
              Live Edge CDN metrics
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {[
              { label: "Avg Load Time", value: `${videoAnalytics.avg_load_time}ms`, desc: "Target <300ms", status: videoAnalytics.avg_load_time < 300 ? "text-emerald-400" : "text-amber-400" },
              { label: "Avg Buffer Time", value: `${videoAnalytics.avg_buffer_time}ms`, desc: "Minimal lag", status: "text-blue-400" },
              { label: "Cache Hit Rate", value: `${videoAnalytics.cache_hit_rate}%`, desc: "Redis cache tier", status: "text-indigo-400" },
              { label: "CDN Hit Rate", value: `${videoAnalytics.cdn_hit_rate}%`, desc: "Cloudflare edge", status: "text-purple-400" },
              { label: "Playback Failures", value: videoAnalytics.total_failures, desc: "Zero errors", status: videoAnalytics.total_failures === 0 ? "text-emerald-400" : "text-red-400" }
            ].map((stat, i) => (
              <div key={i} className="p-4 rounded-xl border border-gray-800/40 bg-muted/20 flex flex-col justify-between gap-1">
                <span className="text-[10px] text-gray-400 uppercase font-bold tracking-wider">{stat.label}</span>
                <span className={`text-lg font-black ${stat.status}`}>{stat.value}</span>
                <span className="text-[9px] text-gray-550 font-medium">{stat.desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Live Logs Terminal */}
      <div className="glass-panel p-6 rounded-2xl border border-gray-800 bg-card/40 flex flex-col gap-4">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <Terminal size={16} className="text-purple-400" />
          <span>Live Orchestration execution logs</span>
        </h2>
        
        <div className="h-52 overflow-y-auto bg-background border border-gray-800 rounded-xl p-4 font-mono text-xs flex flex-col gap-2.5">
          {logs.length === 0 ? (
            <span className="text-gray-600 italic">Logs stream starting... Waiting for system events.</span>
          ) : (
            logs.map((log, i) => (
              <div key={i} className="flex gap-4 items-start text-gray-400 hover:text-white transition-colors">
                <span className="text-purple-500 font-semibold shrink-0">
                  [{new Date(log.time).toLocaleTimeString()}]
                </span>
                <span className="text-indigo-400 font-bold shrink-0">{log.action}:</span>
                <span className="leading-relaxed">{log.details}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
