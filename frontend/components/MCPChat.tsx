"use client";

import { useState, useEffect, useRef } from "react";
import { apiService } from "@/services/api";
import {
  X, Send, Bot, User, Loader2, Sparkles, ChevronRight,
  Mic, Maximize2, Minimize2, RotateCcw, ArrowUp,
} from "lucide-react";
import Link from "next/link";
import AIActionCard from "@/components/AIActionCard";

export type MCPMode = "resume" | "skill-lab" | "job-agent";

interface Message {
  sender: "user" | "ai";
  text: string;
  timestamp: Date;
  actions?: { label: string; href: string }[];
  action_cards?: any[];
  memory_updated?: boolean;
}

interface MCPConfig {
  label: string;
  color: string;          // tailwind text color
  bgColor: string;        // tailwind bg color for header/button
  gradFrom: string;
  gradTo: string;
  borderColor: string;
  iconBg: string;
  systemContext: string;
  placeholder: string;
  starters: string[];
}

const MCP_CONFIGS: Record<MCPMode, MCPConfig> = {
  "resume": {
    label: "Resume MCP",
    color: "text-violet-600 dark:text-violet-400",
    bgColor: "bg-violet-600",
    gradFrom: "from-violet-600",
    gradTo: "to-purple-700",
    borderColor: "border-violet-500/30",
    iconBg: "bg-violet-100 dark:bg-violet-950/50",
    systemContext:
      "You are a professional resume expert and career coach for VidyaMarg AI platform. " +
      "Help users optimize their resume for ATS systems, write compelling summaries, highlight achievements " +
      "with quantified metrics, tailor resumes for specific roles, and improve overall resume quality. " +
      "Give specific, actionable advice. Be concise and professional.",
    placeholder: "Ask about your resume, ATS tips, formatting…",
    starters: [
      "How do I optimize my resume for ATS?",
      "Help me write a stronger professional summary",
      "What action verbs should I use?",
      "Review my skills section",
    ],
  },
  "skill-lab": {
    label: "Skill Lab MCP",
    color: "text-emerald-600 dark:text-emerald-400",
    bgColor: "bg-emerald-600",
    gradFrom: "from-emerald-600",
    gradTo: "to-teal-700",
    borderColor: "border-emerald-500/30",
    iconBg: "bg-emerald-100 dark:bg-emerald-950/50",
    systemContext:
      "You are an expert learning advisor and educational coach for VidyaMarg AI skill lab. " +
      "Help users choose the right courses, build personalized learning paths, understand technical concepts, " +
      "plan skill development strategies, and transition careers through education. " +
      "Give clear explanations with examples. Be encouraging and specific.",
    placeholder: "Ask about courses, learning paths, concepts…",
    starters: [
      "Recommend courses for my career goals",
      "Create a 3-month learning plan for me",
      "Explain React hooks with examples",
      "What certifications should I pursue?",
    ],
  },
  "job-agent": {
    label: "Job Agent MCP",
    color: "text-blue-600 dark:text-blue-400",
    bgColor: "bg-blue-600",
    gradFrom: "from-blue-600",
    gradTo: "to-indigo-700",
    borderColor: "border-blue-500/30",
    iconBg: "bg-blue-100 dark:bg-blue-950/50",
    systemContext:
      "You are an expert career advisor and job search strategist for VidyaMarg AI platform. " +
      "Help users find relevant jobs, craft compelling cover letters, prepare for technical and behavioral interviews, " +
      "negotiate salaries, evaluate job offers, and develop long-term career strategies. " +
      "Be practical, data-driven, and encouraging.",
    placeholder: "Ask about jobs, interviews, salary negotiation…",
    starters: [
      "How do I prepare for a system design interview?",
      "Help me write a cover letter for a tech role",
      "How do I negotiate a better salary?",
      "What companies hire remote developers?",
    ],
  },
};

interface MCPChatProps {
  mode: MCPMode;
  /** Optional extra context to prepend (e.g. user's current resume score) */
  contextHint?: string;
}

