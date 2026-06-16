"use client";

import { useState, useEffect, useRef } from "react";
import { useAuthStore } from "@/store/authStore";
import { apiService } from "@/services/api";
import { Sparkles, Mic, Send, Briefcase, FileText, ClipboardList, User, Bot, Loader2, ChevronRight, Globe, BarChart3, Target, Rocket, Plus, ArrowUp } from "lucide-react";
import Link from "next/link";

interface Message {
  sender: "user" | "tush";
  text: string;
  timestamp: Date;
  actions?: { label: string; href: string }[];
}

export default function TushAIChat() {
  const { fullName } = useAuthStore();
  const [query, setQuery] = useState("");
  const [isChatActive, setIsChatActive] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const landingTextareaRef = useRef<HTMLTextAreaElement>(null);
  const chatTextareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize landing input
  useEffect(() => {
    const textarea = landingTextareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [query, isChatActive]);

  // Auto-resize chat input
  useEffect(() => {
    const textarea = chatTextareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [query, isChatActive]);

  // Speech to Text (STT) state & handlers
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  const startListening = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser. Please try Chrome or Safari.");
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const rec = new SpeechRecognition();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = "en-US";

    rec.onstart = () => {
      setIsListening(true);
    };

    rec.onresult = (event: any) => {
      let finalTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        }
      }
      if (finalTranscript) {
        setQuery((prev) => prev + (prev.endsWith(" ") || prev === "" ? "" : " ") + finalTranscript);
      }
    };

    rec.onerror = (e: any) => {
      console.error("Speech recognition error:", e);
      setIsListening(false);
    };

    rec.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = rec;
    rec.start();
  };

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  // File Upload states and handlers
  const [attachments, setAttachments] = useState<File[]>([]);
  const landingFileInputRef = useRef<HTMLInputElement>(null);
  const chatFileInputRef = useRef<HTMLInputElement>(null);

  const handlePlusClick = (isLanding: boolean) => {
    if (isLanding) {
      landingFileInputRef.current?.click();
    } else {
      chatFileInputRef.current?.click();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      setAttachments((prev) => [...prev, ...selectedFiles]);
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, idx) => idx !== index));
  };

  const firstName = fullName ? fullName.split(" ")[0] : "User";
  const capitalizedFirstName = firstName.charAt(0).toUpperCase() + firstName.slice(1);

  // Scroll to bottom on new messages
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loading]);

  const quickSuggestions = [
    {
      title: "Discover Career Opportunities",
      query: "Show me available job openings",
      icon: Briefcase,
      color: "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/30",
    },
    {
      title: "Track My Application Status",
      query: "What is the status of my applications?",
      icon: ClipboardList,
      color: "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30",
    },
    {
      title: "Identify High-Impact Skill Gaps",
      query: "Analyze my skill gaps and recommend roadmaps",
      icon: BarChart3,
      color: "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30",
    },
    {
      title: "Develop a Personalized Career Roadmap",
      query: "Create a career development roadmap for me",
      icon: Target,
      color: "text-violet-600 dark:text-violet-400 bg-violet-50 dark:bg-violet-950/30",
    },
    {
      title: "Prepare for Upcoming Interviews",
      query: "Prepare me for an upcoming interview",
      icon: Rocket,
      color: "text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/30",
    },
    {
      title: "Explore Remote & Global Opportunities",
      query: "Show me remote job opportunities worldwide",
      icon: Globe,
      color: "text-cyan-600 dark:text-cyan-400 bg-cyan-50 dark:bg-cyan-950/30",
    },
  ];

  const handleSend = async (textToSend: string) => {
    let finalQuery = textToSend;
    let messageText = textToSend;

    if (attachments.length > 0) {
      const fileNames = attachments.map(f => f.name).join(", ");
      const attachmentText = `\n\n[Attached: ${fileNames}]`;
      messageText = textToSend ? `${textToSend}${attachmentText}` : `[Attached: ${fileNames}]`;
      finalQuery = textToSend ? `${textToSend} (with files: ${fileNames})` : `Processing files: ${fileNames}`;
    }

    if (!messageText.trim()) return;

    setIsChatActive(true);
    const userMsg: Message = {
      sender: "user",
      text: messageText,
      timestamp: new Date()
    };
    
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setQuery("");
    setAttachments([]);
    setLoading(true);

    try {
      const history = updatedMessages.slice(0, -1).map(msg => ({
        role: msg.sender === "user" ? "user" : "assistant",
        content: msg.text
      }));

      const result = await apiService.chatCopilot(finalQuery, history);

      const botMsg: Message = {
        sender: "tush",
        text: result.response,
        timestamp: new Date(),
        actions: result.actions && result.actions.length > 0 ? result.actions : undefined
      };
      setMessages((prev) => [...prev, botMsg]);
      setLoading(false);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          sender: "tush",
          text: "I encountered a minor issue. Please try again or navigate using the side menu options.",
          timestamp: new Date()
        }
      ]);
      setLoading(false);
    }
  };

  return (
    <div className="w-full h-full min-h-screen bg-app-bg text-app-text flex flex-col font-sans transition-colors duration-300 relative">

      {!isChatActive ? (
        // ── Landing / Welcome View ──
        <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 max-w-3xl mx-auto w-full">
          
          {/* Welcome Greeting */}
          <p className="text-base text-app-text-secondary font-medium mb-3">
            Welcome back, <span className="text-blue-600 dark:text-blue-400 font-semibold">{capitalizedFirstName}</span> 👋
          </p>

          {/* Main Heading */}
          <h1 className="text-2xl md:text-3xl lg:text-4xl font-extrabold text-app-text tracking-tight text-center leading-tight mb-10">
            How can <span className="text-blue-600 dark:text-blue-400">Tush AI</span> help you today?
          </h1>

          {/* Search Input */}
          <div className="w-full max-w-2xl mb-12">
            <div className="flex flex-col flex flex-col bg-card border border-border rounded-32 p-2 pl-4 pr-3 shadow-custom-glass hover:border-border-hover dark:hover:border-neutral-700 focus-within:border-primary/50 dark:focus-within:border-primary/40 focus-within:shadow-[0_8px_30px_rgba(59,130,246,0.08)] transition-all duration-300 w-full">
              
              {/* Attachment Preview Chips */}
              {attachments.length > 0 && (
                <div className="flex flex-wrap gap-2 px-1 pt-2 pb-1.5 border-b border-gray-100 dark:border-zinc-800 mb-2 w-full">
                  {attachments.map((file, idx) => {
                    const isImage = file.type.startsWith("image/");
                    return (
                      <div 
                        key={idx} 
                        className="flex items-center gap-1.5 pl-2 pr-1.5 py-1 rounded-lg bg-gray-50 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 text-xs text-gray-700 dark:text-zinc-300"
                      >
                        {isImage ? (
                          <span className="w-4.5 h-4.5 rounded overflow-hidden shrink-0 border border-gray-300 dark:border-zinc-600">
                            <img 
                              src={URL.createObjectURL(file)} 
                              alt={file.name} 
                              className="w-full h-full object-cover"
                            />
                          </span>
                        ) : (
                          <FileText size={14} className="text-blue-500" />
                        )}
                        <span className="max-w-120 truncate font-medium">{file.name}</span>
                        <button 
                          onClick={() => removeAttachment(idx)}
                          className="w-4 h-4 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-600 dark:hover:text-zinc-200 hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors cursor-pointer"
                          title="Remove file"
                        >
                          &times;
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Main Pill Controls row */}
              <div className="flex items-end gap-2 w-full min-h-10">
                {/* Left Side: Plus icon */}
                <button 
                  onClick={() => handlePlusClick(true)}
                  className="flex items-center justify-center w-9 h-9 rounded-full text-gray-400 hover:text-gray-600 dark:text-zinc-400 dark:hover:text-zinc-200 hover:bg-gray-100 dark:hover:bg-zinc-800/50 transition-colors shrink-0 mb-0.5" 
                  title="Add attachment"
                >
                  <Plus size={20} />
                </button>
                <input 
                  type="file" 
                  ref={landingFileInputRef} 
                  onChange={handleFileChange} 
                  multiple 
                  accept="image/*,.pdf,.doc,.docx,.txt"
                  className="hidden" 
                />

                {/* Center: Textarea that expands naturally */}
                <div className="flex-1 min-w-0 py-1.5 self-center">
                  <textarea
                    ref={landingTextareaRef}
                    rows={1}
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleSend(query);
                      }
                    }}
                    placeholder="Ask Tush AI anything..."
                    className="chat-input-textarea w-full bg-transparent resize-none border-none outline-none focus:ring-0 text-sm text-foreground placeholder-muted-foreground py-1 max-h-200 h-6"
                  />
                </div>

                {/* Right Side: Microphone and Send buttons */}
                <div className="flex items-center gap-1.5 shrink-0 self-center">
                  {/* Microphone Icon */}
                  <button 
                    onClick={startListening}
                    className={`flex items-center justify-center w-9 h-9 rounded-full transition-all duration-300 ${
                      isListening 
                        ? "bg-red-500 text-white animate-pulse shadow-[0_0_12px_rgba(239,68,68,0.5)]" 
                        : "text-gray-400 hover:text-gray-600 dark:text-zinc-400 dark:hover:text-zinc-200 hover:bg-gray-100 dark:hover:bg-zinc-800/50"
                    }`} 
                    title={isListening ? "Stop listening" : "Voice input"}
                  >
                    <Mic size={18} />
                  </button>

                  {/* Send button (always visible) */}
                  <button
                    onClick={() => handleSend(query)}
                    disabled={!query.trim() && attachments.length === 0}
                    className={`flex items-center justify-center w-9 h-9 rounded-full transition-all duration-200 shrink-0 ${
                      query.trim() || attachments.length > 0
                        ? "bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:scale-105 active:scale-95 cursor-pointer"
                        : "bg-slate-100 dark:bg-zinc-800 text-slate-400 dark:text-slate-600 cursor-not-allowed"
                    }`}
                    title="Send message"
                  >
                    <ArrowUp size={16} />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Suggestions */}
          <div className="w-full max-w-3xl">
            <p className="text-xs font-semibold text-app-text-muted text-center mb-5 uppercase tracking-wider">Quick suggestions</p>
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
              {quickSuggestions.map((suggestion) => {
                const Icon = suggestion.icon;
                return (
                  <button
                    key={suggestion.title}
                    onClick={() => handleSend(suggestion.query)}
                    className="flex items-center gap-3 px-4 py-3.5 rounded-xl bg-app-card border border-app-border text-left hover:shadow-md hover:border-slate-300 dark:hover:border-slate-700 hover:scale-[1.01] transition-all duration-200 cursor-pointer group"
                  >
                    <div className={`p-2 rounded-lg shrink-0 ${suggestion.color}`}>
                      <Icon size={15} />
                    </div>
                    <span className="text-xs font-semibold text-app-text-secondary group-hover:text-app-text transition-colors leading-snug">
                      {suggestion.title}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

        </div>
      ) : (
        // ── Active Chat Thread ──
        <div className="flex-1 flex flex-col h-full max-w-4xl w-full mx-auto p-4 md:p-6 justify-between overflow-hidden">
          
          {/* Chat Header */}
          <div className="flex items-center justify-between pb-4 border-b border-app-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-600 text-white rounded-xl flex items-center justify-center shadow-md">
                <Sparkles size={18} />
              </div>
              <div>
                <h2 className="text-sm font-bold text-app-text">Tush AI</h2>
                <span className="text-10 text-emerald-500 font-medium flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
                  Active Session
                </span>
              </div>
            </div>
            <button 
              onClick={() => {
                setIsChatActive(false);
                setMessages([]);
              }}
              className="text-xs font-semibold text-app-text-secondary hover:text-app-text px-3 py-1.5 rounded-lg border border-app-border hover:bg-app-surface transition-colors cursor-pointer"
            >
              New Chat
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto py-6 space-y-5 scroll-smooth pr-1">
            {messages.map((msg, idx) => (
              <div 
                key={idx} 
                className={`flex gap-3 max-w-85-pct ${
                  msg.sender === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
                }`}
              >
                {/* Avatar */}
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                  msg.sender === "user" 
                    ? "bg-blue-600 text-white" 
                    : "bg-app-card text-blue-600 dark:text-blue-400 border border-app-border"
                }`}>
                  {msg.sender === "user" ? <User size={15} /> : <Bot size={15} />}
                </div>

                {/* Message */}
                <div className={`p-4 rounded-2xl flex flex-col gap-2 text-sm leading-relaxed border ${
                  msg.sender === "user"
                    ? "bg-blue-50 dark:bg-blue-950/20 text-app-text border-blue-100 dark:border-blue-900/30 rounded-tr-sm"
                    : "bg-app-card text-app-text border-app-border rounded-tl-sm shadow-sm"
                }`}>
                  <div className="whitespace-pre-wrap">{msg.text}</div>

                  {/* Action buttons */}
                  {msg.actions && (
                    <div className="flex flex-wrap gap-2 pt-2 mt-1 border-t border-app-border">
                      {msg.actions.map((act) => (
                        <Link 
                          key={act.label} 
                          href={act.href}
                          className="px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-950/20 hover:bg-blue-100 dark:hover:bg-blue-950/30 border border-blue-200 dark:border-blue-800/30 text-blue-600 dark:text-blue-400 text-xs font-semibold transition-all inline-flex items-center gap-1"
                        >
                          <span>{act.label}</span>
                          <ChevronRight size={12} />
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex gap-3 mr-auto">
                <div className="w-8 h-8 rounded-lg bg-app-card border border-app-border flex items-center justify-center text-blue-600 dark:text-blue-400">
                  <Bot size={15} />
                </div>
                <div className="p-4 rounded-2xl bg-app-card border border-app-border rounded-tl-sm shadow-sm flex items-center gap-2">
                  <Loader2 size={14} className="animate-spin text-blue-600 dark:text-blue-400" />
                  <span className="text-xs text-app-text-muted font-medium">Tush AI is thinking...</span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Footer input */}
          <div className="pt-2 pb-2">
            <div className="flex flex-col flex flex-col bg-card border border-border rounded-32 p-2 pl-4 pr-3 shadow-custom-glass hover:border-border-hover dark:hover:border-neutral-700 focus-within:border-primary/50 dark:focus-within:border-primary/40 focus-within:shadow-[0_8px_30px_rgba(59,130,246,0.08)] transition-all duration-300 w-full">
              
              {/* Attachment Preview Chips */}
              {attachments.length > 0 && (
                <div className="flex flex-wrap gap-2 px-1 pt-2 pb-1.5 border-b border-gray-100 dark:border-zinc-800 mb-2 w-full">
                  {attachments.map((file, idx) => {
                    const isImage = file.type.startsWith("image/");
                    return (
                      <div 
                        key={idx} 
                        className="flex items-center gap-1.5 pl-2 pr-1.5 py-1 rounded-lg bg-gray-50 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 text-xs text-gray-700 dark:text-zinc-300"
                      >
                        {isImage ? (
                          <span className="w-4.5 h-4.5 rounded overflow-hidden shrink-0 border border-gray-300 dark:border-zinc-600">
                            <img 
                              src={URL.createObjectURL(file)} 
                              alt={file.name} 
                              className="w-full h-full object-cover"
                            />
                          </span>
                        ) : (
                          <FileText size={14} className="text-blue-500" />
                        )}
                        <span className="max-w-120 truncate font-medium">{file.name}</span>
                        <button 
                          onClick={() => removeAttachment(idx)}
                          className="w-4 h-4 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-600 dark:hover:text-zinc-200 hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors cursor-pointer"
                          title="Remove file"
                        >
                          &times;
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Main Pill Controls row */}
              <div className="flex items-end gap-2 w-full min-h-10">
                {/* Left Side: Plus icon */}
                <button 
                  onClick={() => handlePlusClick(false)}
                  className="flex items-center justify-center w-9 h-9 rounded-full text-gray-400 hover:text-gray-600 dark:text-zinc-400 dark:hover:text-zinc-200 hover:bg-gray-100 dark:hover:bg-zinc-800/50 transition-colors shrink-0 mb-0.5" 
                  title="Add attachment"
                >
                  <Plus size={20} />
                </button>
                <input 
                  type="file" 
                  ref={chatFileInputRef} 
                  onChange={handleFileChange} 
                  multiple 
                  accept="image/*,.pdf,.doc,.docx,.txt"
                  className="hidden" 
                />

                {/* Center: Textarea that expands naturally */}
                <div className="flex-1 min-w-0 py-1.5 self-center">
                  <textarea
                    ref={chatTextareaRef}
                    rows={1}
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleSend(query);
                      }
                    }}
                    placeholder="Ask Tush AI anything..."
                    className="chat-input-textarea w-full bg-transparent resize-none border-none outline-none focus:ring-0 text-sm text-foreground placeholder-muted-foreground py-1 max-h-200 h-6"
                  />
                </div>

                {/* Right Side: Microphone and Send buttons */}
                <div className="flex items-center gap-1.5 shrink-0 self-center">
                  {/* Microphone Icon */}
                  <button 
                    onClick={startListening}
                    className={`flex items-center justify-center w-9 h-9 rounded-full transition-all duration-300 ${
                      isListening 
                        ? "bg-red-500 text-white animate-pulse shadow-[0_0_12px_rgba(239,68,68,0.5)]" 
                        : "text-gray-400 hover:text-gray-600 dark:text-zinc-400 dark:hover:text-zinc-200 hover:bg-gray-100 dark:hover:bg-zinc-800/50"
                    }`} 
                    title={isListening ? "Stop listening" : "Voice input"}
                  >
                    <Mic size={18} />
                  </button>

                  {/* Send button (always visible) */}
                  <button
                    onClick={() => handleSend(query)}
                    disabled={!query.trim() && attachments.length === 0}
                    className={`flex items-center justify-center w-9 h-9 rounded-full transition-all duration-200 shrink-0 ${
                      query.trim() || attachments.length > 0
                        ? "bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:scale-105 active:scale-95 cursor-pointer"
                        : "bg-slate-100 dark:bg-zinc-800 text-slate-400 dark:text-slate-600 cursor-not-allowed"
                    }`}
                    title="Send message"
                  >
                    <ArrowUp size={16} />
                  </button>
                </div>
              </div>
            </div>
            
            <p className="text-10 text-app-text-muted text-center mt-2.5">
              Tush AI provides personalized career guidance powered by advanced intelligence.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
