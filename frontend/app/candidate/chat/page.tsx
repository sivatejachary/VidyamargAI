"use client";

import { useState, useEffect, useRef } from "react";
import { useAuthStore } from "@/store/authStore";
import { apiService } from "@/services/api";
import {
  Sparkles, Mic, Send, Briefcase, FileText, ClipboardList,
  User, Bot, Loader2, ChevronRight, Globe, BarChart3, Target,
  Rocket, Plus, ArrowUp, GraduationCap, BookOpen, Brain,
  TrendingUp, Zap, X
} from "lucide-react";
import Link from "next/link";
import AgentActivityFeed from "@/components/AgentActivityFeed";
import HumanActionQueue from "@/components/HumanActionQueue";
import AIActionCard from "@/components/AIActionCard";

interface Message {
  sender: "user" | "tush";
  text: string;
  timestamp: Date;
  actions?: { label: string; href: string }[];
  action_cards?: any[];
  memory_updated?: boolean;
}



const quickSuggestions = [
  {
    title: "Discover Career Opportunities",
    query: "Show me available job openings matching my profile",
    icon: Briefcase,
    color: "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/30",
  },
  {
    title: "Track My Applications",
    query: "What is the status of my job applications?",
    icon: ClipboardList,
    color: "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30",
  },
  {
    title: "Analyze My Skill Gaps",
    query: "Analyze my skill gaps and recommend what to learn next",
    icon: BarChart3,
    color: "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30",
  },
  {
    title: "Personalized Career Roadmap",
    query: "Create a personalized career development roadmap for me",
    icon: Target,
    color: "text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-950/30",
  },
  {
    title: "Interview Preparation",
    query: "Prepare me for an upcoming technical interview",
    icon: Rocket,
    color: "text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/30",
  },
  {
    title: "Remote & Global Jobs",
    query: "Show me remote job opportunities worldwide in my field",
    icon: Globe,
    color: "text-cyan-600 dark:text-cyan-400 bg-cyan-50 dark:bg-cyan-950/30",
  },
];

