"use client";

import { useEffect, useState, useCallback } from "react";
import { AlertTriangle, X, CheckCircle2, Clock, ChevronDown, ChevronUp } from "lucide-react";
import { apiService } from "@/services/api";

interface HAQItem {
  id: number;
  action_type: string;
  title: string;
  description?: string;
  status: string;
  callback_key: string;
  created_at: string;
  expires_at?: string;
}

const ACTION_TYPE_ICONS: Record<string, string> = {
  captcha: "🤖",
  otp: "📱",
  "2fa": "🔐",
  payment: "💳",
  manual_review: "👁",
  recruiter_question: "💬",
};

const ACTION_TYPE_COLORS: Record<string, string> = {
  captcha: "border-amber-300 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-700/40",
  otp: "border-blue-300 bg-blue-50 dark:bg-blue-950/20 dark:border-blue-700/40",
  "2fa": "border-violet-300 bg-violet-50 dark:bg-violet-950/20 dark:border-violet-700/40",
  payment: "border-rose-300 bg-rose-50 dark:bg-rose-950/20 dark:border-rose-700/40",
  manual_review: "border-slate-300 bg-slate-50 dark:bg-slate-950/20 dark:border-slate-700/40",
  recruiter_question: "border-emerald-300 bg-emerald-50 dark:bg-emerald-950/20 dark:border-emerald-700/40",
};

export default function HumanActionQueue() {
  const [items, setItems] = useState<HAQItem[]>([]);
  const [expanded, setExpanded] = useState(true);
  const [dismissing, setDismissing] = useState<Set<string>>(new Set());
  const [inputs, setInputs] = useState<Record<string, string>>({});

  const fetchPending = useCallback(async () => {
    try {
      const data = await apiService.getHAQPending();
      if (Array.isArray(data)) setItems(data);
    } catch {
      // Silently fail — HAQ is non-critical
    }
  }, []);

  useEffect(() => {
    fetchPending();
    const interval = setInterval(fetchPending, 15000); // Poll every 15s
    return () => clearInterval(interval);
  }, [fetchPending]);

  const handleDismiss = async (callbackKey: string) => {
    setDismissing(prev => new Set(prev).add(callbackKey));
    try {
      await apiService.dismissHAQItem(callbackKey);
      setItems(prev => prev.filter(i => i.callback_key !== callbackKey));
    } catch {
      setDismissing(prev => { const s = new Set(prev); s.delete(callbackKey); return s; });
    }
  };

  const handleComplete = async (callbackKey: string) => {
    try {
      const val = inputs[callbackKey] || "";
      await apiService.completeHAQItem(callbackKey, {
        value: val,
        code: val,
        answer: val
      });
      setItems(prev => prev.filter(i => i.callback_key !== callbackKey));
      setInputs(prev => {
        const next = { ...prev };
        delete next[callbackKey];
        return next;
      });
    } catch (err) {
      console.error(err);
    }
  };

  const getTimeAgo = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    return `${Math.floor(mins / 60)}h ago`;
  };

  if (items.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 w-80 max-w-[calc(100vw-2rem)] flex flex-col gap-2">
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-2 rounded-xl bg-amber-500 text-white shadow-lg cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <AlertTriangle size={14} className="animate-pulse" />
          <span className="text-xs font-bold">
            {items.length} Action{items.length > 1 ? 's' : ''} Required
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-5 h-5 rounded-full bg-white/30 flex items-center justify-center text-[10px] font-bold">
            {items.length}
          </span>
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>

      {/* Items */}
      {expanded && items.map((item) => {
        const colorClass = ACTION_TYPE_COLORS[item.action_type] || ACTION_TYPE_COLORS.manual_review;
        const icon = ACTION_TYPE_ICONS[item.action_type] || "⚠️";
        const isDismissing = dismissing.has(item.callback_key);

        return (
          <div
            key={item.callback_key}
            className={`rounded-xl border p-3 shadow-lg backdrop-blur-sm ${colorClass} transition-all duration-300`}
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="flex items-center gap-2">
                <span className="text-base">{icon}</span>
                <div>
                  <p className="text-xs font-bold text-foreground leading-tight">{item.title}</p>
                  <p className="text-[10px] text-muted-foreground">
                    {item.action_type.replace(/_/g, ' ')} · {getTimeAgo(item.created_at)}
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleDismiss(item.callback_key)}
                disabled={isDismissing}
                className="p-1 rounded-full hover:bg-black/10 text-muted-foreground hover:text-foreground transition-colors cursor-pointer shrink-0"
              >
                <X size={12} />
              </button>
            </div>

            {item.description && (
              <p className="text-[10px] text-muted-foreground mb-2.5 leading-relaxed">{item.description}</p>
            )}

            {["otp", "captcha", "2fa", "recruiter_question"].includes(item.action_type) && (
              <input
                type="text"
                value={inputs[item.callback_key] || ""}
                onChange={(e) => setInputs(prev => ({ ...prev, [item.callback_key]: e.target.value }))}
                placeholder={
                  item.action_type === "otp" ? "Enter OTP Code..." :
                  item.action_type === "captcha" ? "Enter CAPTCHA..." :
                  item.action_type === "2fa" ? "Enter 2FA Code..." :
                  "Enter your answer..."
                }
                className="w-full px-2.5 py-1.5 mb-2.5 text-[11px] border border-amber-300 rounded-lg bg-white/70 dark:bg-black/35 text-slate-800 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
              />
            )}

            <div className="flex items-center gap-2">
              <button
                onClick={() => handleComplete(item.callback_key)}
                className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-[10px] font-bold transition-colors cursor-pointer"
              >
                <CheckCircle2 size={10} /> Complete Now
              </button>
              {item.expires_at && (
                <div className="flex items-center gap-1 text-[9px] text-muted-foreground">
                  <Clock size={9} />
                  {new Date(item.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
