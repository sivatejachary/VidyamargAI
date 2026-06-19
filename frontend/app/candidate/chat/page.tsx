"use client";

import { useState, useEffect, useRef } from "react";
import { useAuthStore } from "@/store/authStore";
import { apiService } from "@/services/api";
import {
  Sparkles, Mic, Send, Briefcase, FileText, ClipboardList,
  User, Bot, Loader2, ChevronRight, Globe, BarChart3, Target,
  Rocket, Plus, ArrowUp, GraduationCap, BookOpen, Brain,
  TrendingUp, Zap, X, Pin, PinOff, Archive, Trash2, Edit2, Check,
  PanelLeftClose, PanelLeftOpen, Search, Download, FileUp
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

  // Sidebar history state
  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [isHistoryOpen, setIsHistoryOpen] = useState(true);
  const [sessionsPage, setSessionsPage] = useState(1);
  const [sessionsHasMore, setSessionsHasMore] = useState(true);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  
  // Inline rename state
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editTitleText, setEditTitleText] = useState("");

  // Export dropdown
  const [showExportMenu, setShowExportMenu] = useState(false);

  // Load chat sessions on mount and when search query changes
  useEffect(() => {
    fetchSessions(1, true);
  }, [searchQuery]);

  const fetchSessions = async (page = 1, replace = false) => {
    try {
      setLoadingSessions(true);
      const res = await apiService.getMcpSessions(page, 20, searchQuery);
      if (replace) {
        setSessions(res.sessions || []);
      } else {
        setSessions((prev) => {
          const existingIds = new Set(prev.map((s) => s.id));
          const filtered = (res.sessions || []).filter((s: any) => !existingIds.has(s.id));
          return [...prev, ...filtered];
        });
      }
      setSessionsHasMore(page < (res.pages || 1));
      setSessionsPage(page);
    } catch (err) {
      console.error("Failed to load chat sessions:", err);
    } finally {
      setLoadingSessions(false);
    }
  };

  const handleSessionsScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    if (scrollHeight - scrollTop - clientHeight < 40 && sessionsHasMore && !loadingSessions) {
      fetchSessions(sessionsPage + 1);
    }
  };

  const selectSession = async (sessionId: string) => {
    try {
      setLoading(true);
      setIsChatActive(true);
      setActiveSessionId(sessionId);
      const dbMsgs = await apiService.getMcpSessionMessages(sessionId);
      const formatted = dbMsgs.map((m: any) => ({
        sender: m.sender === "user" ? ("user" as const) : ("tush" as const),
        text: m.text,
        timestamp: new Date(m.created_at),
        actions: m.actions,
        action_cards: m.action_cards,
        memory_updated: m.memory_updated
      }));
      setMessages(formatted);
    } catch (err) {
      console.error("Failed to load session messages:", err);
    } finally {
      setLoading(false);
    }
  };

  const startNewChat = () => {
    setActiveSessionId(null);
    setMessages([]);
    setIsChatActive(false);
  };

  const togglePinSession = async (sessionId: string, currentPinned: boolean, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiService.pinMcpSession(sessionId, !currentPinned);
      fetchSessions(1, true);
    } catch (err) {
      console.error("Failed to toggle pin:", err);
    }
  };

  const archiveSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiService.archiveMcpSession(sessionId, true);
      if (activeSessionId === sessionId) {
        startNewChat();
      }
      fetchSessions(1, true);
    } catch (err) {
      console.error("Failed to archive session:", err);
    }
  };

  const deleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this conversation?")) return;
    try {
      await apiService.deleteMcpSession(sessionId);
      if (activeSessionId === sessionId) {
        startNewChat();
      }
      fetchSessions(1, true);
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  };

  const startRename = (sessionId: string, currentTitle: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingSessionId(sessionId);
    setEditTitleText(currentTitle);
  };

  const saveRename = async (sessionId: string) => {
    if (!editTitleText.trim()) return;
    try {
      await apiService.renameMcpSession(sessionId, editTitleText.trim());
      setEditingSessionId(null);
      fetchSessions(1, true);
    } catch (err) {
      console.error("Failed to rename session:", err);
    }
  };

  const handleExportMarkdown = () => {
    let md = `# Ask Tush AI - Conversation Export\n\n`;
    if (activeSessionId) {
      const sess = sessions.find((s) => s.id === activeSessionId);
      if (sess) {
        md = `# Ask Tush AI - ${sess.title}\n\n`;
      }
    }
    messages.forEach((m) => {
      const role = m.sender === "user" ? "User" : "Tush AI";
      md += `### **${role}** _(${m.timestamp.toLocaleString()})_\n\n${m.text}\n\n`;
      if (m.action_cards && m.action_cards.length > 0) {
        md += `*Action Cards generated:*\n`;
        m.action_cards.forEach((c: any) => {
          md += `- **${c.title}**: ${c.subtitle} [${c.action_label}](${c.action_href})\n`;
        });
        md += `\n`;
      }
    });

    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `chat-history-${activeSessionId || "new"}.md`;
    a.click();
    URL.revokeObjectURL(url);
    setShowExportMenu(false);
  };

  const handleExportPDF = () => {
    setShowExportMenu(false);
    window.print();
  };

  // Grouping helper for sessions
  const groupSessions = (sessionList: any[]) => {
    const pinned: any[] = [];
    const today: any[] = [];
    const yesterday: any[] = [];
    const previous7Days: any[] = [];
    const older: any[] = [];
    
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const startOfYesterday = new Date(startOfToday.getTime() - 24 * 60 * 60 * 1000);
    const startOf7DaysAgo = new Date(startOfToday.getTime() - 7 * 24 * 60 * 60 * 1000);
    
    sessionList.forEach((s) => {
      if (s.is_pinned) {
        pinned.push(s);
        return;
      }
      const date = new Date(s.updated_at);
      if (date >= startOfToday) {
        today.push(s);
      } else if (date >= startOfYesterday) {
        yesterday.push(s);
      } else if (date >= startOf7DaysAgo) {
        previous7Days.push(s);
      } else {
        older.push(s);
      }
    });
    
    return { pinned, today, yesterday, previous7Days, older };
  };

  const grouped = groupSessions(sessions);

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

      // Add a placeholder message for the streaming response
      const assistantMsgIndex = updated.length;
      setMessages((p) => [...p, {
        sender: "tush",
        text: "",
        timestamp: new Date()
      }]);

      const streamResponse = await apiService.mcpChatStream(
        finalQuery,
        "general",
        history,
        undefined,
        activeSessionId || undefined
      );

      const reader = streamResponse.body?.getReader();
      if (!reader) throw new Error("No reader");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data: ")) continue;

          try {
            const data = JSON.parse(trimmed.slice(6));
            if (data.type === "session") {
              setActiveSessionId(data.session_id);
              fetchSessions(1, true);
            } else if (data.type === "content") {
              setMessages((p) => {
                const next = [...p];
                if (next[assistantMsgIndex]) {
                  next[assistantMsgIndex] = {
                    ...next[assistantMsgIndex],
                    text: next[assistantMsgIndex].text + data.text
                  };
                }
                return next;
              });
            } else if (data.type === "done") {
              setMessages((p) => {
                const next = [...p];
                if (next[assistantMsgIndex]) {
                  next[assistantMsgIndex] = {
                    ...next[assistantMsgIndex],
                    actions: data.actions,
                    action_cards: data.action_cards,
                    memory_updated: data.memory_updated
                  };
                }
                return next;
              });
              setLoading(false);
              fetchSessions(1, true);
            }
          } catch (e) {
            console.error("SSE parse error", e);
          }
        }
      }
    } catch (err) {
      console.error(err);
      setMessages((p) => [...p, {
        sender: "tush",
        text: "I encountered an issue. Please try again.",
        timestamp: new Date(),
      }]);
      setLoading(false);
    }
  };

  const SessionItem = ({ s }: { s: any }) => {
    const isEditing = editingSessionId === s.id;
    const isActive = activeSessionId === s.id;

    return (
      <div
        onClick={() => !isEditing && selectSession(s.id)}
        className={`group flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold cursor-pointer border transition-all duration-200 ${
          isActive
            ? "bg-blue-50/70 dark:bg-blue-950/20 border-blue-200/50 dark:border-blue-900/30 text-blue-600 dark:text-blue-400"
            : "text-app-text-secondary border-transparent hover:bg-slate-100/50 dark:hover:bg-slate-800/40 hover:text-app-text"
        }`}
      >
        <div className="flex items-center gap-2 flex-1 min-w-0 mr-2">
          {s.is_pinned ? (
            <Pin size={11} className="text-blue-500 shrink-0 rotate-45" />
          ) : (
            <Brain size={12} className="text-app-text-muted shrink-0" />
          )}
          {isEditing ? (
            <input
              type="text"
              value={editTitleText}
              onChange={(e) => setEditTitleText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") saveRename(s.id);
                if (e.key === "Escape") setEditingSessionId(null);
              }}
              onClick={(e) => e.stopPropagation()}
              autoFocus
              className="w-full bg-transparent border-b border-blue-500 outline-none text-app-text py-0.5 text-xs font-semibold"
            />
          ) : (
            <span className="truncate">{s.title}</span>
          )}
        </div>

        {/* Hover Action Buttons */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity no-print">
          {isEditing ? (
            <button
              onClick={(e) => { e.stopPropagation(); saveRename(s.id); }}
              className="p-1 rounded hover:bg-blue-100 dark:hover:bg-blue-950 text-blue-600 dark:text-blue-400"
              title="Save Title"
            >
              <Check size={11} />
            </button>
          ) : (
            <>
              <button
                onClick={(e) => togglePinSession(s.id, s.is_pinned, e)}
                className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-app-text-muted hover:text-app-text"
                title={s.is_pinned ? "Unpin Chat" : "Pin Chat"}
              >
                <Pin size={11} className={s.is_pinned ? "text-blue-500 rotate-45" : ""} />
              </button>
              <button
                onClick={(e) => startRename(s.id, s.title, e)}
                className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-app-text-muted hover:text-app-text"
                title="Rename Chat"
              >
                <Edit2 size={11} />
              </button>
              <button
                onClick={(e) => archiveSession(s.id, e)}
                className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-app-text-muted hover:text-app-text"
                title="Archive Chat"
              >
                <Archive size={11} />
              </button>
              <button
                onClick={(e) => deleteSession(s.id, e)}
                className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-950/20 text-app-text-muted hover:text-red-500"
                title="Delete Chat"
              >
                <Trash2 size={11} />
              </button>
            </>
          )}
        </div>
      </div>
    );
  };



  return (
    <div className="w-full h-full min-h-screen bg-app-bg text-app-text flex flex-row font-sans transition-colors duration-300 relative overflow-hidden">
      
      {/* 1. Collapsible Left Chat History Sidebar */}
      {isHistoryOpen && (
        <aside className="no-print w-72 shrink-0 border-r border-app-border bg-app-surface/90 backdrop-blur-md flex flex-col h-screen transition-all duration-300 ease-in-out">
          {/* Header & New Chat */}
          <div className="p-4 flex flex-col gap-3 shrink-0">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-widest text-app-text-muted">Chat History</span>
              <button
                onClick={() => setIsHistoryOpen(false)}
                className="p-1.5 rounded-lg text-app-text-muted hover:text-app-text hover:bg-app-bg transition-colors"
                title="Hide Sidebar"
              >
                <PanelLeftClose size={16} />
              </button>
            </div>

            <button
              onClick={startNewChat}
              className="flex items-center justify-center gap-2 w-full py-3.5 px-4 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition-all shadow-md hover:scale-[1.01] active:scale-[0.99] cursor-pointer"
            >
              <Plus size={14} /> New Chat
            </button>

            {/* Search Box */}
            <div className="relative flex items-center bg-app-bg border border-app-border rounded-xl px-3 py-2 focus-within:border-primary/50 transition-colors">
              <Search size={14} className="text-app-text-muted shrink-0 mr-2" />
              <input
                type="text"
                placeholder="Search chats..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-transparent text-xs font-semibold text-app-text outline-none placeholder-app-text-muted"
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery("")} className="text-app-text-muted hover:text-app-text">
                  <X size={12} />
                </button>
              )}
            </div>
          </div>

          {/* Sessions List with Infinite Scroll */}
          <div
            onScroll={handleSessionsScroll}
            className="flex-1 overflow-y-auto px-3 pb-6 space-y-4 custom-scrollbar"
          >
            {/* Pinned Chats */}
            {grouped.pinned.length > 0 && (
              <div className="space-y-1">
                <span className="text-[10px] font-bold text-app-text-muted uppercase tracking-wider pl-3 block mb-1">Pinned</span>
                {grouped.pinned.map((s) => (
                  <SessionItem key={s.id} s={s} />
                ))}
              </div>
            )}

            {/* Today */}
            {grouped.today.length > 0 && (
              <div className="space-y-1">
                <span className="text-[10px] font-bold text-app-text-muted uppercase tracking-wider pl-3 block mb-1">Today</span>
                {grouped.today.map((s) => (
                  <SessionItem key={s.id} s={s} />
                ))}
              </div>
            )}

            {/* Yesterday */}
            {grouped.yesterday.length > 0 && (
              <div className="space-y-1">
                <span className="text-[10px] font-bold text-app-text-muted uppercase tracking-wider pl-3 block mb-1">Yesterday</span>
                {grouped.yesterday.map((s) => (
                  <SessionItem key={s.id} s={s} />
                ))}
              </div>
            )}

            {/* Last 7 Days */}
            {grouped.previous7Days.length > 0 && (
              <div className="space-y-1">
                <span className="text-[10px] font-bold text-app-text-muted uppercase tracking-wider pl-3 block mb-1">Previous 7 Days</span>
                {grouped.previous7Days.map((s) => (
                  <SessionItem key={s.id} s={s} />
                ))}
              </div>
            )}

            {/* Older */}
            {grouped.older.length > 0 && (
              <div className="space-y-1">
                <span className="text-[10px] font-bold text-app-text-muted uppercase tracking-wider pl-3 block mb-1">Older</span>
                {grouped.older.map((s) => (
                  <SessionItem key={s.id} s={s} />
                ))}
              </div>
            )}

            {loadingSessions && (
              <div className="flex justify-center py-2 text-app-text-muted">
                <Loader2 size={16} className="animate-spin" />
              </div>
            )}

            {!loadingSessions && sessions.length === 0 && (
              <div className="text-center py-8 text-xs text-app-text-muted">
                No past conversations found.
              </div>
            )}
          </div>
        </aside>
      )}

      {/* 2. Main Content Area */}
      <div className="flex-1 flex flex-col h-screen overflow-hidden print-full-width">
        
        {/* Toggle button if Sidebar is closed */}
        {!isHistoryOpen && (
          <div className="absolute top-4 left-4 z-30 no-print">
            <button
              onClick={() => setIsHistoryOpen(true)}
              className="p-2 bg-app-surface border border-app-border rounded-lg text-app-text-muted hover:text-app-text shadow-sm transition-colors"
              title="Show Sidebar"
            >
              <PanelLeftOpen size={18} />
            </button>
          </div>
        )}

        {!isChatActive ? (
          <div className="flex-1 flex flex-col items-center justify-start px-6 py-10 max-w-3xl mx-auto w-full overflow-y-auto">
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
                    onClick={() => landingFileRef.current?.click()}
                    className="flex items-center justify-center w-9 h-9 rounded-full text-gray-400 hover:text-gray-600 dark:text-zinc-400 dark:hover:text-zinc-200 hover:bg-gray-100 dark:hover:bg-zinc-800/50 transition-colors shrink-0 mb-0.5 cursor-pointer"
                  ><Plus size={20} /></button>
                  <input type="file" ref={landingFileRef} onChange={handleFileChange} multiple accept="image/*,.pdf,.doc,.docx,.txt" className="hidden" />

                  <div className="flex-1 min-w-0 py-1.5 self-center">
                    <textarea
                      ref={landingTextareaRef}
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
          // Active Chat Panel
          <div className="flex-1 flex flex-col md:flex-row h-full max-w-6xl w-full mx-auto p-4 md:p-6 gap-6 overflow-hidden print-full-width">
            
            {/* Main Chat Panel */}
            <div className="flex-1 flex flex-col h-full justify-between overflow-hidden print-full-width">
              {/* Chat Header */}
              <div className="flex items-center justify-between pb-3 border-b border-app-border no-print">
                <div className="flex items-center gap-3 pl-8 md:pl-0">
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
                  {/* Export Button */}
                  <div className="relative">
                    <button
                      onClick={() => setShowExportMenu(!showExportMenu)}
                      className="flex items-center gap-1.5 text-xs font-semibold text-app-text-secondary hover:text-app-text px-3 py-1.5 rounded-lg border border-app-border hover:bg-app-surface transition-colors cursor-pointer"
                    >
                      <Download size={14} /> Export
                    </button>
                    {showExportMenu && (
                      <div className="absolute right-0 mt-1.5 w-44 bg-app-surface border border-app-border rounded-xl shadow-lg z-50 p-1">
                        <button
                          onClick={handleExportMarkdown}
                          className="flex items-center gap-2 w-full text-left px-3 py-2 text-xs font-semibold text-app-text-secondary hover:text-app-text hover:bg-slate-100 dark:hover:bg-slate-800/40 rounded-lg"
                        >
                          <FileText size={13} /> Export as Markdown
                        </button>
                        <button
                          onClick={handleExportPDF}
                          className="flex items-center gap-2 w-full text-left px-3 py-2 text-xs font-semibold text-app-text-secondary hover:text-app-text hover:bg-slate-100 dark:hover:bg-slate-800/40 rounded-lg"
                        >
                          <GraduationCap size={13} /> Export as PDF
                        </button>
                      </div>
                    )}
                  </div>

                  <button
                    onClick={startNewChat}
                    className="text-xs font-semibold text-app-text-secondary hover:text-app-text px-3 py-1.5 rounded-lg border border-app-border hover:bg-app-surface transition-colors cursor-pointer"
                  >New Chat</button>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto py-5 space-y-4 scroll-smooth pr-1 print-full-width">
                {messages.map((msg, idx) => (
                  <div key={idx} className={`flex gap-3 max-w-[85%] print-full-width print-page-break ${msg.sender === "user" ? "ml-auto flex-row-reverse" : "mr-auto"}`}>
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 no-print ${msg.sender === "user" ? "bg-blue-600 text-white" : "bg-app-card text-blue-600 dark:text-blue-400 border border-app-border"}`}>
                      {msg.sender === "user" ? <User size={14} /> : <Bot size={14} />}
                    </div>
                    <div className={`p-3.5 rounded-2xl flex flex-col gap-2 text-sm leading-relaxed border ${msg.sender === "user" ? "bg-blue-50 dark:bg-blue-950/20 text-app-text border-blue-100 dark:border-blue-900/30 rounded-tr-sm" : "bg-app-card text-app-text border-app-border rounded-tl-sm shadow-sm"}`}>
                      <div className="whitespace-pre-wrap">{msg.text}</div>
                      {msg.actions && msg.actions.length > 0 && (
                        <div className="flex flex-wrap gap-2 pt-2 mt-1 border-t border-app-border no-print">
                          {msg.actions.map((act) => (
                            <Link key={act.label} href={act.href} className="px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-950/20 hover:bg-blue-100 border border-blue-200 dark:border-blue-800/30 text-blue-600 dark:text-blue-400 text-xs font-semibold transition-all inline-flex items-center gap-1">
                              {act.label} <ChevronRight size={12} />
                            </Link>
                          ))}
                        </div>
                      )}
                      {msg.action_cards && msg.action_cards.length > 0 && (
                        <div className="flex flex-col gap-2 pt-2 border-t border-app-border mt-1 w-full no-print">
                          {msg.action_cards.map((card, idx) => (
                            <AIActionCard key={idx} card={card} />
                          ))}
                        </div>
                      )}
                      {msg.memory_updated && (
                        <div className="flex items-center gap-1 text-[9px] text-violet-600 dark:text-violet-400 font-semibold self-start mt-0.5 no-print">
                          <span>🧠 Memory updated</span>
                        </div>
                      )}
                      <span className="text-[10px] text-app-text-muted self-end">
                        {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                  </div>
                ))}
                {loading && messages[messages.length - 1]?.sender === "user" && (
                  <div className="flex gap-3 mr-auto no-print">
                    <div className="w-8 h-8 rounded-lg bg-app-card border border-app-border flex items-center justify-center text-blue-600 dark:text-blue-400"><Bot size={14} /></div>
                    <div className="p-3.5 rounded-2xl bg-app-card border border-app-border rounded-tl-sm shadow-sm flex items-center gap-2">
                      <Loader2 size={14} className="animate-spin text-blue-600 dark:text-blue-400" />
                      <span className="text-xs text-app-text-muted font-medium">Tush AI is thinking...</span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              <div className="pt-2 pb-1 no-print">
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
                      onClick={() => chatFileRef.current?.click()}
                      className="flex items-center justify-center w-9 h-9 rounded-full text-gray-400 hover:text-gray-600 dark:text-zinc-400 dark:hover:text-zinc-200 hover:bg-gray-100 dark:hover:bg-zinc-800/50 transition-colors shrink-0 mb-0.5 cursor-pointer"
                    ><Plus size={20} /></button>
                    <input type="file" ref={chatFileRef} onChange={handleFileChange} multiple accept="image/*,.pdf,.doc,.docx,.txt" className="hidden" />

                    <div className="flex-1 min-w-0 py-1.5 self-center">
                      <textarea
                        ref={chatTextareaRef}
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
                <p className="text-[10px] text-app-text-muted text-center mt-2">
                  Tush AI · Personalized career guidance
                </p>
              </div>
            </div>

            {/* Activity Feed Sidebar (Desktop) */}
            <div className="hidden lg:block w-80 shrink-0 border-l border-app-border pl-6 overflow-y-auto no-print">
              <AgentActivityFeed maxItems={15} />
            </div>
          </div>
        )}
      </div>
      <HumanActionQueue />
    </div>
  );
}