export default function TushAIChat() {
  const { fullName } = useAuthStore();
  const [query, setQuery] = useState("");
  const [isChatActive, setIsChatActive] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const landingTextareaRef = useRef<HTMLTextAreaElement>(null);
  const chatTextareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = isChatActive ? chatTextareaRef.current : landingTextareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [query, isChatActive]);

  // Speech recognition
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  const startListening = () => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { alert("Speech recognition not supported. Use Chrome."); return; }
    if (isListening) { recognitionRef.current?.stop(); setIsListening(false); return; }
    const rec = new SR();
    rec.continuous = true; rec.interimResults = true; rec.lang = "en-US";
    rec.onstart = () => setIsListening(true);
    rec.onresult = (e: any) => {
      let t = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) t += e.results[i][0].transcript;
      }
      if (t) setQuery((p) => p + (p.endsWith(" ") || p === "" ? "" : " ") + t);
    };
    rec.onerror = () => setIsListening(false);
    rec.onend = () => setIsListening(false);
    recognitionRef.current = rec;
    rec.start();
  };

  useEffect(() => {
    return () => { recognitionRef.current?.stop(); };
  }, []);

  // File attachments
  const [attachments, setAttachments] = useState<File[]>([]);
  const landingFileRef = useRef<HTMLInputElement>(null);
  const chatFileRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) setAttachments((p) => [...p, ...Array.from(e.target.files!)]);
  };
  const removeAttachment = (idx: number) => setAttachments((p) => p.filter((_, i) => i !== idx));

  const firstName = fullName ? fullName.split(" ")[0] : "User";
  const capitalizedFirstName = firstName.charAt(0).toUpperCase() + firstName.slice(1);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (textToSend: string) => {
    let finalQuery = textToSend;
    let messageText = textToSend;

    if (attachments.length > 0) {
      const names = attachments.map((f) => f.name).join(", ");
      messageText = textToSend ? `${textToSend}\n\n[Attached: ${names}]` : `[Attached: ${names}]`;
      finalQuery = textToSend ? `${textToSend} (with files: ${names})` : `Processing files: ${names}`;
    }
    if (!messageText.trim()) return;

    setIsChatActive(true);
    const userMsg: Message = { sender: "user", text: messageText, timestamp: new Date() };
    const updated = [...messages, userMsg];
    setMessages(updated);
    setQuery("");
    setAttachments([]);
    setLoading(true);

    try {
      const history = updated.slice(0, -1).map((m) => ({
        role: m.sender === "user" ? ("user" as const) : ("assistant" as const),
        content: m.text,
      }));
      const result = await apiService.mcpChat(finalQuery, "general", history);
      setMessages((p) => [...p, {
        sender: "tush",
        text: result.response,
        timestamp: new Date(),
        actions: result.actions?.length > 0 ? result.actions : undefined,
        action_cards: result.action_cards?.length > 0 ? result.action_cards : undefined,
        memory_updated: result.memory_updated,
      }]);
    } catch {
      setMessages((p) => [...p, {
        sender: "tush",
        text: "I encountered an issue. Please try again or use one of the MCP tools below.",
        timestamp: new Date(),
      }]);
    } finally {
      setLoading(false);
    }
  };

  const InputBox = ({ isLanding }: { isLanding: boolean }) => (
    <div className="flex flex-col bg-card border border-border rounded-2xl p-2 pl-4 pr-3 shadow-custom-glass hover:border-border-hover dark:hover:border-neutral-700 focus-within:border-primary/50 dark:focus-within:border-primary/40 focus-within:shadow-[0_8px_30px_rgba(59,130,246,0.08)] transition-all duration-300 w-full">
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 px-1 pt-2 pb-1.5 border-b border-gray-100 dark:border-zinc-800 mb-2">
          {attachments.map((file, idx) => (
            <div key={idx} className="flex items-center gap-1.5 pl-2 pr-1.5 py-1 rounded-lg bg-gray-50 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 text-xs text-gray-700 dark:text-zinc-300">
              {file.type.startsWith("image/") ? (
                <img src={URL.createObjectURL(file)} alt={file.name} className="w-4 h-4 rounded object-cover" />
              ) : (
                <FileText size={13} className="text-blue-500" />
              )}
              <span className="max-w-28 truncate font-medium">{file.name}</span>
              <button onClick={() => removeAttachment(idx)} className="w-4 h-4 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-600 cursor-pointer"><X size={10} /></button>
            </div>
          ))}
        </div>
      )}
      <div className="flex items-end gap-2 w-full min-h-10">
        <button
          onClick={() => isLanding ? landingFileRef.current?.click() : chatFileRef.current?.click()}
          className="flex items-center justify-center w-9 h-9 rounded-full text-gray-400 hover:text-gray-600 dark:text-zinc-400 dark:hover:text-zinc-200 hover:bg-gray-100 dark:hover:bg-zinc-800/50 transition-colors shrink-0 mb-0.5 cursor-pointer"
        ><Plus size={20} /></button>
        <input type="file" ref={isLanding ? landingFileRef : chatFileRef} onChange={handleFileChange} multiple accept="image/*,.pdf,.doc,.docx,.txt" className="hidden" />

        <div className="flex-1 min-w-0 py-1.5 self-center">
          <textarea
            ref={isLanding ? landingTextareaRef : chatTextareaRef}
            rows={1}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(query); } }}
            placeholder="Ask Tush AI anything about your career, jobs, learning..."
            className="chat-input-textarea w-full bg-transparent resize-none border-none outline-none focus:ring-0 text-sm text-foreground placeholder-muted-foreground py-1 max-h-48 h-6"
          />
        </div>

        <div className="flex items-center gap-1.5 shrink-0 self-center">
          <button
            onClick={startListening}
            className={`flex items-center justify-center w-9 h-9 rounded-full transition-all duration-300 cursor-pointer ${isListening ? "bg-red-500 text-white animate-pulse shadow-[0_0_12px_rgba(239,68,68,0.5)]" : "text-gray-400 hover:text-gray-600 dark:text-zinc-400 dark:hover:text-zinc-200 hover:bg-gray-100 dark:hover:bg-zinc-800/50"}`}
          ><Mic size={18} /></button>
          <button
            onClick={() => handleSend(query)}
            disabled={!query.trim() && attachments.length === 0}
            className={`flex items-center justify-center w-9 h-9 rounded-full transition-all duration-200 shrink-0 ${query.trim() || attachments.length > 0 ? "bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:scale-105 active:scale-95 cursor-pointer" : "bg-slate-100 dark:bg-zinc-800 text-slate-400 dark:text-slate-600 cursor-not-allowed"}`}
          ><ArrowUp size={16} /></button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="w-full h-full min-h-screen bg-app-bg text-app-text flex flex-col font-sans transition-colors duration-300 relative">

      {!isChatActive ? (
        <div className="flex-1 flex flex-col items-center justify-start px-6 py-10 max-w-3xl mx-auto w-full">

          {/* Hero */}
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg mb-4">
            <Sparkles size={26} className="text-white animate-pulse" />
          </div>
          <p className="text-sm text-app-text-secondary font-medium mb-1">
            Welcome back, <span className="text-blue-600 dark:text-blue-400 font-semibold">{capitalizedFirstName}</span> 👋
          </p>
          <h1 className="text-2xl md:text-3xl font-extrabold text-app-text tracking-tight text-center leading-tight mb-1">
            How can <span className="text-blue-600 dark:text-blue-400">Tush AI</span> help you today?
          </h1>
          <p className="text-xs text-app-text-muted text-center mb-8">
            Your AI-powered career companion
          </p>

          {/* Input */}
          <div className="w-full max-w-2xl mb-8">
            <InputBox isLanding={true} />
          </div>



          {/* Quick Suggestions */}
          <div className="w-full max-w-3xl">
            <div className="flex items-center gap-2 mb-4">
              <div className="h-px flex-1 bg-app-border" />
              <p className="text-xs font-bold text-app-text-muted uppercase tracking-widest px-3">Quick Suggestions</p>
              <div className="h-px flex-1 bg-app-border" />
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
              {quickSuggestions.map((s) => {
                const Icon = s.icon;
                return (
                  <button
                    key={s.title}
                    onClick={() => handleSend(s.query)}
                    className="flex items-center gap-3 px-4 py-3 rounded-xl bg-app-card border border-app-border text-left hover:shadow-md hover:border-slate-300 dark:hover:border-slate-700 hover:scale-[1.01] transition-all duration-200 cursor-pointer group"
                  >
                    <div className={`p-2 rounded-lg shrink-0 ${s.color}`}><Icon size={14} /></div>
                    <span className="text-xs font-semibold text-app-text-secondary group-hover:text-app-text transition-colors leading-snug">{s.title}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        // Active Chat
        <div className="flex-1 flex flex-col md:flex-row h-full max-w-6xl w-full mx-auto p-4 md:p-6 gap-6 overflow-hidden">
          {/* Main Chat Panel */}
          <div className="flex-1 flex flex-col h-full justify-between overflow-hidden">
            {/* Chat Header */}
            <div className="flex items-center justify-between pb-3 border-b border-app-border">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 bg-gradient-to-br from-blue-600 to-indigo-600 text-white rounded-xl flex items-center justify-center shadow-md">
                  <Sparkles size={16} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-app-text">Tush AI</h2>
                  <span className="text-[10px] text-emerald-500 font-medium flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
                    Active Session
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => { setIsChatActive(false); setMessages([]); }}
                  className="text-xs font-semibold text-app-text-secondary hover:text-app-text px-3 py-1.5 rounded-lg border border-app-border hover:bg-app-surface transition-colors cursor-pointer"
                >New Chat</button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto py-5 space-y-4 scroll-smooth pr-1">
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex gap-3 max-w-[85%] ${msg.sender === "user" ? "ml-auto flex-row-reverse" : "mr-auto"}`}>
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${msg.sender === "user" ? "bg-blue-600 text-white" : "bg-app-card text-blue-600 dark:text-blue-400 border border-app-border"}`}>
                    {msg.sender === "user" ? <User size={14} /> : <Bot size={14} />}
                  </div>
                  <div className={`p-3.5 rounded-2xl flex flex-col gap-2 text-sm leading-relaxed border ${msg.sender === "user" ? "bg-blue-50 dark:bg-blue-950/20 text-app-text border-blue-100 dark:border-blue-900/30 rounded-tr-sm" : "bg-app-card text-app-text border-app-border rounded-tl-sm shadow-sm"}`}>
                    <div className="whitespace-pre-wrap">{msg.text}</div>
                    {msg.actions && (
                      <div className="flex flex-wrap gap-2 pt-2 mt-1 border-t border-app-border">
                        {msg.actions.map((act) => (
                          <Link key={act.label} href={act.href} className="px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-950/20 hover:bg-blue-100 border border-blue-200 dark:border-blue-800/30 text-blue-600 dark:text-blue-400 text-xs font-semibold transition-all inline-flex items-center gap-1">
                            {act.label} <ChevronRight size={12} />
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
              {loading && (
                <div className="flex gap-3 mr-auto">
                  <div className="w-8 h-8 rounded-lg bg-app-card border border-app-border flex items-center justify-center text-blue-600 dark:text-blue-400"><Bot size={14} /></div>
                  <div className="p-3.5 rounded-2xl bg-app-card border border-app-border rounded-tl-sm shadow-sm flex items-center gap-2">
                    <Loader2 size={14} className="animate-spin text-blue-600 dark:text-blue-400" />
                    <span className="text-xs text-app-text-muted font-medium">Tush AI is thinking...</span>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Footer */}
            <div className="pt-2 pb-1">
              <InputBox isLanding={false} />
              <p className="text-[10px] text-app-text-muted text-center mt-2">
                Tush AI · Personalized career guidance
              </p>
            </div>
          </div>

          {/* Activity Feed Sidebar (Desktop) */}
          <div className="hidden md:block w-80 shrink-0 border-l border-app-border pl-6 overflow-y-auto">
            <AgentActivityFeed maxItems={15} />
          </div>
        </div>
      )}
      <HumanActionQueue />
    </div>
  );
}
