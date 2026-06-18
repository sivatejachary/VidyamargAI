"use client";

import React, { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { 
  GraduationCap, X, ArrowRight, Play, CheckSquare, Info, Plus, Mic, ArrowUp, 
  FileText, List, AlertTriangle, Sparkles, User, Flame, Award, Pin,
  Heart, Edit2, Trash2, CheckCircle2, ChevronRight, BookOpenCheck, Loader2, RefreshCw, Eye,
  Copy, Download, CheckCircle, Circle, MessageSquare, HelpCircle, FileSpreadsheet, PlayCircle, ToggleLeft, ToggleRight
} from "lucide-react";
import { apiService } from "@/services/api";
import { ProgressBar } from "@/components/ui/Progress";

interface AiMentorProps {
  email: string | null;
  fullName: string | null;
  profile: any;
  loadData: () => Promise<void>;
  setXp: React.SetStateAction<any>;
  enrollments: any[];
  courses: any[];
}

interface MentorSession {
  id: string;
  user_id: number;
  title: string;
  metadata_json: any;
  created_at: string;
  updated_at: string;
  is_deleted?: boolean;
}

interface MentorMessage {
  id: string;
  session_id: string;
  user_id: number;
  sender: string;
  message: string;
  metadata_json: any;
  created_at: string;
}

interface StudyPlan {
  id: string;
  user_id: number;
  duration: string;
  title: string;
  content: string;
  created_at: string;
}

interface Artifact {
  id: string;
  user_id: number;
  artifact_type: string;
  title: string;
  content: string;
  version: number;
  metadata_json: any;
  created_at: string;
}

interface Insight {
  id: string;
  user_id: number;
  insight_type: string;
  title: string;
  description: string;
  created_at: string;
}

interface MentorProfileStats {
  health_score: number;
  health_status: string;
  strengths: string[];
  weaknesses: string[];
  next_best_actions: string[];
  estimated_time: string;
  xp: number;
  level: number;
  streak: number;
  weekly_progress: number;
  courses_in_progress: number;
  completed_courses: number;
  completed_lessons_count: number;
  avg_quiz_score: number;
  upcoming_assessments: string[];
  insights: Insight[];
  enrolled_courses: { course_id: string; title: string; progress: number; status: string }[];
  career_goal: string;
  target_role?: string;
  target_level?: string;
  hours_learned: number;
  completed_certs: number;
  monthly_progress: number;
  risk_score: number;
  current_roadmap_stage: string;
  weekly_goal_progress: number;
  agent_status: string;
}

export default function AiMentor({
  email,
  fullName,
  profile,
  loadData,
  setXp,
  enrollments,
  courses
}: AiMentorProps) {
  const firstName = fullName ? fullName.split(" ")[0] : "Learner";

  // Tab State
  const [activeTab, setActiveTab] = useState<"dashboard" | "chat" | "study-plans" | "artifacts">("dashboard");

  // Feature flags configuration
  const [config, setConfig] = useState({
    ai_mentor_enabled: true,
    voice_mentor_enabled: false,
    study_plan_enabled: true,
    artifacts_enabled: true,
    search_enabled: true,
    analytics_enabled: false
  });

  // Search states (Global search vs. Chat sidebar filter)
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchPage, setSearchPage] = useState(1);
  const [searchHasMore, setSearchHasMore] = useState(false);
  const [searchType, setSearchType] = useState<"all" | "chat" | "studyplan" | "artifact">("all");
  const [sidebarSearchQuery, setSidebarSearchQuery] = useState("");

  // Cache & Profile Stats
  const [profileStats, setProfileStats] = useState<MentorProfileStats | null>(null);
  const [loadingProfile, setLoadingProfile] = useState(true);

  // Chat sessions list & messages
  const [chatSessions, setChatSessions] = useState<MentorSession[]>([]);
  const [pinnedSessions, setPinnedSessions] = useState<string[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<MentorMessage[]>([]);
  const [mentorQuery, setMentorQuery] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMode, setChatMode] = useState<"tutor" | "quiz" | "challenge" | "revision" | "interview">("tutor");
  const [agentMode, setAgentMode] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Autonomous Learning OS Dashboard states
  const [activityFeed, setActivityFeed] = useState<any[]>([]);
  const [loadingFeed, setLoadingFeed] = useState(false);
  const [agentRunning, setAgentRunning] = useState(false);

  // Study plans & Artifacts lists
  const [studyPlans, setStudyPlans] = useState<StudyPlan[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<StudyPlan | null>(null);
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [selectedDuration, setSelectedDuration] = useState("7-day");
  const [generatingPlan, setGeneratingPlan] = useState(false);
  // Checklist tracker state
  const [checkedTasks, setCheckedTasks] = useState<Record<string, boolean>>({});

  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);
  const [artifactFilter, setArtifactFilter] = useState<string>("all");

  // Auto-resize textarea ref
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  
  // Voice Input (Speech recognition) states
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  // Load configuration and bootstrap data
  useEffect(() => {
    const init = async () => {
      try {
        const cfg = await apiService.getAIMentorConfig();
        setConfig(cfg);
        if (cfg.ai_mentor_enabled) {
          fetchProfileData();
          fetchChatSessions();
          fetchActivityFeed();
          if (cfg.study_plan_enabled) fetchStudyPlans();
          if (cfg.artifacts_enabled) fetchArtifacts();
        }
      } catch (err) {
        console.error("Error loading config, falling back to defaults:", err);
        fetchProfileData();
        fetchChatSessions();
        fetchActivityFeed();
        fetchStudyPlans();
        fetchArtifacts();
      }
    };
    init();
  }, [enrollments]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
    }
  }, [mentorQuery]);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [chatMessages, chatLoading]);

  // API fetches
  const fetchProfileData = async () => {
    setLoadingProfile(true);
    try {
      const stats = await apiService.getAIMentorProfile();
      setProfileStats(stats);
    } catch (err) {
      console.error("Error fetching AI Mentor Profile:", err);
    } finally {
      setLoadingProfile(false);
    }
  };

  const fetchActivityFeed = async () => {
    setLoadingFeed(true);
    try {
      const feed = await apiService.getAgentActivityFeed();
      setActivityFeed(feed);
    } catch (err) {
      console.error("Error fetching activity feed:", err);
    } finally {
      setLoadingFeed(false);
    }
  };

  const fetchChatSessions = async (selectFirst: boolean = false) => {
    try {
      const sessions = await apiService.getAIMentorSessions();
      setChatSessions(sessions);
      if (sessions.length > 0) {
        if (selectFirst || !currentSessionId) {
          handleSelectSession(sessions[0].id);
        }
      } else {
        const newSession = await apiService.createAIMentorSession("Welcome Session");
        setChatSessions([newSession]);
        handleSelectSession(newSession.id);
      }
    } catch (err) {
      console.error("Error fetching sessions:", err);
    }
  };

  const fetchStudyPlans = async () => {
    try {
      const plans = await apiService.getAIMentorStudyPlans();
      setStudyPlans(plans);
    } catch (err) {
      console.error("Error fetching study plans:", err);
    }
  };

  const fetchArtifacts = async () => {
    try {
      const arts = await apiService.getAIMentorArtifacts();
      setArtifacts(arts);
    } catch (err) {
      console.error("Error fetching artifacts:", err);
    }
  };

  // Run supervisor agent manually
  const handleRunSupervisor = async () => {
    setAgentRunning(true);
    try {
      await apiService.runSupervisorAgent();
      await fetchProfileData();
      await fetchActivityFeed();
      if (config.study_plan_enabled) await fetchStudyPlans();
      if (config.artifacts_enabled) await fetchArtifacts();
    } catch (err) {
      console.error("Failed to run supervisor agent:", err);
    } finally {
      setAgentRunning(false);
    }
  };

  // Update target career goal dropdown select
  const handleSelectGoal = async (goal: string) => {
    setAgentRunning(true);
    try {
      await apiService.updateCareerGoal(goal);
      await fetchProfileData();
      await fetchActivityFeed();
      if (config.study_plan_enabled) await fetchStudyPlans();
      if (config.artifacts_enabled) await fetchArtifacts();
    } catch (err) {
      console.error("Failed to update goal:", err);
    } finally {
      setAgentRunning(false);
    }
  };

  const handleSelectSession = async (sessionId: string) => {
    setCurrentSessionId(sessionId);
    setChatMessages([]);
    try {
      const msgs = await apiService.getAIMentorMessages(sessionId);
      setChatMessages(msgs);
    } catch (err) {
      console.error("Error fetching messages:", err);
    }
  };

  const handleCreateSession = async () => {
    try {
      const title = `New Chat #${chatSessions.length + 1}`;
      const newSession = await apiService.createAIMentorSession(title);
      setChatSessions([newSession, ...chatSessions]);
      handleSelectSession(newSession.id);
    } catch (err) {
      console.error("Error creating session:", err);
    }
  };

  const handleRenameSession = async (sessionId: string) => {
    const newTitle = prompt("Enter new title for this conversation:");
    if (!newTitle || !newTitle.trim()) return;
    try {
      await apiService.renameAIMentorSession(sessionId, newTitle);
      setChatSessions(chatSessions.map(s => s.id === sessionId ? { ...s, title: newTitle } : s));
    } catch (err) {
      console.error("Error renaming session:", err);
    }
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to archive/delete this conversation?")) return;
    try {
      await apiService.deleteAIMentorSession(sessionId);
      const updated = chatSessions.filter(s => s.id !== sessionId);
      setChatSessions(updated);
      if (currentSessionId === sessionId) {
        if (updated.length > 0) {
          handleSelectSession(updated[0].id);
        } else {
          setCurrentSessionId(null);
          setChatMessages([]);
        }
      }
    } catch (err) {
      console.error("Error deleting session:", err);
    }
  };

  const handleTogglePin = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (pinnedSessions.includes(sessionId)) {
      setPinnedSessions(pinnedSessions.filter(id => id !== sessionId));
    } else {
      setPinnedSessions([sessionId, ...pinnedSessions]);
    }
  };

  const handleSearch = async (page: number = 1) => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const data = await apiService.searchAIMentor(searchQuery, searchType, page, 20);
      if (page === 1) {
        setSearchResults(data.results);
      } else {
        setSearchResults([...searchResults, ...data.results]);
      }
      setSearchHasMore(data.has_more);
      setSearchPage(page);
    } catch (err) {
      console.error("Error searching:", err);
    } finally {
      setSearching(false);
    }
  };

  const handleSelectSearchResult = (res: any) => {
    setSearchQuery("");
    setSearchResults([]);
    
    if (res.type === "chat_session") {
      setActiveTab("chat");
      handleSelectSession(res.id);
    } else if (res.type === "message") {
      setActiveTab("chat");
      handleSelectSession(res.session_id);
    } else if (res.type === "study_plan") {
      setActiveTab("study-plans");
      const found = studyPlans.find(p => p.id === res.id);
      if (found) {
        setSelectedPlan(found);
        setShowPlanModal(true);
      }
    } else {
      setActiveTab("artifacts");
      const found = artifacts.find(a => a.id === res.id);
      if (found) {
        setSelectedArtifact(found);
      }
    }
  };

  const handleSendChat = async () => {
    if (!mentorQuery.trim() || !currentSessionId || chatLoading) return;
    const userQuery = mentorQuery;
    setMentorQuery("");
    setChatLoading(true);

    const tempUserMsg: MentorMessage = {
      id: strUuid(),
      session_id: currentSessionId,
      user_id: 0,
      sender: "user",
      message: userQuery,
      metadata_json: {},
      created_at: new Date().toISOString()
    };

    setChatMessages((prev) => [...prev, tempUserMsg]);

    try {
      const res = await apiService.sendAIMentorChat(currentSessionId, userQuery, chatMode);
      
      const tempAiMsg: MentorMessage = {
        id: strUuid(),
        session_id: currentSessionId,
        user_id: 0,
        sender: "ai",
        message: res.response,
        metadata_json: {},
        created_at: new Date().toISOString()
      };
      setChatMessages((prev) => [...prev, tempAiMsg]);
      setXp((prev: number) => prev + 10);
      
      // Auto-trigger supervisor planning on agent mode or modes trigger
      if (agentMode || chatMode !== "tutor") {
        apiService.runSupervisorAgent().then(() => {
          fetchProfileData();
          fetchActivityFeed();
          fetchArtifacts();
        }).catch(err => console.error(err));
      }
    } catch (err: any) {
      console.error(err);
      const tempErrorMsg: MentorMessage = {
        id: strUuid(),
        session_id: currentSessionId,
        user_id: 0,
        sender: "ai",
        message: err.message || "Failed to receive AI guidance. Please try again.",
        metadata_json: {},
        created_at: new Date().toISOString()
      };
      setChatMessages((prev) => [...prev, tempErrorMsg]);
    } finally {
      setChatLoading(false);
      fetchChatSessions(false);
    }
  };

  const handleSendQuickAction = async (promptText: string, mode: typeof chatMode) => {
    setChatMode(mode);
    setMentorQuery(promptText);
    setActiveTab("chat");
  };

  // Helper utility to make UUID locally
  const strUuid = () => {
    return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
  };

  // Export Chat thread
  const handleExportChat = () => {
    if (chatMessages.length === 0) return;
    const chatTitle = chatSessions.find(s => s.id === currentSessionId)?.title || "Chat Export";
    const markdownText = chatMessages
      .map(m => `### ${m.sender === "user" ? "Student" : "AI Mentor"}\n${m.message}\n`)
      .join("\n");
      
    const blob = new Blob([markdownText], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${chatTitle.toLowerCase().replace(/\s+/g, "_")}_export.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Copy code blocks helper
  const handleCopyText = (text: string) => {
    navigator.clipboard.writeText(text);
    alert("Copied to clipboard!");
  };

  // Toggle checklist checkbox completion state
  const handleToggleTask = (taskKey: string) => {
    setCheckedTasks(prev => ({
      ...prev,
      [taskKey]: !prev[taskKey]
    }));
  };

  // Parse custom roadmapsNotes artifact
  const parsedRoadmap = useMemo(() => {
    const roadmapArt = artifacts.find(a => a.artifact_type === "notes" && a.title.includes("Roadmap"));
    if (roadmapArt && roadmapArt.metadata_json && Array.isArray(roadmapArt.metadata_json.stages)) {
      return {
        stages: roadmapArt.metadata_json.stages,
        current: roadmapArt.metadata_json.current_focus || "General"
      };
    }
    // Fallback standard stages
    const goal = profileStats?.career_goal || "Frontend Engineer";
    if (goal.toLowerCase().includes("frontend")) {
      return { stages: ["HTML", "CSS", "JavaScript", "React", "Next.js", "APIs", "System Design"], current: "React" };
    }
    return { stages: ["Programming Core", "Databases", "APIs", "Docker", "Cloud", "System Architecture"], current: "APIs" };
  }, [artifacts, profileStats]);

  // Voice recording handlers
  const startListening = () => {
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRec) {
      alert("Speech recognition is not supported in your browser.");
      return;
    }
    
    if (isListening) {
      if (recognitionRef.current) recognitionRef.current.stop();
      setIsListening(false);
      return;
    }

    const rec = new SpeechRec();
    rec.continuous = false;
    rec.lang = "en-US";
    rec.interimResults = false;

    rec.onstart = () => {
      setIsListening(true);
    };

    rec.onresult = (e: any) => {
      const transcript = e.results[0][0].transcript;
      setMentorQuery(prev => prev + (prev ? " " : "") + transcript);
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

  const renderMarkdown = (text: string) => {
    if (!text) return "";
    const lines = text.split("\n");
    return lines.map((line, idx) => {
      // Code blocks
      if (line.startsWith("```")) {
        return null; // Handle code blocks fully in wrapper if parsed, else treat simply
      }
      // Lists
      if (line.trim().startsWith("- ") || line.trim().startsWith("* ")) {
        return (
          <li key={idx} className="ml-4 list-disc pl-1 py-0.5 text-xs text-foreground font-semibold">
            {line.replace(/^[\s-*]+/, "")}
          </li>
        );
      }
      // Headers
      if (line.startsWith("#")) {
        const hSize = line.match(/^#+/)?.[0].length || 1;
        const hText = line.replace(/^#+\s*/, "");
        if (hSize === 1) return <h1 key={idx} className="text-sm font-black text-foreground mt-2 mb-1 border-b pb-0.5">{hText}</h1>;
        if (hSize === 2) return <h2 key={idx} className="text-xs font-black text-foreground mt-2 mb-1">{hText}</h2>;
        return <h3 key={idx} className="text-xs font-extrabold text-foreground mt-1 mb-0.5">{hText}</h3>;
      }
      return <p key={idx} className="text-xs py-0.5 text-foreground leading-normal font-semibold">{line}</p>;
    });
  };

  // Local sidebar session filtering
  const filteredSessions = useMemo(() => {
    return chatSessions.filter(s => 
      s.title.toLowerCase().includes(sidebarSearchQuery.toLowerCase())
    );
  }, [chatSessions, sidebarSearchQuery]);

  // Split chats between pinned and recent
  const pinnedList = useMemo(() => {
    return filteredSessions.filter(s => pinnedSessions.includes(s.id));
  }, [filteredSessions, pinnedSessions]);

  const recentList = useMemo(() => {
    return filteredSessions.filter(s => !pinnedSessions.includes(s.id));
  }, [filteredSessions, pinnedSessions]);

  const filteredArtifacts = useMemo(() => {
    if (artifactFilter === "all") return artifacts;
    return artifacts.filter(a => a.artifact_type === artifactFilter);
  }, [artifacts, artifactFilter]);

  // Main UI render
  if (!config.ai_mentor_enabled) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-card border border-border rounded-3xl gap-4">
        <GraduationCap className="w-16 h-16 text-muted-foreground" />
        <h3 className="text-base font-bold text-foreground">AI Mentor offline</h3>
        <p className="text-xs text-muted-foreground max-w-sm text-center">
          The AI Mentor Operating System is currently disabled in your portal settings.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full flex-1 min-h-0 relative">
      
      {/* Tab Navigation header */}
      <div className="flex items-center justify-between border-b border-border/80 pb-3 shrink-0">
        <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-none">
          {[
            { id: "dashboard", label: "Autonomous Learning OS" },
            { id: "chat", label: "AI Mentor Chat" },
            { id: "study-plans", label: "Study Plans" },
            { id: "artifacts", label: "Artifact Library" }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id as any);
                if (tab.id === "dashboard") {
                  fetchProfileData();
                  fetchActivityFeed();
                }
              }}
              className={`text-11 font-bold px-3 py-1.5 rounded-xl border transition-all cursor-pointer whitespace-nowrap ${
                activeTab === tab.id
                  ? "bg-indigo-600 border-indigo-600 text-white shadow-md shadow-indigo-600/10"
                  : "border-border bg-card text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Global Agent Status banner */}
        <div className="hidden sm:flex items-center gap-2 bg-slate-100 dark:bg-black/20 px-3 py-1.5 rounded-xl border border-border/50 text-[10px] font-semibold text-muted-foreground">
          <span className={`w-2 h-2 rounded-full ${agentRunning ? "bg-indigo-500 animate-spin" : "bg-emerald-500"}`} />
          <span>Agent OS: {agentRunning ? "Analyzing..." : "Sync Completed"}</span>
        </div>
      </div>

      <div className="flex-1 min-h-0 pt-4">

        {/* ────────────────── 1. LEARNING OS DASHBOARD ────────────────── */}
        {activeTab === "dashboard" && (
          <div className="h-full overflow-y-auto space-y-6 pr-1.5 scrollbar-thin pb-6">
            {loadingProfile ? (
              <div className="flex flex-col items-center justify-center h-80 gap-3">
                <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                <span className="text-xs text-muted-foreground font-bold">Assembling your Learning Operating System...</span>
              </div>
            ) : (
              <>
                {/* COMMAND CENTER METRICS */}
                <div className="bg-gradient-to-r from-slate-900 via-indigo-950/80 to-slate-900 border border-indigo-500/20 rounded-3xl p-5 shadow-xl relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
                  
                  <div className="relative z-10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-white/10 pb-4 mb-4">
                    <div>
                      <h3 className="text-sm font-black text-white flex items-center gap-1.5">
                        <Sparkles className="w-4 h-4 text-indigo-400" /> Command Center
                      </h3>
                      <p className="text-[10px] text-indigo-200 mt-0.5">Control settings & trigger autonomous subagents</p>
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                      {/* Active target goal dropdown */}
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-indigo-300 font-bold">Goal Target:</span>
                        <select
                          value={profileStats?.career_goal || "Frontend Engineer"}
                          onChange={(e) => handleSelectGoal(e.target.value)}
                          className="bg-black/40 text-white border border-white/20 rounded-xl px-2.5 py-1 text-xs font-bold focus:outline-none cursor-pointer hover:border-indigo-400"
                        >
                          <option value="Frontend Engineer" className="bg-slate-950 text-white">Frontend Engineer</option>
                          <option value="Backend Engineer" className="bg-slate-950 text-white">Backend Engineer</option>
                          <option value="AI Engineer" className="bg-slate-950 text-white">AI Engineer</option>
                          <option value="Data Analyst" className="bg-slate-950 text-white">Data Analyst</option>
                          <option value="Data Scientist" className="bg-slate-950 text-white">Data Scientist</option>
                          <option value="DevOps Engineer" className="bg-slate-950 text-white">DevOps Engineer</option>
                        </select>
                      </div>

                      {/* Manual trigger button */}
                      <button
                        onClick={handleRunSupervisor}
                        disabled={agentRunning}
                        className="px-4 py-1.8 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-800 text-white text-xs font-black rounded-xl shadow-lg shadow-indigo-600/30 flex items-center gap-1.5 cursor-pointer transition-all hover:scale-105 active:scale-95"
                      >
                        {agentRunning ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
                        <span>Sync Agents</span>
                      </button>
                    </div>
                  </div>

                  <div className="relative z-10 grid grid-cols-2 md:grid-cols-6 gap-4">
                    {/* Health Score circle */}
                    <div className="p-3 bg-black/30 border border-white/5 rounded-2xl flex flex-col justify-between">
                      <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Learning Health</span>
                      <div className="flex items-center gap-3 mt-2">
                        <div className="w-11 h-11 rounded-full border-2 border-indigo-500/50 flex items-center justify-center font-black text-white text-sm">
                          {Math.round(profileStats?.health_score || 84)}%
                        </div>
                        <span className="text-11 text-slate-200 font-extrabold">{profileStats?.health_status || "Improving"}</span>
                      </div>
                    </div>

                    {/* Risk score */}
                    <div className="p-3 bg-black/30 border border-white/5 rounded-2xl flex flex-col justify-between">
                      <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Risk Score</span>
                      <div className="mt-2 space-y-1">
                        <h4 className={`text-sm font-black ${
                          profileStats?.risk_score && profileStats.risk_score >= 60 ? "text-red-400 animate-pulse" : "text-emerald-400"
                        }`}>
                          {profileStats?.risk_score || 15}/100
                        </h4>
                        <ProgressBar value={profileStats?.risk_score || 15} className="h-1 bg-white/10" />
                      </div>
                    </div>

                    {/* Stage */}
                    <div className="p-3 bg-black/30 border border-white/5 rounded-2xl flex flex-col justify-between">
                      <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Roadmap Stage</span>
                      <h4 className="text-xs font-black text-indigo-300 mt-2 truncate">
                        {profileStats?.current_roadmap_stage || "React State"}
                      </h4>
                    </div>

                    {/* Weekly goal progress */}
                    <div className="p-3 bg-black/30 border border-white/5 rounded-2xl flex flex-col justify-between">
                      <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Weekly Progress</span>
                      <div className="mt-2 space-y-1">
                        <span className="text-xs font-black text-white block">
                          {Math.round(profileStats?.weekly_goal_progress || 0)}%
                        </span>
                        <ProgressBar value={profileStats?.weekly_goal_progress || 0} className="h-1 bg-white/10" />
                      </div>
                    </div>

                    {/* Status */}
                    <div className="p-3 bg-black/30 border border-white/5 rounded-2xl flex flex-col justify-between">
                      <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Agent Status</span>
                      <div className="flex items-center gap-1.5 mt-2.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                        <span className="text-xs font-black text-white">{profileStats?.agent_status || "Active"}</span>
                      </div>
                    </div>

                    {/* XP / Level info */}
                    <div className="p-3 bg-black/30 border border-white/5 rounded-2xl flex flex-col justify-between">
                      <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">XP Level</span>
                      <div className="flex items-baseline gap-1 mt-2">
                        <span className="text-sm font-black text-white">Lvl {profileStats?.level || 8}</span>
                        <span className="text-[9px] text-slate-400 font-bold">({profileStats?.xp || 1250} XP)</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  
                  {/* RECOMMENDED ACTIONS */}
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 dark:text-foreground">Recommended Actions</h4>
                      <p className="text-[10px] text-muted-foreground">Immediate steps to optimize learning health</p>
                    </div>

                    <div className="space-y-2">
                      <button
                        onClick={() => handleSendQuickAction("Create a 3-question MCQ quiz on React State.", "quiz")}
                        className="w-full p-3 bg-card border border-border hover:border-indigo-500/30 rounded-2xl flex items-center justify-between transition-all group cursor-pointer text-left"
                      >
                        <div className="flex items-center gap-2.5">
                          <HelpCircle className="w-4.5 h-4.5 text-indigo-500" />
                          <div>
                            <span className="text-xs font-bold text-foreground block">Take Topic Quiz</span>
                            <span className="text-[10px] text-muted-foreground">Evaluate recent study modules</span>
                          </div>
                        </div>
                        <ChevronRight size={14} className="text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
                      </button>

                      <button
                        onClick={() => handleSendQuickAction("Give me a coding challenge to write a React counter reducer.", "challenge")}
                        className="w-full p-3 bg-card border border-border hover:border-indigo-500/30 rounded-2xl flex items-center justify-between transition-all group cursor-pointer text-left"
                      >
                        <div className="flex items-center gap-2.5">
                          <CheckCircle className="w-4.5 h-4.5 text-emerald-500" />
                          <div>
                            <span className="text-xs font-bold text-foreground block">Practice Coding</span>
                            <span className="text-[10px] text-muted-foreground">Solve adaptive programming problems</span>
                          </div>
                        </div>
                        <ChevronRight size={14} className="text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
                      </button>

                      <button
                        onClick={() => handleSendQuickAction("Ask me interview questions on React lifecycle hooks.", "interview")}
                        className="w-full p-3 bg-card border border-border hover:border-indigo-500/30 rounded-2xl flex items-center justify-between transition-all group cursor-pointer text-left"
                      >
                        <div className="flex items-center gap-2.5">
                          <MessageSquare className="w-4.5 h-4.5 text-blue-500" />
                          <div>
                            <span className="text-xs font-bold text-foreground block">AI Mock Interview</span>
                            <span className="text-[10px] text-muted-foreground">Technical viva for current focus</span>
                          </div>
                        </div>
                        <ChevronRight size={14} className="text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
                      </button>

                      <button
                        onClick={() => setActiveTab("artifacts")}
                        className="w-full p-3 bg-card border border-border hover:border-indigo-500/30 rounded-2xl flex items-center justify-between transition-all group cursor-pointer text-left"
                      >
                        <div className="flex items-center gap-2.5">
                          <FileText className="w-4.5 h-4.5 text-violet-500" />
                          <div>
                            <span className="text-xs font-bold text-foreground block">Review Notes</span>
                            <span className="text-[10px] text-muted-foreground">Inspect saved summaries & guides</span>
                          </div>
                        </div>
                        <ChevronRight size={14} className="text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
                      </button>
                    </div>
                  </div>

                  {/* AI ACTIVITY FEED */}
                  <div className="space-y-4 md:col-span-2">
                    <div>
                      <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 dark:text-foreground">AI Activity Feed</h4>
                      <p className="text-[10px] text-muted-foreground">Live operations feed from learning subagents</p>
                    </div>

                    <div className="border border-border/80 rounded-2xl bg-card overflow-hidden">
                      <div className="max-h-[280px] overflow-y-auto divide-y divide-border/50 scrollbar-thin">
                        {loadingFeed ? (
                          <div className="p-6 text-center text-xs text-muted-foreground font-bold">Loading feed items...</div>
                        ) : activityFeed.map((item, index) => (
                          <div key={item.id || index} className="p-3.5 flex items-start gap-3.5 hover:bg-slate-50 dark:hover:bg-muted/10 transition-colors">
                            <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                              item.severity === "SUCCESS"
                                ? "bg-emerald-500 shadow-md shadow-emerald-500/30"
                                : item.severity === "WARNING"
                                ? "bg-amber-500 shadow-md shadow-amber-500/30"
                                : item.severity === "CRITICAL"
                                ? "bg-red-500 animate-pulse"
                                : "bg-blue-500"
                            }`} />
                            
                            <div className="flex-1 space-y-1">
                              <div className="flex justify-between items-start">
                                <span className="text-xs font-extrabold text-foreground">{item.title}</span>
                                <span className="text-[9px] text-muted-foreground font-semibold">
                                  {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </span>
                              </div>
                              <p className="text-11 text-muted-foreground font-bold">{item.description}</p>
                            </div>
                          </div>
                        ))}

                        {activityFeed.length === 0 && (
                          <div className="p-6 text-center text-xs text-muted-foreground font-bold">
                            No activities logged. Trigger supervisor sync above to populate the OS logs.
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                {/* VISUAL ROADMAP TIMELINE */}
                <div className="p-5 bg-card border border-border rounded-3xl space-y-4 shadow-sm">
                  <div>
                    <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 dark:text-foreground">Learning Roadmap timeline</h4>
                    <p className="text-[10px] text-muted-foreground">Interactive stages matched to your goal</p>
                  </div>

                  <div className="flex items-center gap-4 overflow-x-auto pb-4 pt-2 scrollbar-thin">
                    {parsedRoadmap.stages.map((stage: string, idx: number) => {
                      const isFocus = parsedRoadmap.current === stage;
                      const isPassed = idx < parsedRoadmap.stages.indexOf(parsedRoadmap.current);

                      return (
                        <React.Fragment key={stage}>
                          <div
                            onClick={() => handleSendQuickAction(`Explain the concepts included under ${stage} roadmap stage.`, "tutor")}
                            className={`px-4 py-3 rounded-2xl border flex flex-col items-center justify-center gap-1 min-w-[130px] max-w-[130px] cursor-pointer hover:scale-105 transition-all text-center ${
                              isFocus
                                ? "border-indigo-500 bg-indigo-500/5 shadow-sm"
                                : isPassed
                                ? "border-emerald-500/30 bg-emerald-500/5"
                                : "border-border bg-card"
                            }`}
                          >
                            <span className={`text-[9px] font-black uppercase tracking-widest ${
                              isFocus ? "text-indigo-500" : isPassed ? "text-emerald-500" : "text-muted-foreground"
                            }`}>
                              Stage {idx + 1}
                            </span>
                            <span className="text-xs font-extrabold text-foreground truncate w-full">{stage}</span>
                            <span className="text-[9px] text-muted-foreground mt-1 font-semibold">
                              {isFocus ? "Focusing" : isPassed ? "Passed" : "Upcoming"}
                            </span>
                          </div>

                          {idx < parsedRoadmap.stages.length - 1 && (
                            <div className="w-6 h-0.5 bg-border shrink-0" />
                          )}
                        </React.Fragment>
                      );
                    })}
                  </div>
                </div>

                {/* INSIGHTS CENTER */}
                <div className="p-5 bg-card border border-border rounded-3xl space-y-4">
                  <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 dark:text-foreground">AI Insights Center</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {profileStats?.insights.map((ins) => (
                      <div key={ins.id} className={`p-3.5 border rounded-2xl flex gap-3 ${
                        ins.insight_type === "achievement" 
                          ? "bg-emerald-500/5 dark:bg-emerald-500/10 border-emerald-500/15" 
                          : ins.insight_type === "warning"
                          ? "bg-red-500/5 dark:bg-red-500/10 border-red-500/15"
                          : "bg-blue-500/5 dark:bg-blue-500/10 border-blue-500/15"
                      }`}>
                        <div className="mt-0.5 shrink-0">
                          {ins.insight_type === "achievement" ? (
                            <Award className="w-5 h-5 text-emerald-500" />
                          ) : ins.insight_type === "warning" ? (
                            <AlertTriangle className="w-5 h-5 text-red-500 animate-pulse" />
                          ) : (
                            <Sparkles className="w-5 h-5 text-blue-500" />
                          )}
                        </div>
                        <div>
                          <span className="text-xs font-black text-slate-900 dark:text-foreground block">{ins.title}</span>
                          <p className="text-11 text-muted-foreground font-bold mt-1 leading-normal">{ins.description}</p>
                        </div>
                      </div>
                    ))}

                    {profileStats?.insights.length === 0 && (
                      <div className="col-span-2 text-center py-6 text-xs text-muted-foreground font-bold">
                        No custom insights generated. Quizzes & lessons completed automatically populates warning or milestone alerts.
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* ────────────────── 2. CHAT EXPERIENCE ────────────────── */}
        {activeTab === "chat" && (
          <div className="h-full flex overflow-hidden border border-border rounded-3xl bg-card relative min-h-0">
            
            {/* Sidebar toggle button (mobile only) */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="absolute md:hidden top-3.5 left-4 z-20 p-1 bg-slate-100 hover:bg-slate-200 dark:bg-muted dark:hover:bg-[#374151] text-muted-foreground hover:text-foreground rounded-lg transition-colors cursor-pointer"
            >
              <List size={16} />
            </button>

            {/* Sidebar pane */}
            <div className={`absolute md:static top-0 left-0 h-full w-64 bg-slate-50 dark:bg-black/40 border-r border-border shrink-0 z-10 flex flex-col transition-transform duration-300 md:translate-x-0 ${
              sidebarOpen ? "translate-x-0" : "-translate-x-full"
            }`}>
              
              {/* Header */}
              <div className="p-4 border-b border-border flex justify-between items-center shrink-0">
                <span className="text-xs font-black text-foreground uppercase tracking-wider">Conversations</span>
                <button
                  onClick={handleCreateSession}
                  className="p-1.5 bg-white hover:bg-slate-50 dark:bg-card dark:hover:bg-muted border border-border text-indigo-500 rounded-lg cursor-pointer transition-colors"
                  title="New Session"
                >
                  <Plus size={15} />
                </button>
              </div>

              {/* Sidebar Search Chats */}
              <div className="p-3 border-b border-border shrink-0">
                <input
                  type="text"
                  placeholder="Filter chat history..."
                  value={sidebarSearchQuery}
                  onChange={(e) => setSidebarSearchQuery(e.target.value)}
                  className="w-full bg-white dark:bg-card border border-border rounded-xl px-3 py-1.5 text-xs text-foreground placeholder-muted-foreground font-semibold focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Pinned and Recent Sessions lists */}
              <div className="flex-1 overflow-y-auto p-2 space-y-3 scrollbar-thin">
                
                {/* Pinned list */}
                {pinnedList.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-[9px] font-black text-muted-foreground px-2 uppercase tracking-wider block">Pinned</span>
                    {pinnedList.map(s => (
                      <div
                        key={s.id}
                        onClick={() => {
                          handleSelectSession(s.id);
                          setSidebarOpen(false);
                        }}
                        className={`group p-2.5 rounded-xl flex items-center justify-between cursor-pointer transition-all ${
                          currentSessionId === s.id
                            ? "bg-indigo-500/10 border border-indigo-500/20 text-indigo-600 dark:text-indigo-400"
                            : "hover:bg-slate-100 dark:hover:bg-muted/30 text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        <div className="flex items-center gap-2 truncate pr-2">
                          <Pin size={12} className="text-indigo-500 shrink-0" />
                          <span className="text-xs font-bold truncate">{s.title}</span>
                        </div>
                        <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={(e) => handleTogglePin(s.id, e)}
                            className="p-0.5 hover:bg-slate-200 dark:hover:bg-[#374151] rounded text-slate-500 hover:text-slate-700 cursor-pointer"
                            title="Unpin"
                          >
                            <X size={11} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Recent list */}
                <div className="space-y-1">
                  <span className="text-[9px] font-black text-muted-foreground px-2 uppercase tracking-wider block">Recent Chats</span>
                  {recentList.map(s => (
                    <div
                      key={s.id}
                      onClick={() => {
                        handleSelectSession(s.id);
                        setSidebarOpen(false);
                      }}
                      className={`group p-2.5 rounded-xl flex items-center justify-between cursor-pointer transition-all ${
                        currentSessionId === s.id
                          ? "bg-indigo-500/10 border border-indigo-500/20 text-indigo-600 dark:text-indigo-400"
                          : "hover:bg-slate-100 dark:hover:bg-muted/30 text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <div className="flex items-center gap-2 truncate pr-2">
                        <GraduationCap className="w-4 h-4 shrink-0 text-slate-400" />
                        <span className="text-xs font-bold truncate">{s.title}</span>
                      </div>
                      <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => handleTogglePin(s.id, e)}
                          className="p-0.5 hover:bg-slate-200 dark:hover:bg-[#374151] rounded text-slate-500 hover:text-slate-700 cursor-pointer"
                          title="Pin conversation"
                        >
                          <Pin size={11} />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRenameSession(s.id);
                          }}
                          className="p-0.5 hover:bg-slate-200 dark:hover:bg-[#374151] rounded text-slate-500 hover:text-slate-700 cursor-pointer"
                        >
                          <Edit2 size={11} />
                        </button>
                        <button
                          onClick={(e) => handleDeleteSession(s.id, e)}
                          className="p-0.5 hover:bg-slate-250 dark:hover:bg-[#374151] rounded text-red-500 hover:text-red-700 cursor-pointer"
                        >
                          <Trash2 size={11} />
                        </button>
                      </div>
                    </div>
                  ))}

                  {recentList.length === 0 && (
                    <div className="text-center py-6 text-xs text-muted-foreground font-bold">No matching chats.</div>
                  )}
                </div>
              </div>

              {/* Mode Selection */}
              <div className="p-3 border-t border-border bg-slate-50/50 dark:bg-black/10 shrink-0">
                <label className="text-[9px] font-black uppercase tracking-wider text-muted-foreground block mb-1">Mentor Mode</label>
                <select
                  value={chatMode}
                  onChange={(e) => setChatMode(e.target.value as any)}
                  className="w-full bg-white dark:bg-card border border-border rounded-xl p-2 text-xs text-foreground font-semibold focus:outline-none focus:border-indigo-500 cursor-pointer mb-3"
                >
                  <option value="tutor">Tutor Mode</option>
                  <option value="quiz">Quiz Mode</option>
                  <option value="challenge">Challenge Mode</option>
                  <option value="revision">Revision Mode</option>
                  <option value="interview">Interview Mode</option>
                </select>

                {/* Agent mode toggle switch */}
                <div className="flex items-center justify-between bg-white dark:bg-card border border-border p-2 rounded-xl">
                  <span className="text-[9px] font-black uppercase tracking-wider text-slate-700 dark:text-slate-300">Agent Mode</span>
                  <button
                    onClick={() => setAgentMode(!agentMode)}
                    className="text-indigo-600 hover:text-indigo-700 transition-colors cursor-pointer"
                  >
                    {agentMode ? <ToggleRight size={26} /> : <ToggleLeft size={26} className="text-slate-400" />}
                  </button>
                </div>
              </div>
            </div>

            {/* Chat Thread Panel */}
            <div className="flex-1 flex flex-col h-full overflow-hidden min-h-0 relative bg-slate-50/10">
              
              {/* Export and header controls */}
              <div className="border-b border-border/80 p-3 bg-white dark:bg-card flex items-center justify-between shrink-0 pl-12 md:pl-4">
                <span className="text-xs font-bold text-foreground truncate">
                  {chatSessions.find(s => s.id === currentSessionId)?.title || "AI Mentor Chat"}
                </span>

                <button
                  onClick={handleExportChat}
                  disabled={chatMessages.length === 0}
                  className="px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 disabled:bg-slate-50 dark:bg-indigo-950/20 text-indigo-600 dark:text-indigo-400 rounded-lg text-[10px] font-bold border border-indigo-500/10 flex items-center gap-1 cursor-pointer transition-colors"
                >
                  <Download size={12} />
                  <span>Export Chat</span>
                </button>
              </div>

              {/* Agent mode active banner */}
              {agentMode && (
                <div className="bg-indigo-500/10 border-b border-indigo-500/20 px-4 py-1.8 text-[10px] font-semibold text-indigo-400 flex items-center gap-1.5 shrink-0">
                  <Sparkles size={11} className="animate-pulse" />
                  <span>Agent Mode Active: supervisor will automatically execute roadmap & quiz planners.</span>
                </div>
              )}

              {/* Messages thread */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
                {chatMessages.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center max-w-sm mx-auto text-center gap-4 py-8">
                    <GraduationCap className="w-12 h-12 text-indigo-500 bg-indigo-500/5 p-2.5 rounded-2xl" />
                    <div>
                      <h4 className="text-xs font-black text-slate-800 dark:text-foreground">Autonomous AI Mentor</h4>
                      <p className="text-xs text-muted-foreground font-bold mt-1.5 leading-normal">
                        Select a mode from the sidebar options to generate tailored study sheets, quizzes, or structured mock viva questions.
                      </p>
                    </div>
                  </div>
                ) : (
                  chatMessages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex flex-col gap-1.5 max-w-[85%] ${
                        msg.sender === "user" ? "self-end items-end ml-auto" : "self-start items-start mr-auto"
                      }`}
                    >
                      <span className="text-[9px] font-black uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                        {msg.sender === "user" ? <User size={10} /> : <span>🤖</span>}
                        <span>{msg.sender === "user" ? "You" : "AI Mentor"}</span>
                      </span>
                      <div
                        className={`p-3.5 rounded-2xl text-xs leading-relaxed border relative group ${
                          msg.sender === "user"
                            ? "bg-indigo-50 dark:bg-indigo-950/20 text-slate-900 dark:text-foreground border-indigo-100 dark:border-indigo-900/30 rounded-tr-sm"
                            : "bg-white dark:bg-[#1f2937]/50 border-border text-foreground dark:text-foreground rounded-tl-sm"
                        }`}
                      >
                        {renderMarkdown(msg.message)}
                        
                        {/* Copy button */}
                        <button
                          onClick={() => handleCopyText(msg.message)}
                          className="absolute right-2 top-2 p-1 bg-muted hover:bg-muted-hover text-muted-foreground hover:text-foreground rounded opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                          title="Copy message text"
                        >
                          <Copy size={11} />
                        </button>
                      </div>
                    </div>
                  ))
                )}

                {chatLoading && (
                  <div className="flex flex-col gap-1.5 max-w-xs self-start items-start">
                    <span className="text-[9px] font-black uppercase tracking-wider text-muted-foreground">AI Mentor</span>
                    <div className="p-3.5 bg-white dark:bg-[#1f2937]/50 border border-border text-foreground dark:text-foreground rounded-2xl rounded-tl-sm flex items-center gap-2 shadow-sm">
                      <Loader2 className="w-4 h-4 text-indigo-500 animate-spin" />
                      <span className="text-10 font-bold text-muted-foreground">Thinking...</span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Suggestions Toolbar */}
              <div className="px-4 py-2 border-t border-border bg-slate-50/50 dark:bg-black/10 flex items-center gap-2 overflow-x-auto scrollbar-none shrink-0">
                <span className="text-[9px] font-black text-indigo-500 uppercase tracking-wider shrink-0">Quick Options:</span>
                {[
                  { label: "Practice MCQ Quiz", prompt: "Create a 3-question MCQ quiz on Python functions.", mode: "quiz" as const },
                  { label: "Coding Challenge", prompt: "Give me an easy coding challenge to reverse a string.", mode: "challenge" as const },
                  { label: "Master OOP", prompt: "Explain polymorphism in Object Oriented Programming with a simple code block.", mode: "tutor" as const },
                  { label: "Mock Viva Questions", prompt: "Ask me a viva question on database normalization.", mode: "interview" as const }
                ].map((act, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendQuickAction(act.prompt, act.mode)}
                    className="px-2.5 py-1 bg-white hover:bg-slate-50 dark:bg-card dark:hover:bg-muted border border-border rounded-full text-10 font-bold text-slate-800 dark:text-foreground cursor-pointer transition-colors whitespace-nowrap shrink-0"
                  >
                    {act.label}
                  </button>
                ))}
              </div>

              {/* Input controls */}
              <div className="p-4 border-t border-border bg-white dark:bg-card shrink-0 flex items-end gap-2">
                <div className="flex-1 bg-slate-50 dark:bg-black/30 border border-border focus-within:border-indigo-500/50 rounded-2xl p-1.5 flex items-end">
                  <textarea
                    ref={textareaRef}
                    rows={1}
                    value={mentorQuery}
                    onChange={(e) => setMentorQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleSendChat();
                      }
                    }}
                    placeholder="Ask AI Mentor for explanations, quizes or code..."
                    className="w-full bg-transparent resize-none border-none outline-none focus:ring-0 text-xs text-foreground placeholder-muted-foreground px-2 py-1 max-h-36 overflow-y-auto"
                  />
                  
                  {config.voice_mentor_enabled && (
                    <button
                      onClick={startListening}
                      className={`p-2 rounded-xl transition-all shrink-0 ${
                        isListening ? "bg-red-500 text-white animate-pulse" : "text-muted-foreground hover:text-foreground hover:bg-slate-100 dark:hover:bg-muted"
                      }`}
                    >
                      <Mic size={15} />
                    </button>
                  )}
                </div>

                <button
                  onClick={handleSendChat}
                  disabled={!mentorQuery.trim() || chatLoading}
                  className={`p-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-100 disabled:text-slate-400 dark:disabled:bg-background text-white rounded-2xl shrink-0 cursor-pointer shadow-sm transition-all`}
                >
                  <ArrowUp size={16} />
                </button>
              </div>

            </div>
          </div>
        )}

        {/* ────────────────── 3. STUDY PLANS TAB ────────────────── */}
        {activeTab === "study-plans" && (
          <div className="h-full overflow-y-auto space-y-6 pr-1.5 scrollbar-thin pb-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
              <div>
                <h3 className="text-sm font-black text-foreground">Personalized Study Plans</h3>
                <p className="text-[10px] text-muted-foreground">Generates structured curriculum timelines for durations</p>
              </div>

              <div className="flex items-center gap-2 bg-card border border-border p-1.5 rounded-2xl">
                <select
                  value={selectedDuration}
                  onChange={(e) => setSelectedDuration(e.target.value)}
                  className="bg-transparent text-xs font-bold px-2 py-1 border-none focus:outline-none cursor-pointer text-foreground"
                >
                  <option value="7-day">7-Day Plan</option>
                  <option value="30-day">30-Day Plan</option>
                  <option value="90-day">90-Day Plan</option>
                </select>
                
                <button
                  onClick={async () => {
                    setGeneratingPlan(true);
                    try {
                      await apiService.generateAIMentorStudyPlan(selectedDuration, `${selectedDuration === "7-day" ? "7-Day" : selectedDuration === "30-day" ? "30-Day" : "90-Day"} Plan`);
                      await fetchStudyPlans();
                    } catch (err) {
                      console.error("Failed to generate plan:", err);
                    } finally {
                      setGeneratingPlan(false);
                    }
                  }}
                  disabled={generatingPlan}
                  className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-700 text-white rounded-xl text-[10px] font-black cursor-pointer shadow-sm flex items-center gap-1.5"
                >
                  {generatingPlan ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
                  <span>Generate Plan</span>
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {studyPlans.map(plan => {
                const checkedCount = Object.keys(checkedTasks).filter(k => k.startsWith(plan.id) && checkedTasks[k]).length;
                
                // Parse bullet points from content
                const lines = plan.content.split("\n");
                const tasks = lines.filter(l => l.trim().startsWith("- [ ]") || l.trim().startsWith("- ") || l.trim().startsWith("* "));
                const progressPct = tasks.length > 0 ? Math.round((checkedCount / tasks.length) * 100) : 0;

                return (
                  <div key={plan.id} className="p-4 bg-card border border-border rounded-3xl flex flex-col justify-between gap-4 shadow-sm hover:scale-[1.01] transition-all">
                    <div className="space-y-3">
                      <div className="flex justify-between items-start">
                        <span className="text-[9px] font-black uppercase tracking-wider text-indigo-500 bg-indigo-500/5 px-2 py-0.5 rounded border border-indigo-500/10">
                          {plan.duration}
                        </span>
                        <span className="text-[10px] text-muted-foreground font-semibold">
                          {new Date(plan.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      
                      <h4 className="text-xs font-black text-foreground">{plan.title}</h4>
                      <div className="space-y-2 max-h-48 overflow-y-auto pr-1 scrollbar-thin">
                        {tasks.map((t, idx) => {
                          const taskKey = `${plan.id}-${idx}`;
                          const isChecked = checkedTasks[taskKey] || false;
                          const cleanText = t.replace(/^[\s-*\[\]]+/, "");
                          return (
                            <div key={idx} className="flex items-start gap-2.5">
                              <button
                                onClick={() => handleToggleTask(taskKey)}
                                className={`mt-0.5 shrink-0 transition-colors cursor-pointer ${
                                  isChecked ? "text-emerald-500" : "text-muted-foreground hover:text-foreground"
                                }`}
                              >
                                {isChecked ? <CheckCircle size={14} /> : <Circle size={14} />}
                              </button>
                              <span className={`text-[11px] leading-tight font-semibold ${
                                isChecked ? "line-through text-muted-foreground" : "text-foreground"
                              }`}>
                                {cleanText}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <div className="space-y-2 pt-2 border-t border-border/50">
                      <div className="flex justify-between text-[10px] text-muted-foreground font-bold">
                        <span>Task Completion</span>
                        <span>{progressPct}%</span>
                      </div>
                      <ProgressBar value={progressPct} className="h-1 bg-slate-100" />
                      <button
                        onClick={() => {
                          setSelectedPlan(plan);
                          setShowPlanModal(true);
                        }}
                        className="w-full mt-2 py-1.8 bg-indigo-50 dark:bg-indigo-950/20 text-indigo-600 dark:text-indigo-400 rounded-xl text-[10px] font-black border border-indigo-500/10 cursor-pointer flex items-center justify-center gap-1.5"
                      >
                        <Eye size={12} />
                        <span>Inspect Full Plan</span>
                      </button>
                    </div>
                  </div>
                );
              })}

              {studyPlans.length === 0 && (
                <div className="col-span-3 text-center py-12 bg-slate-50 dark:bg-black/10 border border-dashed border-border rounded-3xl text-xs text-muted-foreground font-bold">
                  No study plans generated. Select a duration and click generate above.
                </div>
              )}
            </div>
          </div>
        )}

        {/* ────────────────── 4. ARTIFACT LIBRARY TAB ────────────────── */}
        {activeTab === "artifacts" && (
          <div className="h-full flex gap-5 min-h-0">
            {/* Artifact list */}
            <div className="flex-1 flex flex-col min-h-0 bg-card border border-border rounded-3xl p-4 shadow-sm overflow-hidden">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 border-b border-border/80 pb-3 shrink-0 mb-4">
                <div>
                  <h4 className="text-xs font-black text-foreground uppercase tracking-wider">Artifacts Registry</h4>
                  <p className="text-[10px] text-muted-foreground">Versioned notes, challenge codes, and mock sets</p>
                </div>
                
                {/* Filters */}
                <div className="flex flex-wrap items-center gap-1.5">
                  {["all", "quiz", "challenge", "notes", "questions"].map(type => (
                    <button
                      key={type}
                      onClick={() => setArtifactFilter(type)}
                      className={`px-2 py-1 rounded-lg text-[9px] font-black uppercase tracking-wider border transition-all cursor-pointer ${
                        artifactFilter === type
                          ? "bg-indigo-600 border-indigo-600 text-white"
                          : "border-border hover:bg-slate-50 dark:hover:bg-muted/30 text-muted-foreground"
                      }`}
                    >
                      {type}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex-1 overflow-y-auto space-y-2 pr-1.5 scrollbar-thin">
                {filteredArtifacts.map(art => (
                  <div
                    key={art.id}
                    onClick={() => setSelectedArtifact(art)}
                    className={`p-3 rounded-2xl border transition-all cursor-pointer flex items-center justify-between group ${
                      selectedArtifact?.id === art.id
                        ? "border-indigo-500 bg-indigo-500/5"
                        : "border-border hover:border-indigo-500/30 bg-card/50"
                    }`}
                  >
                    <div className="space-y-1.5 truncate pr-3">
                      <div className="flex items-center gap-2 truncate">
                        <span className={`text-[9px] font-black px-1.5 py-0.5 rounded uppercase tracking-wider ${
                          art.artifact_type === "quiz"
                            ? "bg-amber-500/10 text-amber-600"
                            : art.artifact_type === "challenge"
                            ? "bg-emerald-500/10 text-emerald-600"
                            : art.artifact_type === "questions"
                            ? "bg-blue-500/10 text-blue-600"
                            : "bg-purple-500/10 text-purple-600"
                        }`}>
                          {art.artifact_type}
                        </span>
                        <h5 className="text-xs font-extrabold text-foreground truncate">{art.title}</h5>
                      </div>
                      <p className="text-[10px] text-muted-foreground font-semibold">
                        Version {art.version} • Created on {new Date(art.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    
                    <button className="p-1 bg-white hover:bg-slate-50 dark:bg-card dark:hover:bg-muted border border-border text-muted-foreground rounded-lg opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer">
                      <ChevronRight size={13} />
                    </button>
                  </div>
                ))}

                {filteredArtifacts.length === 0 && (
                  <div className="text-center py-12 text-xs text-muted-foreground font-bold">
                    No artifacts found matching this category.
                  </div>
                )}
              </div>
            </div>

            {/* Markdown Preview Drawer panel */}
            <div className={`hidden lg:flex w-[400px] border border-border rounded-3xl bg-card p-4 shadow-sm flex-col min-h-0 overflow-hidden transition-all duration-300`}>
              {selectedArtifact ? (
                <div className="h-full flex flex-col min-h-0">
                  <div className="border-b border-border/80 pb-3 flex justify-between items-start shrink-0 mb-4">
                    <div className="space-y-1 pr-4">
                      <h4 className="text-xs font-black text-foreground">{selectedArtifact.title}</h4>
                      <p className="text-[10px] text-indigo-500 font-bold uppercase tracking-wider">
                        {selectedArtifact.artifact_type} • Version {selectedArtifact.version}
                      </p>
                    </div>
                    <button
                      onClick={() => setSelectedArtifact(null)}
                      className="text-muted-foreground hover:text-foreground cursor-pointer"
                    >
                      <X size={15} />
                    </button>
                  </div>

                  <div className="flex-1 overflow-y-auto pr-1 scrollbar-thin text-xs space-y-3 p-2 border border-border bg-slate-50/50 dark:bg-black/10 rounded-2xl">
                    {renderMarkdown(selectedArtifact.content)}
                  </div>
                  
                  <div className="pt-3 border-t border-border/80 flex items-center justify-between shrink-0 mt-4">
                    <button
                      onClick={() => handleCopyText(selectedArtifact.content)}
                      className="px-3 py-1.8 bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/20 text-indigo-600 dark:text-indigo-400 rounded-xl text-[10px] font-black border border-indigo-500/10 cursor-pointer flex items-center gap-1 transition-colors"
                    >
                      <Copy size={12} />
                      <span>Copy content</span>
                    </button>

                    <button
                      onClick={() => {
                        const blob = new Blob([selectedArtifact.content], { type: "text/markdown" });
                        const url = URL.createObjectURL(blob);
                        const link = document.createElement("a");
                        link.href = url;
                        link.download = `${selectedArtifact.title.toLowerCase().replace(/\s+/g, "_")}.md`;
                        link.click();
                        URL.revokeObjectURL(url);
                      }}
                      className="px-3 py-1.8 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-[10px] font-black border border-slate-700 cursor-pointer flex items-center gap-1 transition-colors"
                    >
                      <Download size={12} />
                      <span>Download MD</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-center text-xs text-muted-foreground font-bold p-8">
                  <span>Select an artifact to preview formatted notes, MCQs, or challenge instructions.</span>
                </div>
              )}
            </div>

          </div>
        )}

      </div>

      {/* Study Plan Full View Modal */}
      {showPlanModal && selectedPlan && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-background border border-border w-full max-w-2xl h-[75vh] rounded-3xl overflow-hidden flex flex-col shadow-2xl">
            <div className="p-5 border-b border-border flex justify-between items-start bg-indigo-600 text-white shrink-0">
              <div className="space-y-1">
                <span className="text-[9px] font-black bg-white/20 px-2 py-0.5 rounded text-white uppercase tracking-wider">
                  {selectedPlan.duration} Plan
                </span>
                <h3 className="text-sm font-black">{selectedPlan.title}</h3>
              </div>
              <button
                onClick={() => setShowPlanModal(false)}
                className="text-white/60 hover:text-white transition-colors cursor-pointer"
              >
                <X size={20} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50 dark:bg-slate-900/40">
              {renderMarkdown(selectedPlan.content)}
            </div>

            <div className="p-4 border-t border-border shrink-0 flex items-center justify-end bg-card">
              <button
                onClick={() => setShowPlanModal(false)}
                className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-bold cursor-pointer transition-colors"
              >
                Close Plan
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Artifact Library mobile viewer modal */}
      {selectedArtifact && (
        <div className="lg:hidden fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-background border border-border w-full max-w-lg h-[75vh] rounded-3xl overflow-hidden flex flex-col shadow-2xl">
            <div className="p-5 border-b border-border flex justify-between items-start shrink-0">
              <div className="space-y-1">
                <span className="text-[9px] font-black bg-indigo-500/10 text-indigo-500 px-2 py-0.5 rounded uppercase tracking-wider">
                  {selectedArtifact.artifact_type}
                </span>
                <h3 className="text-sm font-black text-foreground">{selectedArtifact.title}</h3>
              </div>
              <button
                onClick={() => setSelectedArtifact(null)}
                className="text-muted-foreground hover:text-foreground cursor-pointer"
              >
                <X size={20} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-50 dark:bg-slate-900/40">
              {renderMarkdown(selectedArtifact.content)}
            </div>

            <div className="p-4 border-t border-border shrink-0 flex items-center justify-between bg-card">
              <button
                onClick={() => handleCopyText(selectedArtifact.content)}
                className="px-3.5 py-1.8 bg-indigo-50 dark:bg-indigo-950/20 text-indigo-600 dark:text-indigo-400 rounded-xl text-10 font-black border border-indigo-500/10 cursor-pointer"
              >
                Copy Text
              </button>
              <button
                onClick={() => setSelectedArtifact(null)}
                className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-bold cursor-pointer"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
