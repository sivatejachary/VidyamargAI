"use client";

import { useEffect, useState } from "react";
import { apiService } from "@/services/api";
import { useWebSockets } from "@/hooks/useWebSockets";
import { Users, ClipboardList, CheckCircle, XCircle, Video, FileSignature, Terminal, Sparkles } from "lucide-react";
import { 
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Cell
} from "recharts";

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState<any>({
    total_candidates: 0,
    total_applications: 0,
    shortlisted: 0,
    rejected: 0,
    interviewed: 0,
    offers_sent: 0,
    offers_accepted: 0
  });
  const [funnel, setFunnel] = useState<any[]>([]);
  const [fraudTrends, setFraudTrends] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [videoAnalytics, setVideoAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Connect websocket for live logs & proctor alerts
  const { addMessageListener } = useWebSockets("admin");

  const loadData = async () => {
    try {
      const data = await apiService.getAdminMetrics();
      setMetrics(data.metrics);
      setFunnel(data.funnel);
      setFraudTrends(data.fraud_trends);
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
    // Listen to real-time logs from agent runs
    const removeListener = addMessageListener((msg: any) => {
      if (msg.type === "agent_log") {
        setLogs((prev) => [
          { action: msg.data.agent_name, details: msg.data.message, time: msg.data.timestamp },
          ...prev.slice(0, 14)
        ]);
        loadData(); // Reload numbers
      } else if (msg.type === "proctor_alert") {
        setLogs((prev) => [
          { action: "Proctor Alert", details: `${msg.data.candidate_name}: ${msg.data.event_type} - ${msg.data.details}`, time: msg.data.timestamp },
          ...prev.slice(0, 14)
        ]);
        loadData();
      }
    });

    return () => removeListener();
  }, [addMessageListener]);

  const COLORS = ["#8b5cf6", "#6366f1", "#4f46e5", "#3b82f6", "#10b981", "#059669"];

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
            <span>Recruiter Admin Portal</span>
            <Sparkles size={20} className="text-purple-400" />
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Autonomous recruitment execution logs, metrics summaries, and applicant funnels.
          </p>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        {[
          { label: "Total Candidates", value: metrics.total_candidates, icon: Users, color: "text-purple-400" },
          { label: "Applications", value: metrics.total_applications, icon: ClipboardList, color: "text-blue-400" },
          { label: "Shortlisted", value: metrics.shortlisted, icon: CheckCircle, color: "text-emerald-400" },
          { label: "Rejected", value: metrics.rejected, icon: XCircle, color: "text-red-400" },
          { label: "Interviewed", value: metrics.interviewed, icon: Video, color: "text-indigo-400" },
          { label: "Offers Sent", value: metrics.offers_sent, icon: FileSignature, color: "text-pink-400" },
          { label: "Offers Accepted", value: metrics.offers_accepted, icon: CheckCircle, color: "text-emerald-400" }
        ].map((c, i) => {
          const Icon = c.icon;
          return (
            <div key={i} className="glass-panel p-4 rounded-xl border border-gray-800 flex flex-col justify-between gap-3 bg-card/40">
              <div className="flex justify-between items-center">
                <span className="text-10 text-gray-400 font-bold uppercase tracking-wider">{c.label}</span>
                <Icon size={14} className={c.color} />
              </div>
              <span className="text-xl font-bold text-white">{c.value}</span>
            </div>
          );
        })}
      </div>

      {/* Video Streaming & Delivery Performance Monitoring */}
      {videoAnalytics && (
        <div className="glass-panel p-6 rounded-2xl border border-gray-800 bg-card/40 flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Video size={16} className="text-indigo-405" />
              <span>Video Playback & CDN Performance</span>
            </h2>
            <span className="text-[10px] font-mono text-gray-405 bg-gray-900 border border-gray-800 px-2 py-0.5 rounded uppercase font-bold tracking-wider">
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
                <span className="text-[9px] text-gray-500 font-medium">{stat.desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}


      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Funnel Chart */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-gray-800 flex flex-col gap-4 bg-card/40">
          <h2 className="text-sm font-bold text-white">Recruitment Funnel Conversion</h2>
          <div className="h-64 mt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={funnel} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis dataKey="stage" stroke="#9ca3af" fontSize={10} />
                <YAxis stroke="#9ca3af" fontSize={10} />
                <Tooltip 
                  contentStyle={{ backgroundColor: "#0f1019", border: "1px solid #374151" }} 
                  labelStyle={{ color: "#fff", fontSize: 11 }}
                  itemStyle={{ color: "#a78bfa", fontSize: 11 }}
                />
                <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                  {funnel.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Fraud Trends Panel */}
        <div className="glass-panel p-6 rounded-2xl border border-gray-800 bg-muted/40 flex flex-col gap-4">
          <h2 className="text-sm font-bold text-white">AI Proctoring Flags</h2>
          <div className="flex-1 flex flex-col justify-center gap-3">
            {fraudTrends.length === 0 ? (
              <div className="text-center py-12 text-gray-500 text-xs">No fraud logs registered.</div>
            ) : (
              fraudTrends.map((t, i) => (
                <div key={i} className="flex justify-between items-center text-xs p-3 rounded-xl border border-gray-800/40 bg-muted/40">
                  <span className="text-gray-400 capitalize">{t.event.replace("_", " ")}</span>
                  <span className="font-bold text-red-400 bg-red-950/20 px-2 py-0.5 rounded border border-red-900/30">
                    {t.count} flags
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

      </div>

      {/* Live Logs Terminal */}
      <div className="glass-panel p-6 rounded-2xl border border-gray-800 bg-card/40 flex flex-col gap-4">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <Terminal size={16} className="text-purple-400" />
          <span>Live Orchestration execution logs</span>
        </h2>
        
        <div className="h-52 overflow-y-auto bg-background border border-gray-800 rounded-xl p-4 font-mono text-11 flex flex-col gap-2.5">
          {logs.length === 0 ? (
            <span className="text-gray-600 italic">Logs stream starting... Waiting for agent triggers.</span>
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
