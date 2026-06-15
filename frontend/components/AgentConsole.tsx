"use client";

import { useEffect, useState, useRef } from "react";
import { Terminal, Play, CheckCircle2, AlertTriangle, XCircle, Info, RefreshCw } from "lucide-react";

interface LogMessage {
  message: string;
  status: "info" | "success" | "warning" | "error";
  timestamp: string;
}

interface AgentConsoleProps {
  runId: number | null;
  status: string;
  logs: LogMessage[];
  onStartAgent: () => void;
  onRunComplete: () => void;
}

export default function AgentConsole({
  runId,
  status,
  logs: initialLogs,
  onStartAgent,
  onRunComplete
}: AgentConsoleProps) {
  const [logs, setLogs] = useState<LogMessage[]>(initialLogs);
  const [agentStatus, setAgentStatus] = useState(status);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    setLogs(initialLogs);
    setAgentStatus(status);
  }, [initialLogs, status]);

  // Connect to WebSocket when runId changes and status is running
  useEffect(() => {
    if (!runId || agentStatus !== "running") {
      if (socketRef.current) {
        socketRef.current.close();
      }
      return;
    }

    const wsUrl = `ws://127.0.0.1:8000/api/v1/ws/agent/${runId}`;
    console.log("Connecting Agent Console to WebSocket:", wsUrl);
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const newLog: LogMessage = {
          message: data.message,
          status: data.status,
          timestamp: data.timestamp
        };
        
        setLogs((prev) => {
          if (prev.some((l) => l.message === newLog.message)) return prev;
          return [...prev, newLog];
        });

        if (data.message.includes("[Completed]")) {
          setAgentStatus("completed");
          onRunComplete();
        } else if (data.message.includes("[Failed]")) {
          setAgentStatus("failed");
        }
      } catch (err) {
        console.error("Error parsing WebSocket log:", err);
      }
    };

    ws.onerror = (err) => {
      if (ws.readyState !== WebSocket.CLOSED && ws.readyState !== WebSocket.CLOSING) {
        console.error("Agent Console WebSocket error:", err);
      }
    };

    ws.onclose = () => {
      console.log("Agent Console WebSocket closed");
    };

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [runId, agentStatus, onRunComplete]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "success":
        return <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />;
      case "warning":
        return <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />;
      case "error":
        return <XCircle className="w-4 h-4 text-red-400 shrink-0" />;
      default:
        return <Info className="w-4 h-4 text-blue-400 shrink-0" />;
    }
  };

  const getLogTextColor = (status: string) => {
    switch (status) {
      case "success":
        return "text-emerald-400 font-medium";
      case "warning":
        return "text-amber-400 font-medium";
      case "error":
        return "text-red-400 font-medium";
      default:
        return "text-slate-300";
    }
  };

  const latestLog = logs[logs.length - 1];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 flex items-center justify-between shadow-md w-full font-mono text-xs select-none">
      <div className="flex items-center gap-3 overflow-hidden min-w-0">
        <div className="flex items-center gap-1.5 shrink-0 border-r border-slate-800 pr-3 mr-1">
          <Terminal className="w-3.5 h-3.5 text-blue-400" />
          <span className="text-slate-400 font-bold tracking-tight">AGENT:</span>
        </div>
        
        {latestLog ? (
          <div className="flex items-center gap-2 overflow-hidden min-w-0">
            {getStatusIcon(latestLog.status)}
            <span className={`${getLogTextColor(latestLog.status)} truncate`}>
              {latestLog.message}
            </span>
          </div>
        ) : (
          <span className="text-slate-500 italic">
            Agent is idle. Run Agent to discover live opportunities.
          </span>
        )}
      </div>

      <div className="flex items-center gap-3 shrink-0 ml-4">
        {agentStatus === "running" ? (
          <div className="flex items-center gap-2 bg-blue-950/50 border border-blue-900/50 px-2.5 py-1 rounded-lg">
            <RefreshCw className="w-3 h-3 text-blue-400 animate-spin" />
            <span className="text-[10px] text-blue-400 font-bold uppercase tracking-wider">Active</span>
          </div>
        ) : agentStatus === "completed" ? (
          <div className="flex items-center gap-2 bg-emerald-950/50 border border-emerald-900/50 px-2.5 py-1 rounded-lg">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            <span className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider">Ready</span>
          </div>
        ) : agentStatus === "failed" ? (
          <div className="flex items-center gap-2 bg-red-950/50 border border-red-900/50 px-2.5 py-1 rounded-lg">
            <XCircle className="w-3 h-3 text-red-400" />
            <span className="text-[10px] text-red-400 font-bold uppercase tracking-wider">Failed</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 bg-slate-950/50 border border-slate-800 px-2.5 py-1 rounded-lg">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-pulse" />
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Idle</span>
          </div>
        )}
      </div>
    </div>
  );
}
