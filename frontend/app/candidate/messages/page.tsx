"use client";

import { useState, useEffect, useRef } from "react";
import { useAuthStore } from "@/store/authStore";
import { apiService } from "@/services/api";
import { useWebSockets } from "@/hooks/useWebSockets";
import { 
  Send, Search, Users, MessageSquare, AlertCircle, Headphones, Paperclip, ArrowLeft
} from "lucide-react";

/* ─── Types ────────────────────────────────────────────────────────── */

interface MessageItem {
  id: number;
  candidate_id: number;
  chat_id: string;
  sender: "user" | "recruiter" | "mentor" | "other" | "support";
  sender_name: string;
  text: string;
  sent_at: string;
  read: boolean;
}

interface ChatListItem {
  id: string;
  name: string;
  avatar: string;
  category: "mentors" | "teams" | "companies" | "support";
  iconBg: string;
  iconText: string;
}

/* ─── Helpers ──────────────────────────────────────────────────────── */

function formatLastMessageTime(dateStr: string): string {
  if (!dateStr) return "";
  try {
    const date = new Date(dateStr);
    const now  = new Date();

    const today     = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const msgDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());

    if (msgDate.getTime() === today.getTime()) {
      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } else if (msgDate.getTime() === yesterday.getTime()) {
      return "Yesterday";
    } else if (now.getTime() - date.getTime() < 7 * 24 * 60 * 60 * 1000) {
      return date.toLocaleDateString([], { weekday: "short" });
    } else {
      return date.toLocaleDateString([], { day: "numeric", month: "short" });
    }
  } catch {
    return "";
  }
}

/** Returns a smart preview string for the conversation list. */
function formatLastPreview(chat: ChatListItem, msg: MessageItem | undefined): string {
  if (!msg) return "No messages yet";
  const isTeam = chat.category === "teams";
  const prefix = msg.sender === "user" ? "You" : msg.sender_name;
  if (isTeam) return `${prefix}: ${msg.text}`;
  return msg.text;
}

/* ─── Avatar component ─────────────────────────────────────────────── */

function ChatAvatar({ chat, size = "md" }: { chat: ChatListItem | undefined; size?: "sm" | "md" }) {
  if (!chat) return null;
  const dim = size === "sm" ? "w-8 h-8" : "w-10 h-10";
  const textSize = size === "sm" ? "text-[10px]" : "text-xs";

  // Mentor Rahul → real photo
  if (chat.name.includes("Rahul") && chat.category === "mentors") {
    return (
      <img
        src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=100&h=100&q=80"
        alt={chat.name}
        className={`${dim} rounded-full object-cover shrink-0`}
      />
    );
  }

  // Microsoft logo grid
  if (chat.name.includes("Microsoft")) {
    return (
      <div className={`${dim} rounded-full bg-white dark:bg-neutral-900 border border-slate-200 dark:border-neutral-700 flex items-center justify-center shrink-0 shadow-sm`}>
        <div className="grid grid-cols-2 gap-[2px]">
          <div className="w-[9px] h-[9px] bg-[#F25022] rounded-[1px]" />
          <div className="w-[9px] h-[9px] bg-[#7FBA00] rounded-[1px]" />
          <div className="w-[9px] h-[9px] bg-[#00A4EF] rounded-[1px]" />
          <div className="w-[9px] h-[9px] bg-[#FFB900] rounded-[1px]" />
        </div>
      </div>
    );
  }

  // Amazon black logo
  if (chat.name.includes("Amazon")) {
    return (
      <div className={`${dim} rounded-full bg-[#131921] flex items-center justify-center shrink-0`}>
        <span className="text-[#FF9900] font-extrabold text-sm font-sans leading-none">a</span>
      </div>
    );
  }

  // Support headphones
  if (chat.id === "support") {
    return (
      <div className={`${dim} rounded-full bg-purple-100 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0`}>
        <Headphones size={size === "sm" ? 14 : 16} />
      </div>
    );
  }

  // Default initials avatar
  return (
    <div className={`${dim} rounded-full flex items-center justify-center font-bold ${textSize} shrink-0 ${chat.iconBg} ${chat.iconText}`}>
      {chat.avatar}
    </div>
  );
}

/** Avatar for message thread senders */
function SenderAvatar({ senderName, size = "sm" }: { senderName: string; size?: "sm" | "md" }) {
  const dim = size === "sm" ? "w-7 h-7" : "w-8 h-8";
  const avatarMap: Record<string, string> = {
    Rahul:  "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=100&h=100&q=80",
    Teja:   "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=100&h=100&q=80",
    Anusha: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=100&h=100&q=80",
  };
  const url = avatarMap[senderName] || "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&h=100&q=80";
  return <img src={url} alt={senderName} className={`${dim} rounded-full object-cover shrink-0`} />;
}

