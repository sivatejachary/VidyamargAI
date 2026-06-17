"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  GraduationCap, X, ArrowRight, Play, CheckSquare, Info, Plus, Mic, ArrowUp, 
  FileText, List, AlertTriangle, Sparkles, BookOpen, User, Flame, Award, 
  Heart, Edit2, Trash2, CheckCircle2, ChevronRight, BookOpenCheck, Loader2, RefreshCw, Eye
} from "lucide-react";
import { apiService } from "@/services/api";

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

  // Cache & Profile Stats
  const [profileStats, setProfileStats] = useState<MentorProfileStats | null>(null);
  const [riskAnalysis, setRiskAnalysis] = useState<{ risk_level: string; reason: string } | null>(null);
  const [loadingProfile, setLoadingProfile] = useState(true);

  // Chat sessions list & messages
  const [chatSessions, setChatSessions] = useState<MentorSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<MentorMessage[]>([]);
  const [mentorQuery, setMentorQuery] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMode, setChatMode] = useState<"tutor" | "quiz" | "challenge" | "revision" | "interview">("tutor");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Study plans & Artifacts lists
  const [studyPlans, setStudyPlans] = useState<StudyPlan[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<StudyPlan | null>(null);
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [selectedDuration, setSelectedDuration] = useState("7-day");
  const [generatingPlan, setGeneratingPlan] = useState(false);

  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);

  // Auto-resize textarea ref
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  
  // Voice Input (Speech recognition) states
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  // Trigger data fetch on tab switch or mount
  useEffect(() => {
    fetchProfileData();
    fetchChatSessions();
    fetchStudyPlans();
    fetchArtifacts();
  }, []);

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

  // API calls
  const fetchProfileData = async () => {
    setLoadingProfile(true);
    try {
      const stats = await apiService.getAIMentorProfile();
      setProfileStats(stats);
      const risk = await apiService.getAIMentorRiskAnalysis();
      setRiskAnalysis(risk);
    } catch (err) {
      console.error("Error fetching AI Mentor Profile:", err);
    } finally {
      setLoadingProfile(false);
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
        // Automatically create a default session if empty
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
    if (!confirm("Are you sure you want to delete this session?")) return;
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

  const handleSendChat = async () => {
    if (!mentorQuery.trim() || !currentSessionId || chatLoading) return;
    const query = mentorQuery;
    setMentorQuery("");
    
    // Optimistic user update
    const optimisticMsg: MentorMessage = {
      id: String(Date.now()),
      session_id: currentSessionId,
      user_id: 0,
      sender: "user",
      message: query,
      metadata_json: {},
      created_at: new Date().toISOString()
    };
    setChatMessages(prev => [...prev, optimisticMsg]);
    setChatLoading(true);

    try {
      const res = await apiService.sendAIMentorChat(currentSessionId, query, chatMode);
      
      // Update message thread
      const msgs = await apiService.getAIMentorMessages(currentSessionId);
      setChatMessages(msgs);

      // Auto update sidebar titles if name changed on first prompt
      const sIndex = chatSessions.findIndex(s => s.id === currentSessionId);
      if (sIndex > -1 && (chatSessions[sIndex].title.startsWith("New Chat") || chatSessions[sIndex].title === "Welcome Session")) {
        fetchChatSessions();
      }

      // If user requested quiz/coding challenge, also refetch artifacts
      if (chatMode !== "tutor") {
        fetchArtifacts();
      }
    } catch (err: any) {
      console.error("Error sending chat:", err);
      const errMsg: MentorMessage = {
        id: String(Date.now() + 1),
        session_id: currentSessionId,
        user_id: 0,
        sender: "ai",
        message: err.message || "I encountered an error processing your query. Please try again.",
        metadata_json: {},
        created_at: new Date().toISOString()
      };
      setChatMessages(prev => [...prev, errMsg]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleSendQuickAction = async (promptText: string, mode: typeof chatMode) => {
    setChatMode(mode);
    setMentorQuery(promptText);
    setTimeout(() => {
      handleSendChat();
    }, 100);
  };

  // Study plan generator
  const handleGeneratePlan = async () => {
    setGeneratingPlan(true);
    try {
      const newPlan = await apiService.generateAIMentorStudyPlan(selectedDuration, `${selectedDuration} Learning Blueprint`);
      setStudyPlans([newPlan, ...studyPlans]);
      setSelectedPlan(newPlan);
      setShowPlanModal(false);
      
      // Refresh list periodically in case of background updates
      setTimeout(async () => {
        const plans = await apiService.getAIMentorStudyPlans();
        setStudyPlans(plans);
        const updatedPlan = plans.find((p: any) => p.id === newPlan.id);
        if (updatedPlan) {
          setSelectedPlan(updatedPlan);
        }
      }, 5000);
    } catch (err) {
      console.error("Error generating study plan:", err);
    } finally {
      setGeneratingPlan(false);
    }
  };

  // STT (Voice Input)
  const startListening = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Voice input is not supported in this browser. Please try Google Chrome.");
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
        setMentorQuery((prev) => prev + (prev.endsWith(" ") || prev === "" ? "" : " ") + finalTranscript);
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

  // Basic markdown parser
  const renderMarkdown = (text: string) => {
    if (!text) return null;
    const lines = text.split("\n");
    return lines.map((line, idx) => {
      let content = line.trim();
      if (content.startsWith("### ")) {
        return <h4 key={idx} className="text-sm font-extrabold text-slate-800 dark:text-foreground mt-3 mb-1">{content.replace("### ", "")}</h4>;
      }
      if (content.startsWith("## ")) {
        return <h3 key={idx} className="text-base font-black text-slate-900 dark:text-foreground mt-4 mb-2">{content.replace("## ", "")}</h3>;
      }
      if (content.startsWith("# ")) {
        return <h2 key={idx} className="text-lg font-black text-slate-900 dark:text-foreground mt-5 mb-3 border-b border-border pb-1">{content.replace("# ", "")}</h2>;
      }
      if (content.startsWith("- ") || content.startsWith("* ")) {
        return (
          <div key={idx} className="flex items-start gap-2 ml-4 my-1">
            <span className="text-primary mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
            <span className="text-xs text-muted-foreground font-semibold leading-relaxed">{formatBold(content.substring(2))}</span>
          </div>
        );
      }
      const matchOrdered = content.match(/^(\d+)\.\s(.*)/);
      if (matchOrdered) {
        return (
          <div key={idx} className="flex items-start gap-2 ml-4 my-1">
            <span className="text-xs font-black text-blue-500 mt-0.5">{matchOrdered[1]}.</span>
            <span className="text-xs text-muted-foreground font-semibold leading-relaxed">{formatBold(matchOrdered[2])}</span>
          </div>
        );
      }
      if (content === "") {
        return <div key={idx} className="h-2" />;
      }
      return <p key={idx} className="text-xs text-muted-foreground font-semibold leading-relaxed my-1">{formatBold(content)}</p>;
    });
  };

  const formatBold = (text: string) => {
    const parts = text.split(/\*\*([^*]+)\*\*/g);
    return parts.map((part, i) => {
      if (i % 2 === 1) {
        return <strong key={i} className="font-extrabold text-slate-950 dark:text-foreground">{part}</strong>;
      }
      return part;
    });
  };

  return (
    <div className="bg-transparent border-none p-0 shadow-none flex flex-col gap-4 w-full h-full min-h-0 overflow-hidden relative">
      
      {/* Top Section with Status bar & Tab Buttons */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3 shrink-0 border-b border-border pb-3">
        <div>
          <h2 className="text-lg font-black text-slate-900 dark:text-foreground flex items-center gap-2">
            <GraduationCap className="text-blue-500 w-6 h-6" />
            <span>AI Mentor & Learning Coach</span>
          </h2>
          <p className="text-xs text-muted-foreground font-semibold mt-0.5">
            Your personalized learning copilot inside the Skill Lab workspace.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-100 dark:bg-[#1f2937]/50 rounded-2xl border border-border">
          {[
            { id: "dashboard", label: "Insights Dashboard" },
            { id: "chat", label: "Mentor Chat" },
            { id: "study-plans", label: "Study Plans" },
            { id: "artifacts", label: "Saved Artifacts" }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                activeTab === tab.id
                  ? "bg-white dark:bg-card text-blue-600 dark:text-blue-400 shadow-sm border border-border"
                  : "text-muted-foreground hover:text-foreground hover:bg-slate-50 dark:hover:bg-[#374151]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main content display based on activeTab */}
      <div className="flex-1 overflow-hidden min-h-0 w-full">
        
        {/* 1. INSIGHTS DASHBOARD */}
        {activeTab === "dashboard" && (
          <div className="h-full overflow-y-auto space-y-5 pr-1.5 scrollbar-thin">
            {loadingProfile ? (
              <div className="flex flex-col items-center justify-center h-64 gap-3">
                <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                <span className="text-xs text-muted-foreground font-bold">Assembling your Learning Insights...</span>
              </div>
            ) : (
              <>
                {/* Metrics Row */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Learning Health Score */}
                  <div className="p-4 bg-card border border-border rounded-3xl flex flex-col justify-between shadow-sm relative overflow-hidden group">
                    <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/5 dark:bg-blue-500/10 rounded-full blur-2xl group-hover:scale-125 transition-transform" />
                    <div>
                      <span className="text-10 font-bold uppercase tracking-wider text-muted-foreground block">Learning Health</span>
                      <div className="flex items-center gap-4 mt-3">
                        {/* Circular ring */}
                        <div className="relative flex items-center justify-center shrink-0">
                          <svg className="w-16 h-16 transform -rotate-90">
                            <circle cx="32" cy="32" r="28" className="stroke-slate-100 dark:stroke-[#374151]" strokeWidth="6" fill="transparent" />
                            <circle cx="32" cy="32" r="28" className="stroke-blue-500 transition-all duration-1000 ease-out" strokeWidth="6" fill="transparent" 
                              strokeDasharray={2 * Math.PI * 28} 
                              strokeDashoffset={2 * Math.PI * 28 * (1 - (profileStats?.health_score || 0) / 100)} 
                              strokeLinecap="round"
                            />
                          </svg>
                          <span className="absolute text-sm font-black text-slate-800 dark:text-foreground">{Math.round(profileStats?.health_score || 0)}</span>
                        </div>
                        <div>
                          <span className="text-sm font-black text-slate-900 dark:text-foreground block">{profileStats?.health_status}</span>
                          <span className="text-10 text-muted-foreground font-bold block mt-0.5">Based on progress, streak & assessments</span>
                        </div>
                      </div>
                    </div>
                    {riskAnalysis && (
                      <div className="mt-4 pt-3 border-t border-border flex items-center gap-2">
                        <AlertTriangle className={`w-4 h-4 shrink-0 ${
                          riskAnalysis.risk_level === "High" ? "text-red-500 animate-pulse" : riskAnalysis.risk_level === "Medium" ? "text-yellow-500" : "text-emerald-500"
                        }`} />
                        <span className="text-10 font-bold text-slate-700 dark:text-foreground truncate">{riskAnalysis.reason}</span>
                      </div>
                    )}
                  </div>

                  {/* Strengths & Weaknesses Card */}
                  <div className="p-4 bg-card border border-border rounded-3xl shadow-sm flex flex-col justify-between md:col-span-2">
                    <div>
                      <span className="text-10 font-bold uppercase tracking-wider text-muted-foreground block">Skill Breakdown</span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-3">
                        {/* Strengths */}
                        <div className="space-y-2">
                          <span className="text-10 font-black text-emerald-500 flex items-center gap-1">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Strengths
                          </span>
                          <div className="space-y-1.5">
                            {profileStats?.strengths.map((str, i) => (
                              <div key={i} className="px-2.5 py-1.5 bg-emerald-500/5 dark:bg-emerald-500/10 border border-emerald-500/10 rounded-xl text-11 font-bold text-emerald-600 dark:text-emerald-400">
                                {str}
                              </div>
                            ))}
                          </div>
                        </div>
                        {/* Weaknesses */}
                        <div className="space-y-2">
                          <span className="text-10 font-black text-red-500 flex items-center gap-1">
                            <AlertTriangle className="w-3.5 h-3.5" /> Needs Focus
                          </span>
                          <div className="space-y-1.5">
                            {profileStats?.weaknesses.map((weak, i) => (
                              <div key={i} className="px-2.5 py-1.5 bg-red-500/5 dark:bg-red-500/10 border border-red-500/10 rounded-xl text-11 font-bold text-red-600 dark:text-red-400">
                                {weak}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Dashboard Recommendations & Stats */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {/* Recommended Action Card */}
                  <div className="p-5 bg-blue-500/5 dark:bg-blue-500/10 border border-blue-500/20 rounded-3xl shadow-sm relative overflow-hidden flex flex-col justify-between group">
                    <div className="absolute top-0 right-0 w-28 h-28 bg-blue-500/10 dark:bg-blue-500/20 rounded-full blur-2xl" />
                    <div>
                      <div className="flex justify-between items-center">
                        <span className="text-10 font-black text-blue-600 dark:text-blue-400 uppercase tracking-wider flex items-center gap-1">
                          <Sparkles className="w-3.5 h-3.5" /> Recommended Next Action
                        </span>
                        <span className="px-2 py-0.5 bg-blue-500/15 text-9 font-bold text-blue-600 dark:text-blue-400 rounded-full">
                          Est: {profileStats?.estimated_time}
                        </span>
                      </div>
                      <div className="space-y-2.5 mt-4">
                        {profileStats?.next_best_actions.map((act, i) => (
                          <div key={i} className="flex items-start gap-2.5">
                            <span className="text-xs font-black text-blue-500 bg-blue-500/10 w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
                            <span className="text-xs text-slate-800 dark:text-foreground font-semibold leading-relaxed">{act}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <button
                      onClick={() => setActiveTab("chat")}
                      className="mt-5 w-full py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-sm"
                    >
                      <span>Get Mentor Guidance</span>
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>

                  {/* Level & Streak Stats Grid */}
                  <div className="grid grid-cols-2 gap-4 md:col-span-2">
                    <div className="p-4 bg-card border border-border rounded-3xl shadow-sm flex flex-col justify-between">
                      <span className="text-10 font-bold uppercase tracking-wider text-muted-foreground">XP & Level</span>
                      <div className="mt-2">
                        <div className="flex items-baseline gap-1.5">
                          <span className="text-2xl font-black text-slate-800 dark:text-foreground">{profileStats?.xp}</span>
                          <span className="text-10 text-muted-foreground font-bold">total XP</span>
                        </div>
                        <div className="flex items-center gap-2 mt-2">
                          <Award className="w-4 h-4 text-yellow-500" />
                          <span className="text-xs text-slate-700 dark:text-foreground font-extrabold">Level {profileStats?.level}</span>
                        </div>
                      </div>
                      <div className="mt-3 bg-slate-100 dark:bg-[#374151] h-1.5 rounded-full overflow-hidden">
                        <div className="bg-yellow-500 h-full rounded-full transition-all" style={{ width: `${(profileStats?.xp || 0) % 100}%` }} />
                      </div>
                    </div>

                    <div className="p-4 bg-card border border-border rounded-3xl shadow-sm flex flex-col justify-between">
                      <span className="text-10 font-bold uppercase tracking-wider text-muted-foreground">Study Streak</span>
                      <div className="mt-2">
                        <div className="flex items-baseline gap-1.5">
                          <span className="text-2xl font-black text-slate-800 dark:text-foreground">{profileStats?.streak}</span>
                          <span className="text-10 text-muted-foreground font-bold">days active</span>
                        </div>
                        <div className="flex items-center gap-2 mt-2">
                          <Flame className="w-4 h-4 text-orange-500" />
                          <span className="text-xs text-slate-700 dark:text-foreground font-extrabold">Keep the fire burning!</span>
                        </div>
                      </div>
                    </div>

                    <div className="p-4 bg-card border border-border rounded-3xl shadow-sm flex flex-col justify-between">
                      <span className="text-10 font-bold uppercase tracking-wider text-muted-foreground">Completed Lessons</span>
                      <div className="mt-2 flex items-baseline gap-1.5">
                        <span className="text-2xl font-black text-slate-800 dark:text-foreground">{profileStats?.completed_lessons_count}</span>
                        <span className="text-10 text-muted-foreground font-bold">lessons finished</span>
                      </div>
                    </div>

                    <div className="p-4 bg-card border border-border rounded-3xl shadow-sm flex flex-col justify-between">
                      <span className="text-10 font-bold uppercase tracking-wider text-muted-foreground">Avg Quiz Score</span>
                      <div className="mt-2 flex items-baseline gap-1.5">
                        <span className="text-2xl font-black text-slate-800 dark:text-foreground">{Math.round(profileStats?.avg_quiz_score || 0)}%</span>
                        <span className="text-10 text-muted-foreground font-bold">on attempts</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Insights Row */}
                <div className="p-5 bg-card border border-border rounded-3xl shadow-sm space-y-4">
                  <h3 className="text-xs font-black uppercase tracking-wider text-slate-800 dark:text-foreground flex items-center gap-2">
                    <BookOpenCheck className="w-4 h-4 text-blue-500" />
                    <span>AI Mentor Insights & Achievements</span>
                  </h3>
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
                        No custom learning insights generated yet. Complete quizzes and lessons to trigger personalized updates!
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* 2. MENTOR CHAT VIEW */}
        {activeTab === "chat" && (
          <div className="h-full flex overflow-hidden border border-border rounded-3xl bg-card relative min-h-0">
            {/* Sidebar toggle button (mobile) */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="absolute md:hidden top-3.5 left-4 z-20 p-1 bg-slate-100 hover:bg-slate-200 dark:bg-muted dark:hover:bg-[#374151] text-muted-foreground hover:text-foreground rounded-lg transition-colors cursor-pointer"
            >
              <List size={16} />
            </button>

            {/* Sidebar Pane */}
            <div className={`absolute md:static top-0 left-0 h-full w-64 bg-slate-50 dark:bg-black/40 border-r border-border shrink-0 z-10 flex flex-col transition-transform duration-300 md:translate-x-0 ${
              sidebarOpen ? "translate-x-0" : "-translate-x-full"
            }`}>
              {/* Header */}
              <div className="p-4 border-b border-border flex justify-between items-center shrink-0">
                <span className="text-xs font-black text-foreground uppercase tracking-wider">Conversations</span>
                <button
                  onClick={handleCreateSession}
                  className="p-1 bg-white hover:bg-slate-50 dark:bg-card dark:hover:bg-muted border border-border text-blue-500 rounded-lg cursor-pointer transition-colors"
                  title="New Session"
                >
                  <Plus size={16} />
                </button>
              </div>

              {/* Mode Selector */}
              <div className="p-3 border-b border-border shrink-0">
                <label className="text-9 font-bold uppercase tracking-wider text-muted-foreground block mb-1">Mentor Mode</label>
                <select
                  value={chatMode}
                  onChange={(e) => setChatMode(e.target.value as any)}
                  className="w-full bg-white dark:bg-card border border-border rounded-xl p-2 text-xs text-foreground font-semibold focus:outline-none focus:border-blue-500 cursor-pointer"
                >
                  <option value="tutor">Concept Explanations</option>
                  <option value="quiz">Interactive MCQ Quiz</option>
                  <option value="challenge">Coding Challenge</option>
                  <option value="revision">Weak Topic Revision</option>
                  <option value="interview">Mock Interview</option>
                </select>
              </div>

              {/* Sessions list */}
              <div className="flex-1 overflow-y-auto p-2 space-y-1 scrollbar-thin">
                {chatSessions.map((s) => (
                  <div
                    key={s.id}
                    onClick={() => {
                      handleSelectSession(s.id);
                      setSidebarOpen(false);
                    }}
                    className={`group p-2.5 rounded-xl flex items-center justify-between cursor-pointer transition-all ${
                      currentSessionId === s.id
                        ? "bg-blue-500/10 border border-blue-500/20 text-blue-600 dark:text-blue-400"
                        : "hover:bg-slate-100 dark:hover:bg-muted/30 text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate pr-2">
                      <GraduationCap className="w-4 h-4 shrink-0" />
                      <span className="text-xs font-bold truncate">{s.title}</span>
                    </div>
                    <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
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
              </div>
            </div>

            {/* Chat Messages Area */}
            <div className="flex-1 flex flex-col h-full overflow-hidden min-h-0 relative">
              {/* Thread */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin md:pt-4 pt-14">
                {chatMessages.length === 0 ? (
                  <div className="flex-1 flex flex-col items-center justify-center max-w-md mx-auto text-center h-full gap-3 py-10">
                    <GraduationCap className="w-12 h-12 text-blue-500 bg-blue-500/5 p-2.5 rounded-2xl" />
                    <div>
                      <h3 className="text-sm font-black text-slate-800 dark:text-foreground">Ask VidyamargAI Mentor</h3>
                      <p className="text-xs text-muted-foreground font-bold mt-1">
                        Select a mode on the sidebar to get tailored explanations, mcq quizzes, code challenges, or mock interviews.
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
                      <span className="text-[9px] font-black uppercase tracking-wider text-muted-foreground">
                        {msg.sender === "user" ? "You" : "Skill Lab Mentor"}
                      </span>
                      <div
                        className={`p-3.5 rounded-2xl text-xs leading-relaxed border shadow-sm ${
                          msg.sender === "user"
                            ? "bg-blue-50 dark:bg-blue-950/20 text-slate-900 dark:text-foreground border-blue-100 dark:border-blue-900/30 rounded-tr-sm"
                            : "bg-white dark:bg-[#1f2937]/50 border-border text-foreground dark:text-foreground rounded-tl-sm"
                        }`}
                      >
                        {renderMarkdown(msg.message)}
                      </div>
                    </div>
                  ))
                )}
                {chatLoading && (
                  <div className="flex flex-col gap-1.5 max-w-xs self-start items-start">
                    <span className="text-[9px] font-black uppercase tracking-wider text-muted-foreground">Skill Lab Mentor</span>
                    <div className="p-3.5 bg-white dark:bg-[#1f2937]/50 border border-border text-foreground dark:text-foreground rounded-2xl rounded-tl-sm flex items-center gap-2 shadow-sm">
                      <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                      <span className="text-10 font-bold text-muted-foreground">Typing response...</span>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Suggestions Toolbar */}
              <div className="px-4 py-2 border-t border-border bg-slate-50/50 dark:bg-black/10 flex items-center gap-2 overflow-x-auto scrollbar-none shrink-0">
                <span className="text-10 font-black text-blue-500 uppercase tracking-wider shrink-0">Quick Action:</span>
                {[
                  { label: "Create Quiz", prompt: "Create a 3-question MCQ quiz on Python Functions.", mode: "quiz" as const },
                  { label: "Coding Challenge", prompt: "Give me a coding challenge to write a function that finds unique values in a list.", mode: "challenge" as const },
                  { label: "Summarize OOP", prompt: "Explain OOP concepts simply in 2 paragraphs.", mode: "tutor" as const },
                  { label: "Interview Questions", prompt: "Ask me a viva question on database normalization.", mode: "interview" as const }
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

              {/* Input Area */}
              <div className="p-4 border-t border-border bg-white dark:bg-card shrink-0 flex items-end gap-2">
                <div className="flex-1 bg-slate-50 dark:bg-black/30 border border-border focus-within:border-blue-500/50 rounded-2xl p-1.5 flex items-end">
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
                    placeholder="Ask AI Mentor for explanations, quizes or challenge code..."
                    className="w-full bg-transparent resize-none border-none outline-none focus:ring-0 text-xs text-foreground placeholder-muted-foreground px-2 py-1 max-h-36 overflow-y-auto"
                  />
                  
                  {/* Microphone */}
                  <button
                    onClick={startListening}
                    className={`p-2 rounded-xl transition-all shrink-0 ${
                      isListening ? "bg-red-500 text-white animate-pulse" : "text-muted-foreground hover:text-foreground hover:bg-slate-100 dark:hover:bg-muted"
                    }`}
                  >
                    <Mic size={15} />
                  </button>
                </div>

                <button
                  onClick={handleSendChat}
                  disabled={!mentorQuery.trim() || chatLoading}
                  className={`p-3 bg-blue-500 hover:bg-blue-600 disabled:bg-slate-100 disabled:text-slate-400 dark:disabled:bg-background text-white rounded-2xl shrink-0 cursor-pointer shadow-sm transition-all`}
                >
                  <ArrowUp size={16} />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 3. STUDY PLANS TAB */}
        {activeTab === "study-plans" && (
          <div className="h-full flex flex-col md:flex-row overflow-hidden border border-border rounded-3xl bg-card min-h-0">
            {/* Sidebar list of generated plans */}
            <div className="w-full md:w-80 bg-slate-50 dark:bg-black/40 border-r border-border flex flex-col h-full shrink-0 min-h-0">
              <div className="p-4 border-b border-border flex justify-between items-center shrink-0">
                <div>
                  <span className="text-xs font-black text-foreground uppercase tracking-wider block">Study Blueprints</span>
                  <span className="text-[10px] text-muted-foreground font-bold block mt-0.5">Custom learning pathways</span>
                </div>
                <button
                  onClick={() => setShowPlanModal(true)}
                  className="px-2.5 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-xl text-[10px] font-bold cursor-pointer transition-colors shadow-sm flex items-center gap-1 shrink-0"
                >
                  <Sparkles size={11} />
                  <span>Generate</span>
                </button>
              </div>

              {/* Plans List */}
              <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
                {studyPlans.map((plan) => (
                  <div
                    key={plan.id}
                    onClick={() => setSelectedPlan(plan)}
                    className={`p-3 rounded-2xl border cursor-pointer transition-all flex flex-col gap-1.5 relative group ${
                      selectedPlan?.id === plan.id
                        ? "bg-white dark:bg-card border-blue-500/35 dark:border-blue-500 shadow-sm"
                        : "bg-white/50 dark:bg-card/40 border-border hover:border-blue-500/20"
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <span className="text-xs font-bold text-slate-800 dark:text-foreground line-clamp-1 flex-1 pr-2">{plan.title}</span>
                      <span className="px-1.5 py-0.5 bg-slate-100 dark:bg-muted border border-border rounded-md text-[9px] font-bold text-muted-foreground shrink-0">{plan.duration}</span>
                    </div>
                    <span className="text-[9px] text-muted-foreground font-bold">Generated: {new Date(plan.created_at).toLocaleDateString()}</span>
                  </div>
                ))}
                {studyPlans.length === 0 && (
                  <div className="text-center py-8 text-xs text-muted-foreground font-bold">
                    No custom study blueprints generated. Click "Generate" to construct one based on your weak areas!
                  </div>
                )}
              </div>
            </div>

            {/* Display plan details */}
            <div className="flex-1 flex flex-col h-full overflow-hidden min-h-0 bg-white dark:bg-card/20">
              {selectedPlan ? (
                <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin">
                  <div className="flex justify-between items-start border-b border-border pb-4">
                    <div>
                      <h3 className="text-sm font-black text-slate-900 dark:text-foreground">{selectedPlan.title}</h3>
                      <span className="text-[10px] text-muted-foreground font-bold mt-1 block">Created on {new Date(selectedPlan.created_at).toLocaleString()}</span>
                    </div>
                    <span className="px-2.5 py-1 bg-blue-500/10 border border-blue-500/20 text-[10px] font-black text-blue-500 rounded-lg uppercase tracking-wider shrink-0">{selectedPlan.duration}</span>
                  </div>
                  <div className="prose dark:prose-invert max-w-none prose-sm">
                    {selectedPlan.content.includes("currently being generated") ? (
                      <div className="flex items-center gap-3 p-4 bg-blue-500/5 border border-blue-500/10 rounded-2xl text-xs text-blue-500 font-bold">
                        <Loader2 className="w-4 h-4 animate-spin shrink-0" />
                        <span>AI Mentor is constructing your plan in the background. Please wait or click refresh in a few seconds...</span>
                        <button
                          onClick={fetchStudyPlans}
                          className="ml-auto p-1 bg-white hover:bg-slate-50 dark:bg-card dark:hover:bg-muted border border-border text-blue-500 rounded-lg flex items-center gap-1 cursor-pointer font-bold text-9"
                        >
                          <RefreshCw size={10} />
                          <span>Refresh</span>
                        </button>
                      </div>
                    ) : (
                      renderMarkdown(selectedPlan.content)
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-6 h-full gap-2">
                  <BookOpen className="w-10 h-10 text-muted-foreground bg-slate-100 dark:bg-card p-2 rounded-xl" />
                  <h4 className="text-xs font-bold text-slate-700 dark:text-foreground">No Plan Selected</h4>
                  <p className="text-[11px] text-muted-foreground font-bold">Select a learning blueprint on the left side, or create a new one.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 4. SAVED ARTIFACTS TAB */}
        {activeTab === "artifacts" && (
          <div className="h-full flex flex-col md:flex-row overflow-hidden border border-border rounded-3xl bg-card min-h-0">
            {/* Sidebar list of artifacts */}
            <div className="w-full md:w-80 bg-slate-50 dark:bg-black/40 border-r border-border flex flex-col h-full shrink-0 min-h-0">
              <div className="p-4 border-b border-border shrink-0">
                <span className="text-xs font-black text-foreground uppercase tracking-wider block">Persistent AI Artifacts</span>
                <span className="text-[10px] text-muted-foreground font-bold block mt-0.5">Saved quizzes, challenges, revision notes</span>
              </div>

              {/* Artifacts List */}
              <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
                {artifacts.map((art) => (
                  <div
                    key={art.id}
                    onClick={() => setSelectedArtifact(art)}
                    className={`p-3 rounded-2xl border cursor-pointer transition-all flex flex-col gap-1.5 relative group ${
                      selectedArtifact?.id === art.id
                        ? "bg-white dark:bg-card border-blue-500/35 dark:border-blue-500 shadow-sm"
                        : "bg-white/50 dark:bg-card/40 border-border hover:border-blue-500/20"
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <span className="text-xs font-bold text-slate-800 dark:text-foreground line-clamp-1 flex-1 pr-2">{art.title}</span>
                      <span className="px-1.5 py-0.5 bg-blue-500/10 border border-blue-500/20 rounded-md text-[9px] font-black text-blue-500 shrink-0">v{art.version}</span>
                    </div>
                    <div className="flex justify-between items-center text-[9px] text-muted-foreground font-bold">
                      <span className="capitalize">{art.artifact_type}</span>
                      <span>{new Date(art.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))}
                {artifacts.length === 0 && (
                  <div className="text-center py-8 text-xs text-muted-foreground font-bold">
                    No persistent artifacts found. Interact with the chat in quiz, challenge, or revision modes to auto-generate and store study guides!
                  </div>
                )}
              </div>
            </div>

            {/* Display artifact details */}
            <div className="flex-1 flex flex-col h-full overflow-hidden min-h-0 bg-white dark:bg-card/20">
              {selectedArtifact ? (
                <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin">
                  <div className="flex justify-between items-start border-b border-border pb-4">
                    <div>
                      <h3 className="text-sm font-black text-slate-900 dark:text-foreground">{selectedArtifact.title}</h3>
                      <span className="text-[10px] text-muted-foreground font-bold mt-1 block">Version {selectedArtifact.version} • Created on {new Date(selectedArtifact.created_at).toLocaleString()}</span>
                    </div>
                    <span className="px-2.5 py-1 bg-slate-100 dark:bg-muted border border-border text-[10px] font-black text-slate-700 dark:text-foreground rounded-lg uppercase tracking-wider shrink-0">{selectedArtifact.artifact_type}</span>
                  </div>
                  <div className="prose dark:prose-invert max-w-none prose-sm">
                    {renderMarkdown(selectedArtifact.content)}
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-6 h-full gap-2">
                  <FileText className="w-10 h-10 text-muted-foreground bg-slate-100 dark:bg-card p-2 rounded-xl" />
                  <h4 className="text-xs font-bold text-slate-700 dark:text-foreground">No Artifact Selected</h4>
                  <p className="text-[11px] text-muted-foreground font-bold">Select a saved study guide or quiz on the left side to review details.</p>
                </div>
              )}
            </div>
          </div>
        )}

      </div>

      {/* Study Plan Generation Modal */}
      {showPlanModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-background border border-border rounded-3xl p-6 w-full max-w-sm shadow-2xl flex flex-col gap-4">
            <div className="flex justify-between items-center border-b border-border pb-3 shrink-0">
              <h3 className="text-xs font-black uppercase tracking-wider text-slate-800 dark:text-foreground flex items-center gap-1.5">
                <Sparkles size={15} className="text-blue-500" />
                <span>Configure Study Plan</span>
              </h3>
              <button
                onClick={() => setShowPlanModal(false)}
                className="text-slate-400 hover:text-slate-655 dark:text-muted-foreground dark:hover:text-foreground p-1 hover:bg-slate-50 dark:hover:bg-muted rounded-xl cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            <div className="space-y-4 py-2 shrink-0">
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-black uppercase tracking-wider text-muted-foreground">Select Duration</label>
                <div className="grid grid-cols-3 gap-2">
                  {["7-day", "30-day", "90-day"].map((dur) => (
                    <button
                      key={dur}
                      onClick={() => setSelectedDuration(dur)}
                      className={`py-2 rounded-xl text-xs font-bold border transition-all cursor-pointer ${
                        selectedDuration === dur
                          ? "bg-blue-500/10 border-blue-500 text-blue-600 dark:text-blue-400"
                          : "bg-slate-50 dark:bg-card border-border text-slate-700 dark:text-foreground"
                      }`}
                    >
                      {dur}
                    </button>
                  ))}
                </div>
              </div>
              <p className="text-[11px] text-muted-foreground font-semibold leading-relaxed">
                The AI Mentor automatically scans your enrollments, quiz performance, and weak concepts to create a customized study path.
              </p>
            </div>

            <button
              onClick={handleGeneratePlan}
              disabled={generatingPlan}
              className="w-full py-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-slate-100 disabled:text-slate-400 dark:disabled:bg-background text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-md shrink-0"
            >
              {generatingPlan ? (
                <>
                  <Loader2 size={13} className="animate-spin" />
                  <span>Enqueuing Job...</span>
                </>
              ) : (
                <>
                  <Sparkles size={13} fill="white" />
                  <span>Generate Blueprint</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