export default function MCPChat({ mode, contextHint }: MCPChatProps) {
  const config = MCP_CONFIGS[mode];
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = `${Math.min(ta.scrollHeight, 120)}px`;
    }
  }, [query]);

  // Welcome message when opened for first time
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([{
        sender: "ai",
        text: `Hi! I'm your **${config.label}** assistant 👋\n\nI can help you with personalized guidance. Try one of the quick starters below or ask me anything!`,
        timestamp: new Date(),
      }]);
    }
  }, [isOpen]);

  const startListening = () => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { alert("Speech recognition not supported. Please use Chrome."); return; }
    if (isListening) { recognitionRef.current?.stop(); setIsListening(false); return; }
    const rec = new SR();
    rec.continuous = false;
    rec.interimResults = false;
    rec.lang = "en-US";
    rec.onstart = () => setIsListening(true);
    rec.onresult = (e: any) => {
      const transcript = e.results[0][0].transcript;
      setQuery((p) => p + (p ? " " : "") + transcript);
    };
    rec.onend = () => setIsListening(false);
    rec.onerror = () => setIsListening(false);
    recognitionRef.current = rec;
    rec.start();
  };

  const handleSend = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const userMsg: Message = { sender: "user", text: trimmed, timestamp: new Date() };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setQuery("");
    setLoading(true);

    try {
      const history = updatedMessages.slice(0, -1).map((m) => ({
        role: m.sender === "user" ? ("user" as const) : ("assistant" as const),
        content: m.text,
      }));

      const result = await apiService.mcpChat(trimmed, mode, history, contextHint || undefined);

      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          text: result.response,
          timestamp: new Date(),
          actions: result.actions?.length > 0 ? result.actions : undefined,
          action_cards: result.action_cards?.length > 0 ? result.action_cards : undefined,
          memory_updated: result.memory_updated,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          sender: "ai",
          text: "Sorry, I ran into an issue. Please try again.",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend(query);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setTimeout(() => {
      setMessages([{
        sender: "ai",
        text: `Chat cleared! I'm still here to help with ${config.label} questions. What would you like to know?`,
        timestamp: new Date(),
      }]);
    }, 100);
  };

  // Format message text (bold **text**, line breaks)
  const formatText = (text: string) => {
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      return <span key={i}>{part}</span>;
    });
  };

  const panelWidth = isExpanded ? "w-[420px]" : "w-[340px]";

  return (
    <>
      {/* Floating Trigger Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className={`
            fixed bottom-6 right-6 z-50
            flex items-center gap-2 px-4 py-3 rounded-2xl
            bg-gradient-to-br ${config.gradFrom} ${config.gradTo}
            text-white shadow-xl hover:shadow-2xl
            hover:scale-105 active:scale-95
            transition-all duration-200 cursor-pointer
            group
          `}
          title={`Open ${config.label}`}
        >
          <div className="relative">
            <Sparkles size={18} className="animate-pulse" />
            <span className="absolute -top-1 -right-1 w-2 h-2 bg-white rounded-full opacity-80 animate-ping" />
          </div>
          <span className="text-xs font-bold tracking-wide">{config.label}</span>
        </button>
      )}

      {/* Chat Panel */}
      {isOpen && (
        <div
          className={`
            fixed bottom-4 right-4 z-50
            ${panelWidth} h-[580px]
            bg-app-bg border border-app-border rounded-2xl
            shadow-2xl flex flex-col overflow-hidden
            transition-all duration-300
          `}
          style={{ boxShadow: "0 25px 60px rgba(0,0,0,0.18), 0 0 0 1px rgba(0,0,0,0.05)" }}
        >
          {/* Header */}
          <div className={`flex items-center gap-3 px-4 py-3 bg-gradient-to-r ${config.gradFrom} ${config.gradTo} shrink-0`}>
            <div className="w-8 h-8 rounded-xl bg-white/20 flex items-center justify-center backdrop-blur-sm">
              <Sparkles size={16} className="text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold text-white leading-tight">{config.label}</p>
              <p className="text-[10px] text-white/70 leading-tight">AI-powered · Context-aware</p>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={clearChat}
                className="w-7 h-7 rounded-lg bg-white/15 hover:bg-white/25 flex items-center justify-center transition-colors cursor-pointer"
                title="Clear chat"
              >
                <RotateCcw size={13} className="text-white" />
              </button>
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-7 h-7 rounded-lg bg-white/15 hover:bg-white/25 flex items-center justify-center transition-colors cursor-pointer"
                title={isExpanded ? "Collapse" : "Expand"}
              >
                {isExpanded ? <Minimize2 size={13} className="text-white" /> : <Maximize2 size={13} className="text-white" />}
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="w-7 h-7 rounded-lg bg-white/15 hover:bg-white/25 flex items-center justify-center transition-colors cursor-pointer"
                title="Close"
              >
                <X size={13} className="text-white" />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 scroll-smooth">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex gap-2 ${msg.sender === "user" ? "flex-row-reverse" : ""}`}>
                {/* Avatar */}
                <div className={`
                  w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5
                  ${msg.sender === "user"
                    ? `${config.bgColor} text-white`
                    : "bg-app-card border border-app-border text-app-text"
                  }
                `}>
                  {msg.sender === "user" ? <User size={13} /> : <Bot size={13} />}
                </div>

                {/* Bubble */}
                <div className={`
                  max-w-[82%] px-3 py-2.5 rounded-xl text-xs leading-relaxed flex flex-col gap-1.5
                  ${msg.sender === "user"
                    ? "bg-blue-50 dark:bg-blue-950/20 text-app-text border border-blue-100 dark:border-blue-900/20 rounded-tr-sm"
                    : "bg-app-card text-app-text border border-app-border rounded-tl-sm shadow-sm"
                  }
                `}>
                  <div className="whitespace-pre-wrap leading-relaxed">
                    {formatText(msg.text)}
                  </div>

                  {msg.actions && (
                    <div className="flex flex-wrap gap-1.5 pt-1.5 border-t border-app-border mt-0.5">
                      {msg.actions.map((act) => (
                        <Link
                          key={act.label}
                          href={act.href}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800/30 text-blue-600 dark:text-blue-400 text-[11px] font-semibold hover:bg-blue-100 dark:hover:bg-blue-950/30 transition-colors"
                        >
                          {act.label} <ChevronRight size={10} />
                        </Link>
                      ))}
                    </div>
                  )}

                  {msg.action_cards && msg.action_cards.length > 0 && (
                    <div className="flex flex-col gap-2 pt-2 border-t border-app-border mt-1 w-full">
                      {msg.action_cards.map((card, idx) => (
                        <AIActionCard key={idx} card={card} />
                      ))}
                    </div>
                  )}

                  {msg.memory_updated && (
                    <div className="flex items-center gap-1 text-[9px] text-violet-600 dark:text-violet-400 font-semibold self-start mt-0.5">
                      <span>🧠 Memory updated</span>
                    </div>
                  )}

                  <span className="text-[10px] text-app-text-muted self-end">
                    {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
              </div>
            ))}

            {/* Loading indicator */}
            {loading && (
              <div className="flex gap-2">
                <div className="w-7 h-7 rounded-lg bg-app-card border border-app-border flex items-center justify-center shrink-0">
                  <Bot size={13} className="text-app-text" />
                </div>
                <div className="px-3 py-2.5 rounded-xl bg-app-card border border-app-border rounded-tl-sm shadow-sm flex items-center gap-2">
                  <Loader2 size={13} className={`animate-spin ${config.color}`} />
                  <span className="text-[11px] text-app-text-muted">Thinking…</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Starters (shown only when few messages) */}
          {messages.length <= 1 && !loading && (
            <div className="px-3 pb-2 flex flex-wrap gap-1.5 shrink-0">
              {config.starters.map((s) => (
                <button
                  key={s}
                  onClick={() => handleSend(s)}
                  className={`
                    text-[11px] px-2.5 py-1.5 rounded-lg border cursor-pointer
                    bg-app-surface border-app-border text-app-text-secondary
                    hover:border-current hover:text-app-text
                    ${config.color} transition-all duration-150
                  `}
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input Bar */}
          <div className="px-3 pb-3 shrink-0">
            <div className="flex items-end gap-2 bg-app-card border border-app-border rounded-xl px-3 py-2 focus-within:border-app-border-hover transition-colors">
              <textarea
                ref={textareaRef}
                rows={1}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={config.placeholder}
                className="flex-1 bg-transparent resize-none border-none outline-none focus:ring-0 text-xs text-app-text placeholder-app-text-muted leading-relaxed max-h-28 py-0.5"
                disabled={loading}
              />
              <div className="flex items-center gap-1 shrink-0 self-end pb-0.5">
                <button
                  onClick={startListening}
                  className={`
                    w-7 h-7 rounded-lg flex items-center justify-center transition-all cursor-pointer
                    ${isListening
                      ? "bg-red-500 text-white animate-pulse"
                      : "text-app-text-muted hover:text-app-text hover:bg-app-surface"
                    }
                  `}
                  title="Voice input"
                >
                  <Mic size={14} />
                </button>
                <button
                  onClick={() => handleSend(query)}
                  disabled={!query.trim() || loading}
                  className={`
                    w-7 h-7 rounded-lg flex items-center justify-center transition-all
                    ${query.trim() && !loading
                      ? `${config.bgColor} text-white hover:opacity-90 hover:scale-105 active:scale-95 cursor-pointer shadow-sm`
                      : "bg-app-surface text-app-text-muted cursor-not-allowed"
                    }
                  `}
                  title="Send"
                >
                  <ArrowUp size={13} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