/* ═══════════════════════════════════════════════════════════════════ */
/*                          MAIN COMPONENT                            */
/* ═══════════════════════════════════════════════════════════════════ */

export default function Messages() {
  const { fullName, email } = useAuthStore();
  const [activeChat, setActiveChat]     = useState("");
  const [searchQuery, setSearchQuery]   = useState("");
  const [activeTab, setActiveTab]       = useState<"all" | "mentors" | "teams" | "companies" | "support">("all");
  const [chatMessages, setChatMessages] = useState<Record<string, MessageItem[]>>({});
  const [chatListItems, setChatListItems] = useState<ChatListItem[]>([]);
  const [inputVal, setInputVal]         = useState("");
  const [showMobileChatList, setShowMobileChatList] = useState(true);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const { addMessageListener } = useWebSockets(email || "candidate");

  /* ── Load chat list from DB ─────────────────────────────────────── */
  const loadChatList = async () => {
    try {
      const items: ChatListItem[] = [];

      let teamName   = "";
      let mentorName = "";

      try {
        const profile = await apiService.getProfile();
        if (profile) {
          teamName   = profile.hackathon_team   || "";
          mentorName = profile.assigned_mentor   || "";
        }
      } catch (err) {
        console.error("Failed to load candidate profile from DB:", err);
      }

      // 1. Hackathon Team
      if (teamName) {
        items.push({
          id: `team_${teamName.replace(/\s+/g, "_").toLowerCase()}`,
          name: teamName,
          avatar: "TA",
          category: "teams",
          iconBg: "bg-[#2563EB]",
          iconText: "text-white",
        });
      }

      // 2. Mentor
      if (mentorName) {
        items.push({
          id: `mentor_${mentorName.replace(/\s+/g, "_").toLowerCase()}`,
          name: `Mentor ${mentorName}`,
          avatar: mentorName.slice(0, 2).toUpperCase(),
          category: "mentors",
          iconBg: "bg-orange-100 dark:bg-orange-950/40",
          iconText: "text-orange-600 dark:text-orange-400",
        });
      }

      // 3. Hiring teams from applications
      try {
        const apps = await apiService.getApplications();
        if (apps && apps.length > 0) {
          const jobs = await apiService.getJobs();
          apps.forEach((app: any) => {
            const job = jobs.find((j: any) => j.id === app.job_id);
            if (job) {
              const initials = job.title.split(" ").map((n: string) => n[0]).join("").toUpperCase().slice(0, 2);
              items.push({
                id: `hiring_team_${app.id}`,
                name: `${job.title} Hiring Team`,
                avatar: initials,
                category: "companies",
                iconBg: "bg-blue-100 dark:bg-blue-950/40",
                iconText: "text-blue-600 dark:text-blue-400",
              });
            }
          });
        }
      } catch (err) {
        console.error("Failed to load hiring teams:", err);
      }

      // 4. Support — always present, at bottom
      items.push({
        id: "support",
        name: "Support Team",
        avatar: "ST",
        category: "support",
        iconBg: "bg-purple-100 dark:bg-purple-950/40",
        iconText: "text-purple-600 dark:text-purple-400",
      });

      setChatListItems(items);

      if (items.length > 0 && (!activeChat || !items.some((it) => it.id === activeChat))) {
        const teamChat = items.find((it) => it.id.startsWith("team_"));
        setActiveChat(teamChat ? teamChat.id : items[0].id);
      }
    } catch (err) {
      console.error("Failed to build dynamic chat list:", err);
    }
  };

  /* ── Load messages from DB ──────────────────────────────────────── */
  const loadMessagesFromDB = async () => {
    try {
      const data = await apiService.getMessages();
      if (data && data.length > 0) {
        const grouped: Record<string, MessageItem[]> = {};
        data.forEach((msg: MessageItem) => {
          if (!grouped[msg.chat_id]) grouped[msg.chat_id] = [];
          grouped[msg.chat_id].push(msg);
        });
        setChatMessages(grouped);
      }
    } catch (err) {
      console.error("Failed to load message history from backend:", err);
    }
  };

  useEffect(() => {
    loadChatList();
    loadMessagesFromDB();
  }, [fullName, email]);

  /* ── WebSocket live messages ────────────────────────────────────── */
  useEffect(() => {
    if (!email) return;
    const unsubscribe = addMessageListener((event: any) => {
      if (event.type === "chat_message") {
        setChatMessages((prev) => {
          const chatId = event.chat_id;
          const list = prev[chatId] || [];
          if (list.some((m) => m.id === event.message.id)) return prev;
          return { ...prev, [chatId]: [...list, event.message] };
        });
      }
    });
    return () => unsubscribe();
  }, [email, addMessageListener]);

  /* ── Auto-scroll ────────────────────────────────────────────────── */
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages, activeChat]);

  /* ── Send message ───────────────────────────────────────────────── */
  const handleSend = async () => {
    if (!inputVal.trim()) return;
    const textToSend = inputVal;
    setInputVal("");
    try {
      const savedMsg = await apiService.sendMessage(activeChat, textToSend);
      if (savedMsg) {
        setChatMessages((prev) => {
          const list = prev[activeChat] || [];
          if (list.some((m) => m.id === savedMsg.id)) return prev;
          return { ...prev, [activeChat]: [...list, savedMsg] };
        });
      }
    } catch (err) {
      console.error("Failed to send message via API:", err);
    }
  };

  /* ── Filter ─────────────────────────────────────────────────────── */
  const filteredChats = chatListItems.filter((chat) => {
    const matchesSearch = chat.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTab    = activeTab === "all" || chat.category === activeTab;
    return matchesSearch && matchesTab;
  });

  const currentChat = chatListItems.find((c) => c.id === activeChat);

  /* ── Context-aware placeholder ──────────────────────────────────── */
  const getInputPlaceholder = () => {
    if (!currentChat) return "Type a message...";
    if (currentChat.category === "teams")     return "Type a message to your team...";
    if (currentChat.category === "mentors")   return "Type a message to your mentor...";
    if (currentChat.category === "companies") return "Type a message to the hiring team...";
    if (currentChat.category === "support")   return "Type a message to support...";
    return "Type a message...";
  };

  /* ═══════════════════════════════════════════════════════════════════ */
  /*                              RENDER                                */
  /* ═══════════════════════════════════════════════════════════════════ */

  return (
    <div className="w-full h-full flex flex-col font-sans text-slate-800 dark:text-slate-100 bg-[#F4F6F8] dark:bg-black transition-colors duration-300">

      {/* ── Page Header ───────────────────────────────────────────── */}
      <div className={`px-7 pt-6 pb-4 shrink-0 ${!showMobileChatList ? "hidden md:block" : "block"}`}>
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-tight">
          Messages
        </h1>
        <p className="text-[11px] text-slate-500 dark:text-slate-500 mt-0.5 font-medium tracking-wide">
          Mentors • Teams • Hiring Updates • Support
        </p>
      </div>

      {/* ── Main 2-column layout ──────────────────────────────────── */}
      <div className="flex-1 flex gap-0 md:gap-4 px-0 pb-0 md:px-7 md:pb-6 min-h-0">

        {/* ━━━━━━━━━━━━━ LEFT: Conversation List ━━━━━━━━━━━━━━━━━━━ */}
        <div className={`w-full md:w-[35%] md:min-w-[280px] bg-white dark:bg-[#0A0A0A] border-0 md:border border-slate-200/70 dark:border-neutral-800 rounded-none md:rounded-2xl flex flex-col shrink-0 overflow-hidden ${
          !showMobileChatList ? "hidden md:flex" : "flex"
        }`}>

          {/* Search + Filter */}
          <div className="px-4 pt-4 pb-3 shrink-0">
            <div className="flex gap-2">
              <div className="relative flex-1 flex items-center">
                <Search className="absolute left-3 text-slate-400 dark:text-neutral-500 pointer-events-none" size={14} />
                <input
                  type="text"
                  placeholder="Search conversations..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-800 dark:text-white placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:border-[#2563EB] dark:focus:border-[#2563EB] transition-colors"
                />
              </div>
              <button className="w-9 h-9 rounded-xl border border-slate-200 dark:border-neutral-800 flex items-center justify-center text-slate-400 dark:text-neutral-500 hover:bg-slate-50 dark:hover:bg-neutral-900 transition-colors shrink-0 cursor-pointer">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>
              </button>
            </div>
          </div>

          {/* Category pill tabs */}
          <div className="px-4 pb-3 flex gap-1.5 overflow-x-auto shrink-0 scrollbar-none">
            {([
              { id: "all",       label: "All" },
              { id: "mentors",   label: "Mentors" },
              { id: "teams",     label: "Teams" },
              { id: "companies", label: "Companies" },
              { id: "support",   label: "Support" },
            ] as const).map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`h-[32px] px-3.5 rounded-full text-[11px] font-semibold flex items-center justify-center transition-all shrink-0 cursor-pointer ${
                  activeTab === tab.id
                    ? "bg-[#2563EB] text-white shadow-sm"
                    : "bg-slate-100 dark:bg-neutral-900 text-slate-500 dark:text-neutral-400 hover:bg-slate-200 dark:hover:bg-neutral-800"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Divider */}
          <div className="h-px bg-slate-100 dark:bg-neutral-800 mx-4" />

          {/* Chat list */}
          <div className="flex-1 overflow-y-auto py-1.5 scrollbar-none">
            {filteredChats.length === 0 ? (
              <div className="p-10 text-center text-slate-400 dark:text-neutral-600 text-xs flex flex-col items-center gap-2.5">
                <AlertCircle size={20} />
                <span>No conversations found</span>
              </div>
            ) : (
              filteredChats.map((chat) => {
                const thread      = chatMessages[chat.id] || [];
                const lastMsg     = thread[thread.length - 1];
                const active      = activeChat === chat.id;
                const unreadCount = thread.filter((m) => !m.read && m.sender !== "user").length;

                return (
                  <div
                    key={chat.id}
                    onClick={() => {
                      setActiveChat(chat.id);
                      setShowMobileChatList(false);
                    }}
                    className={`px-4 py-3 mx-2 my-0.5 rounded-xl flex items-center gap-3 cursor-pointer transition-all ${
                      active
                        ? "bg-[#EBF2FF] dark:bg-[#2563EB]/10 border border-[#2563EB]/20 dark:border-[#2563EB]/20"
                        : "border border-transparent hover:bg-slate-50 dark:hover:bg-neutral-900/60"
                    }`}
                  >
                    <ChatAvatar chat={chat} />

                    <div className="flex-1 min-w-0 overflow-hidden">
                      <div className="flex justify-between items-center">
                        <h3 className={`text-[13px] font-semibold truncate leading-tight ${
                          active ? "text-[#2563EB] dark:text-[#60A5FA]" : "text-slate-900 dark:text-white"
                        }`}>
                          {chat.name}
                        </h3>
                        <span className="text-[10px] text-slate-400 dark:text-neutral-500 shrink-0 ml-2 font-medium">
                          {lastMsg ? formatLastMessageTime(lastMsg.sent_at) : ""}
                        </span>
                      </div>
                      <div className="flex justify-between items-center mt-1 gap-2">
                        <p className="text-[11px] text-slate-500 dark:text-neutral-500 truncate leading-tight">
                          {formatLastPreview(chat, lastMsg)}
                        </p>
                        {unreadCount > 0 && (
                          <span className="min-w-[18px] h-[18px] px-1 bg-[#2563EB] text-white text-[9px] font-bold rounded-full flex items-center justify-center shrink-0">
                            {unreadCount}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ━━━━━━━━━━━━━ RIGHT: Active Conversation ━━━━━━━━━━━━━━━━ */}
        <div className={`flex-1 bg-white dark:bg-[#0A0A0A] border-0 md:border border-slate-200/70 dark:border-neutral-800 rounded-none md:rounded-2xl flex flex-col min-h-0 overflow-hidden ${
          showMobileChatList ? "hidden md:flex" : "flex"
        }`}>

          {/* Chat header */}
          {currentChat && (
            <div className="px-5 py-3.5 border-b border-slate-100 dark:border-neutral-800 bg-white dark:bg-[#0A0A0A] flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3">
                {/* Back button on mobile */}
                <button
                  onClick={() => setShowMobileChatList(true)}
                  className="md:hidden p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors mr-1 cursor-pointer"
                  title="Back to conversations"
                >
                  <ArrowLeft size={18} />
                </button>
                <ChatAvatar chat={currentChat} />
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white leading-tight">
                    {currentChat.name}
                  </h3>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                    <span className="text-[10px] text-slate-500 dark:text-neutral-500 font-medium">
                      {currentChat.id.startsWith("team_") ? "5 members • 3 online" : "Active now"}
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 text-slate-400 dark:text-neutral-500">
                <button className="w-8 h-8 rounded-lg hover:bg-slate-50 dark:hover:bg-neutral-900 flex items-center justify-center transition-colors cursor-pointer">
                  <Users size={15} />
                </button>
                <button className="w-8 h-8 rounded-lg hover:bg-slate-50 dark:hover:bg-neutral-900 flex items-center justify-center transition-colors cursor-pointer">
                  <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="1"></circle><circle cx="12" cy="5" r="1"></circle><circle cx="12" cy="19" r="1"></circle></svg>
                </button>
              </div>
            </div>
          )}

          {/* Messages thread */}
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4 bg-[#FAFBFC] dark:bg-[#050505] scrollbar-none">

            {/* Date badge */}
            <div className="flex justify-center py-1">
              <span className="px-3 py-1 bg-white dark:bg-neutral-900 border border-slate-200/60 dark:border-neutral-800 text-slate-400 dark:text-neutral-500 rounded-full text-[10px] font-semibold">
                Today
              </span>
            </div>

            {(() => {
              const thread = chatMessages[activeChat] || [];

              if (thread.length === 0) {
                let placeholderText = "Send a message to start the conversation.";
                if (activeChat === "support") {
                  placeholderText = "Welcome to Support. Type your question below and we'll get back to you shortly.";
                } else if (activeChat.startsWith("mentor_")) {
                  placeholderText = `Start your conversation with ${currentChat?.name?.replace("Mentor ", "") || "your mentor"}.`;
                } else if (activeChat.startsWith("team_")) {
                  placeholderText = `Welcome to ${currentChat?.name || "your team"} chat! Collaborate with your team here.`;
                } else if (activeChat.startsWith("hiring_team_")) {
                  placeholderText = `Start chatting with the ${currentChat?.name || "hiring team"}.`;
                }
                return (
                  <div className="h-full flex items-center justify-center text-center">
                    <div className="max-w-xs flex flex-col items-center gap-3">
                      <div className="w-12 h-12 rounded-full bg-blue-50 dark:bg-[#2563EB]/10 flex items-center justify-center text-[#2563EB]">
                        <MessageSquare size={20} />
                      </div>
                      <p className="text-slate-400 dark:text-neutral-500 text-xs leading-relaxed">{placeholderText}</p>
                    </div>
                  </div>
                );
              }

              return thread.map((msg) => {
                const isUser = msg.sender === "user";
                return (
                  <div
                    key={msg.id}
                    className={`flex items-end gap-2 ${isUser ? "justify-end" : "justify-start"}`}
                  >
                    {!isUser && <SenderAvatar senderName={msg.sender_name} />}

                    <div className={`max-w-[65%] flex flex-col gap-0.5 ${isUser ? "items-end" : "items-start"}`}>
                      <span className={`text-[10px] text-slate-400 dark:text-neutral-500 font-medium px-1 ${isUser ? "text-right" : "text-left"}`}>
                        {isUser
                          ? `You • ${new Date(msg.sent_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
                          : `${msg.sender_name} • ${new Date(msg.sent_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`}
                      </span>
                      <div
                        className={`px-3.5 py-2.5 text-[13px] leading-relaxed ${
                          isUser
                            ? "bg-[#2563EB] text-white rounded-2xl rounded-br-md"
                            : "bg-white dark:bg-neutral-900 text-slate-800 dark:text-slate-200 border border-slate-200/60 dark:border-neutral-800 rounded-2xl rounded-bl-md"
                        }`}
                      >
                        <p className="whitespace-pre-wrap">{msg.text}</p>
                      </div>
                    </div>
                  </div>
                );
              });
            })()}
            <div ref={chatEndRef} />
          </div>

          {/* Input bar */}
          <div className="px-5 py-3 bg-white dark:bg-[#0A0A0A] border-t border-slate-100 dark:border-neutral-800 shrink-0">
            <div className="flex items-center gap-2 bg-slate-50 dark:bg-neutral-900 border border-slate-200 dark:border-neutral-800 rounded-full px-1.5 py-1">
              <button className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 dark:text-neutral-500 hover:text-slate-600 dark:hover:text-neutral-300 transition-colors cursor-pointer shrink-0">
                <Paperclip size={15} />
              </button>
              <input
                type="text"
                placeholder={getInputPlaceholder()}
                value={inputVal}
                onChange={(e) => setInputVal(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") handleSend(); }}
                className="flex-1 bg-transparent border-none outline-none focus:ring-0 px-1 py-1.5 text-[13px] text-slate-800 dark:text-white placeholder-slate-400 dark:placeholder-neutral-500"
              />
              <button
                onClick={handleSend}
                disabled={!inputVal.trim()}
                className="w-8 h-8 bg-[#2563EB] text-white rounded-full flex items-center justify-center hover:bg-[#1D4ED8] disabled:opacity-40 transition-all cursor-pointer shrink-0"
              >
                <Send size={14} />
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
