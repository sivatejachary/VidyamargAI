"use client";

import { useEffect, useState, useCallback } from "react";
import { apiService } from "@/services/api";
import {
  MapPin, Search, X, Briefcase, Bookmark, BookmarkCheck,
  ArrowUpRight, RefreshCw, Zap, Building2,
  Clock, Target, AlertCircle, Laptop, Sparkles, CheckCircle2,
  ArrowRight, ShieldCheck, HelpCircle, ChevronLeft, ChevronRight,
  TrendingUp
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Alert } from "@/components/ui/Alert";

// Import custom Job Agent subcomponents
import AgentConsole from "@/components/AgentConsole";
import RecommendedLearning from "@/components/RecommendedLearning";

// ─────────────────────── Types ───────────────────────
interface LiveJob {
  id: string;
  title: string;
  company: string;
  location: string;
  experience: string;
  work_mode: string;
  skills: string[];
  apply_url: string;
  posted_date: string;
  source: string;
  description: string;
  match_score: number;
  opportunity_score?: number;
  matched_skills?: string[];
  missing_skills?: string[];
  skills_gap?: string;
  reasoning: string;
  company_logo?: string;
  is_saved?: boolean;
  verification_score?: number;
  verification_status?: string;
}

interface SkillGap {
  skill: string;
  missing_in_percentage: number;
  priority: "High" | "Medium" | "Low";
  count: number;
}

interface Recommendations {
  skills: string[];
  certifications: string[];
  projects: string[];
  roadmap: string[];
}

function getSourceBadgeStyles(source: string) {
  const lower = source.toLowerCase();
  if (lower.startsWith("telegram")) {
    return "bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 border-indigo-150 dark:border-indigo-800/30";
  }
  if (lower.includes("linkedin")) return "bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border-blue-150 dark:border-blue-800/30";
  if (lower.includes("naukri")) return "bg-orange-50 dark:bg-orange-950/40 text-orange-700 dark:text-orange-300 border-orange-150 dark:border-orange-850/30";
  if (lower.includes("foundit")) return "bg-green-50 dark:bg-green-950/40 text-green-700 dark:text-green-300 border-green-150 dark:border-green-800/30";
  if (lower.includes("internshala")) return "bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border-purple-150 dark:border-purple-800/30";
  if (lower.includes("wellfound")) return "bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border-rose-150 dark:border-rose-800/30";
  if (lower.includes("cutshort")) return "bg-teal-50 dark:bg-teal-950/40 text-teal-700 dark:text-teal-300 border-teal-150 dark:border-teal-800/30";
  if (lower.includes("instahyre")) return "bg-cyan-50 dark:bg-cyan-950/40 text-cyan-700 dark:text-cyan-300 border-cyan-150 dark:border-cyan-800/30";
  if (lower.includes("hirist")) return "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-150 dark:border-amber-800/30";
  return "bg-slate-50 dark:bg-slate-900/40 text-slate-600 dark:text-slate-300 border-slate-150 dark:border-slate-800/30";
}

function getVerificationBadge(score: number, status: string) {
  if (status === "Fully Verified" || score >= 85) {
    return {
      dot: "bg-emerald-500",
      text: "Fully Verified",
      bg: "bg-emerald-50/70 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 border-emerald-150 dark:border-emerald-800/30"
    };
  }
  if (status === "Partially Verified" || score >= 50) {
    return {
      dot: "bg-amber-500",
      text: "Partially Verified",
      bg: "bg-amber-50/70 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 border-amber-150 dark:border-amber-800/30"
    };
  }
  return {
    dot: "bg-rose-500",
    text: "Rejected",
    bg: "bg-rose-50/70 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300 border-rose-150 dark:border-rose-800/30"
  };
}

function getMatchStyles(score: number) {
  if (score >= 80) return { bg: "bg-emerald-50 dark:bg-emerald-950/20", text: "text-emerald-700 dark:text-emerald-300", border: "border-emerald-150 dark:border-emerald-800/20", dot: "bg-emerald-500" };
  if (score >= 60) return { bg: "bg-amber-50 dark:bg-amber-950/20", text: "text-amber-700 dark:text-amber-300", border: "border-amber-150 dark:border-amber-800/20", dot: "bg-amber-500" };
  return { bg: "bg-rose-50 dark:bg-rose-950/20", text: "text-rose-700 dark:text-rose-300", border: "border-rose-150 dark:border-rose-800/20", dot: "bg-rose-500" };
}

function getOpportunityLabel(score: number): string {
  if (score >= 90) return "🔥 Top Opportunity";
  if (score >= 75) return "✅ Strong Match";
  if (score >= 60) return "⚡ Good Fit";
  if (score >= 45) return "🤔 Partial Match";
  return "⚠ Low Priority";
}

function getOpportunityBadgeStyles(score: number) {
  if (score >= 90) return "from-amber-500 to-orange-500 text-white shadow-amber-100";
  if (score >= 75) return "from-emerald-500 to-teal-500 text-white shadow-emerald-100";
  if (score >= 60) return "from-blue-500 to-indigo-500 text-white shadow-blue-100";
  return "from-slate-500 to-slate-600 text-white shadow-slate-100";
}

export default function CandidateJobs() {
  // Session storage caching helpers for instant (0ms) loads
  const getCachedValue = (key: string, fallback: any) => {
    if (typeof window !== "undefined") {
      const cached = sessionStorage.getItem(key);
      if (cached) {
        try { return JSON.parse(cached); } catch { return fallback; }
      }
    }
    return fallback;
  };

  const setCachedValue = (key: string, val: any) => {
    if (typeof window !== "undefined") {
      sessionStorage.setItem(key, JSON.stringify(val));
    }
  };

  const [activeTab, setActiveTab] = useState<"ai_search" | "job_pool" | "saved">("ai_search");

  // AI Search states
  const [jobs, setJobs] = useState<LiveJob[]>(() => getCachedValue("jobs_list", []));
  const [skillGaps, setSkillGaps] = useState<SkillGap[]>(() => getCachedValue("jobs_skill_gaps", []));
  const [recommendations, setRecommendations] = useState<Recommendations | null>(() => getCachedValue("jobs_recommendations", null));
  const [runId, setRunId] = useState<number | null>(() => getCachedValue("jobs_run_id", null));
  const [agentStatus, setAgentStatus] = useState<string>(() => getCachedValue("jobs_agent_status", "idle"));
  const [logs, setLogs] = useState<any[]>(() => getCachedValue("jobs_agent_logs", []));

  // Job Pool states
  const [jobPool, setJobPool] = useState<LiveJob[]>([]);
  const [loadingJobPool, setLoadingJobPool] = useState(false);
  const [poolSearchQuery, setPoolSearchQuery] = useState("");
  const [poolSelectedSource, setPoolSelectedSource] = useState("All");
  const [poolSelectedWorkMode, setPoolSelectedWorkMode] = useState("All");
  const [poolMinScore, setPoolMinScore] = useState(0);

  // Saved Jobs states
  const [savedJobs, setSavedJobs] = useState<any[]>([]);
  const [loadingSavedJobs, setLoadingSavedJobs] = useState(false);

  // General States
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [savedJobIds, setSavedJobIds] = useState<Set<string>>(new Set());
  const [applyingIds, setApplyingIds] = useState<Set<string>>(new Set());

  // Search & Filter within Ranked Jobs (Tab 1)
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSource, setSelectedSource] = useState("All");
  const [showAllOpportunities, setShowAllOpportunities] = useState(false);

  // Pagination for remaining ranked jobs
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 3;

  // Selected job details modal
  const [selectedJob, setSelectedJob] = useState<LiveJob | null>(null);

  // Legal Consents & MCP Servers Health
  const [consents, setConsents] = useState<Record<string, { granted: boolean, consent_ref: string | null }>>({});
  const [mcpServers, setMcpServers] = useState<any[]>([]);

  const fetchConsentsAndServers = useCallback(async () => {
    try {
      const cData = await apiService.getUserConsents();
      setConsents(cData);
      const sData = await apiService.getMCPServers();
      setMcpServers(sData);
    } catch (e) {
      console.error("Failed to load consents/servers", e);
    }
  }, []);

  const handleConsentToggle = async (type: string) => {
    const isGranted = consents[type]?.granted || false;
    try {
      const res = await apiService.updateUserConsent(type, !isGranted);
      setConsents(prev => ({
        ...prev,
        [type]: { granted: res.granted, consent_ref: res.consent_ref }
      }));
    } catch (err) {
      console.error("Failed to update consent:", err);
    }
  };

  const fetchJobPool = useCallback(async () => {
    setLoadingJobPool(true);
    try {
      const data = await apiService.getJobPool();
      setJobPool(data);
    } catch (e) {
      console.error("Failed to fetch job pool", e);
    } finally {
      setLoadingJobPool(false);
    }
  }, []);

  const fetchSavedJobs = useCallback(async () => {
    setLoadingSavedJobs(true);
    try {
      const data = await apiService.getSavedJobs();
      if (Array.isArray(data)) {
        setSavedJobs(data);
        setSavedJobIds(new Set(data.map(sj => String(sj.job_id))));
      }
    } catch (e) {
      console.error("Failed to fetch saved jobs", e);
    } finally {
      setLoadingSavedJobs(false);
    }
  }, []);

  useEffect(() => {
    fetchConsentsAndServers();
  }, [fetchConsentsAndServers]);

  useEffect(() => {
    if (activeTab === "job_pool") {
      fetchJobPool();
    } else if (activeTab === "saved") {
      fetchSavedJobs();
    }
  }, [activeTab, fetchJobPool, fetchSavedJobs]);

  // Trigger a fresh agent run
  const triggerAgentRun = async () => {
    try {
      setLoading(true);
      setError("");
      setLogs([]);
      setAgentStatus("running");
      setCachedValue("jobs_agent_status", "running");
      setCachedValue("jobs_agent_logs", []);
      setCurrentPage(1);
      setShowAllOpportunities(false);

      const res = await apiService.startAgentRun();
      setRunId(res.run_id);
      setAgentStatus(res.status);
      setCachedValue("jobs_run_id", res.run_id);
      setCachedValue("jobs_agent_status", res.status);
    } catch (err: any) {
      console.error("Error starting agent run:", err);
      setError(err.message || "Failed to start autonomous job discovery.");
      setAgentStatus("failed");
      setCachedValue("jobs_agent_status", "failed");
    } finally {
      setLoading(false);
    }
  };

  // Callback on WebSocket completion
  const handleRunComplete = useCallback(async () => {
    setAgentStatus("completed");
    setCachedValue("jobs_agent_status", "completed");
    try {
      const result = await apiService.getAgentRunResult();
      setJobs(result.jobs || []);
      setSkillGaps(result.skill_gaps || []);
      setRecommendations(result.recommendations || null);
      
      setCachedValue("jobs_list", result.jobs || []);
      setCachedValue("jobs_skill_gaps", result.skill_gaps || []);
      setCachedValue("jobs_recommendations", result.recommendations || null);
    } catch (err: any) {
      setError("Failed to fetch job recommendations from cache.");
    }
  }, []);

  // Initialize and check status on mount
  useEffect(() => {
    const initializeAgent = async () => {
      try {
        setLoading(true);
        // Load user saved jobs to keep bookmark states accurate
        const saved = await apiService.getSavedJobs();
        if (Array.isArray(saved)) {
          setSavedJobs(saved);
          setSavedJobIds(new Set(saved.map(sj => String(sj.job_id))));
        }

        const runData = await apiService.getLatestAgentRun();
        if (runData && runData.run_id) {
          setRunId(runData.run_id);
          setAgentStatus(runData.status);
          setLogs(runData.logs || []);
          
          setCachedValue("jobs_run_id", runData.run_id);
          setCachedValue("jobs_agent_status", runData.status);
          setCachedValue("jobs_agent_logs", runData.logs || []);

          if (runData.status === "completed") {
            const result = await apiService.getAgentRunResult();
            setJobs(result.jobs || []);
            setSkillGaps(result.skill_gaps || []);
            setRecommendations(result.recommendations || null);
            
            setCachedValue("jobs_list", result.jobs || []);
            setCachedValue("jobs_skill_gaps", result.skill_gaps || []);
            setCachedValue("jobs_recommendations", result.recommendations || null);
          } else if (runData.status === "failed" || runData.status === "idle") {
            await triggerAgentRun();
          }
        } else {
          await triggerAgentRun();
        }
      } catch (err: any) {
        console.error("Error initializing jobs page:", err);
        setError("Failed to load candidate career agent state.");
      } finally {
        setLoading(false);
      }
    };

    initializeAgent();
  }, []);

  // Toggle saving a job
  const handleSaveJob = async (job: LiveJob) => {
    const isSaved = savedJobIds.has(job.id);
    const newSaved = new Set(savedJobIds);

    if (isSaved) {
      newSaved.delete(job.id);
      setSavedJobIds(newSaved);
      setSavedJobs(prev => prev.filter(sj => String(sj.job_id) !== String(job.id) && String(sj.job?.id) !== String(job.id)));
      try {
        await apiService.unsaveJob(job.id);
      } catch {
        newSaved.add(job.id);
        setSavedJobIds(new Set(newSaved));
        fetchSavedJobs();
      }
    } else {
      newSaved.add(job.id);
      setSavedJobIds(newSaved);
      try {
        const savedItem = await apiService.saveJob(job.id);
        setSavedJobs(prev => [...prev, savedItem]);
      } catch {
        newSaved.delete(job.id);
        setSavedJobIds(new Set(newSaved));
      }
    }
  };

  // Trigger auto apply
  const handleAutoApply = async (jobId: string) => {
    setApplyingIds(prev => new Set(prev).add(jobId));
    try {
      await apiService.autoApplyJob(jobId);
      alert("Auto-apply queued successfully! The agent is filling out details in the background.");
    } catch (e: any) {
      alert("Failed to queue auto-apply: " + e.message);
    } finally {
      setApplyingIds(prev => { const s = new Set(prev); s.delete(jobId); return s; });
    }
  };

  // Filter remaining jobs (excluding top 3 opportunities unless View All is active)
  const topOpportunities = showAllOpportunities ? jobs : jobs.slice(0, 3);
  const remainingJobs = showAllOpportunities ? [] : jobs.slice(3);

  const filteredRemainingJobs = remainingJobs.filter(job => {
    const matchesSearch = 
      job.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.location.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.skills.some(s => s.toLowerCase().includes(searchQuery.toLowerCase()));
    
    const matchesSource = selectedSource === "All" || job.source === selectedSource;
    return matchesSearch && matchesSource;
  });

  // Paginated remaining jobs
  const paginatedJobs = filteredRemainingJobs.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );
  const totalPages = Math.ceil(filteredRemainingJobs.length / pageSize);

  const uniqueSources = ["All", ...Array.from(new Set(jobs.map(j => j.source)))].sort();

  // Filters for Job Pool (Tab 2)
  const filteredJobPool = jobPool.filter(job => {
    const matchesSearch = 
      job.title.toLowerCase().includes(poolSearchQuery.toLowerCase()) ||
      job.company.toLowerCase().includes(poolSearchQuery.toLowerCase()) ||
      job.location.toLowerCase().includes(poolSearchQuery.toLowerCase()) ||
      job.skills.some(s => s.toLowerCase().includes(poolSearchQuery.toLowerCase()));
    
    const matchesSource = poolSelectedSource === "All" || job.source === poolSelectedSource;
    const matchesWorkMode = poolSelectedWorkMode === "All" || job.work_mode === poolSelectedWorkMode;
    const matchesScore = (job.opportunity_score || 0) >= poolMinScore;

    return matchesSearch && matchesSource && matchesWorkMode && matchesScore;
  });

  const poolSources = ["All", ...Array.from(new Set(jobPool.map(j => j.source)))].sort();
  const poolWorkModes = ["All", ...Array.from(new Set(jobPool.map(j => j.work_mode)))].sort();

  return (
    <div className="min-h-screen bg-background text-foreground pb-20">
      {/* Header */}
      <div className="bg-card border-b border-border py-6 sticky top-0 z-20 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-100">
              <Sparkles className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
                Autonomous Recruiter Agent
              </h1>
              <p className="text-xs text-muted-foreground font-medium">
                AI Agent active · Continuously searching, verifying, and matching live jobs
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              onClick={triggerAgentRun}
              loading={agentStatus === "running"}
            >
              <RefreshCw className={`w-4 h-4 ${agentStatus === "running" ? "animate-spin" : ""}`} />
              <span>Re-Run Job Agent</span>
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {error && (
          <Alert variant="error">
            {error}
          </Alert>
        )}

        {/* Tab selection buttons */}
        <div className="flex space-x-1 bg-slate-100 dark:bg-slate-900 p-1.5 rounded-2xl w-max border border-slate-200/50 dark:border-slate-800/40">
          <button
            onClick={() => setActiveTab("ai_search")}
            className={`px-4 py-2.5 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer ${
              activeTab === "ai_search"
                ? "bg-white dark:bg-slate-800 text-foreground shadow-xs border border-slate-200/30 dark:border-slate-700/30"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            AI Search Agent
          </button>
          <button
            onClick={() => setActiveTab("job_pool")}
            className={`px-4 py-2.5 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer ${
              activeTab === "job_pool"
                ? "bg-white dark:bg-slate-800 text-foreground shadow-xs border border-slate-200/30 dark:border-slate-700/30"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Briefcase className="w-3.5 h-3.5" />
            Job Pool (Pre-collected)
          </button>
          <button
            onClick={() => setActiveTab("saved")}
            className={`px-4 py-2.5 rounded-xl text-xs font-bold transition flex items-center gap-2 cursor-pointer ${
              activeTab === "saved"
                ? "bg-white dark:bg-slate-800 text-foreground shadow-xs border border-slate-200/30 dark:border-slate-700/30"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Bookmark className="w-3.5 h-3.5" />
            Saved Jobs ({savedJobIds.size})
          </button>
        </div>

        {/* TAB 1: AI SEARCH */}
        {activeTab === "ai_search" && (
          <>
            {/* Section 1: AI Agent Console */}
            <div className="grid grid-cols-1">
              <AgentConsole
                runId={runId}
                status={agentStatus}
                logs={logs}
                onStartAgent={triggerAgentRun}
                onRunComplete={handleRunComplete}
              />
            </div>

            {/* Section 1.5: Legal Consent & MCP Server Health */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* User Consents Card */}
              <Card className="p-6 space-y-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-blue-600" />
                    Legal Consents & Authorizations
                  </h3>
                  <p className="text-11 text-slate-500 mt-0.5">Authorize actions before autonomous agents execute them.</p>
                </div>
                <div className="space-y-3">
                  {[
                    { id: "account_access", label: "Account Access", desc: "Authorize log into career portals using credentials you provide." },
                    { id: "app_submission", label: "Application Submission", desc: "Authorize submit job applications using your profile details." },
                    { id: "resume_upload", label: "Resume Upload", desc: "Authorize upload your resume PDF to third-party portals." },
                    { id: "data_storage", label: "Data Storage", desc: "Authorize store application history and portal session cookies." }
                  ].map(item => (
                    <div key={item.id} className="flex items-start justify-between gap-4 p-3 rounded-2xl bg-slate-50 border border-slate-100/60">
                      <div className="space-y-0.5">
                        <p className="text-xs font-bold text-slate-800">{item.label}</p>
                        <p className="text-10 text-slate-500 leading-normal">{item.desc}</p>
                      </div>
                      <button
                        onClick={() => handleConsentToggle(item.id)}
                        className={`px-3 py-1.5 rounded-lg text-10 font-bold transition cursor-pointer shrink-0 uppercase tracking-wider ${
                          consents[item.id]?.granted
                            ? "bg-emerald-500 hover:bg-emerald-600 text-white"
                            : "bg-slate-200 hover:bg-slate-300 text-slate-700"
                        }`}
                      >
                        {consents[item.id]?.granted ? "Authorized ✓" : "Authorize →"}
                      </button>
                    </div>
                  ))}
                </div>
              </Card>

              {/* MCP Server Health Card */}
              <Card className="p-6 space-y-4">
                <div>
                  <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                    <Laptop className="w-4 h-4 text-indigo-600" />
                    MCP Server Health Panel
                  </h3>
                  <p className="text-11 text-slate-500 mt-0.5">Status of registered local Model Context Protocol servers.</p>
                </div>
                <div className="space-y-2 max-h-[295px] overflow-y-auto pr-1">
                  {mcpServers.length === 0 ? (
                    <p className="text-xs text-slate-400 italic">Loading MCP servers status...</p>
                  ) : (
                    mcpServers.map(server => (
                      <div key={server.name} className="flex items-center justify-between p-2.5 rounded-xl border border-slate-100 bg-slate-50/50">
                        <span className="text-xs font-bold text-slate-700 font-mono">{server.name}</span>
                        <div className="flex items-center gap-3">
                          <span className="text-10 text-slate-500 font-medium font-mono">{server.latency_ms}ms</span>
                          <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            server.status === "Live"
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-100"
                              : "bg-rose-50 text-rose-700 border border-rose-100"
                          }`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${server.status === "Live" ? "bg-emerald-500" : "bg-rose-500"}`} />
                            {server.status}
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </Card>
            </div>

            {jobs.length > 0 && (
              <>
                {/* Section 2: Top Opportunities */}
                <div className="w-full space-y-6">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
                        <Target className="w-4.5 h-4.5 text-emerald-600" />
                      </div>
                      <h2 className="text-lg font-bold text-slate-800">Top Opportunities</h2>
                    </div>
                    {jobs.length > 3 && (
                      <button
                        onClick={() => setShowAllOpportunities(prev => !prev)}
                        className="text-xs font-bold text-blue-600 hover:text-blue-800 transition flex items-center gap-1 cursor-pointer bg-blue-50/50 px-3 py-1.5 rounded-lg border border-blue-100 hover:border-blue-200"
                      >
                        {showAllOpportunities ? "Show Less" : "View All"}
                        <ArrowRight className={`w-3.5 h-3.5 transition-transform duration-200 ${showAllOpportunities ? "rotate-90" : ""}`} />
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {topOpportunities.map((job) => {
                      const styles = getMatchStyles(job.match_score);
                      const isSaved = savedJobIds.has(job.id);
                      return (
                        <div
                          key={job.id}
                          className="bg-card text-card-foreground border border-border rounded-3xl p-6 shadow-xs hover:border-muted-foreground/30 hover:shadow-md transition-all duration-200 relative overflow-hidden flex flex-col justify-between"
                        >
                          <div className={`absolute top-0 right-0 px-2.5 py-1 rounded-bl-lg border-l border-b border-border text-10 font-extrabold flex items-center gap-1 ${styles.bg} ${styles.text}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${styles.dot}`} />
                            {job.match_score}% Match
                          </div>

                          <div className="mb-4">
                            <div className="flex items-start justify-between gap-3 mb-3 mt-3">
                              <div className="flex items-start gap-2.5 min-w-0">
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-slate-700 to-slate-900 flex items-center justify-center text-white text-sm font-extrabold shrink-0 shadow-inner">
                                  {job.company.charAt(0).toUpperCase()}
                                </div>
                                <div className="min-w-0 pr-6">
                                  <h3 className="font-bold text-slate-800 text-sm leading-snug line-clamp-2 min-h-10 flex items-center">
                                    {job.title}
                                  </h3>
                                  <p className="text-slate-500 font-semibold text-11 mt-0.5 truncate">
                                    {job.company}
                                  </p>
                                </div>
                              </div>
                              
                              <button
                                onClick={() => handleSaveJob(job)}
                                className={`p-1.5 rounded-lg border transition shrink-0 ${
                                  isSaved
                                    ? "bg-blue-50 border-blue-200 text-blue-600"
                                    : "bg-white border-slate-200 text-slate-400 hover:text-slate-600"
                                }`}
                              >
                                {isSaved ? <BookmarkCheck className="w-3.5 h-3.5" /> : <Bookmark className="w-3.5 h-3.5" />}
                              </button>
                            </div>

                            <div className="flex flex-wrap items-center gap-1.5 mb-2.5 text-9 font-bold">
                              <span className={`inline-flex items-center gap-1 px-2 py-0.5 border rounded-md uppercase tracking-wider ${getSourceBadgeStyles(job.source)}`}>
                                💼 {job.source}
                              </span>
                              <span className={`inline-flex items-center gap-1 px-2 py-0.5 border rounded-md uppercase tracking-wider ${getVerificationBadge(job.verification_score || 100, job.verification_status || "Fully Verified").bg}`}>
                                <span className={`w-1.5 h-1.5 rounded-full ${getVerificationBadge(job.verification_score || 100, job.verification_status || "Fully Verified").dot}`} />
                                {getVerificationBadge(job.verification_score || 100, job.verification_status || "Fully Verified").text}
                              </span>
                            </div>

                            <div className="flex flex-wrap items-center gap-1.5 mb-3 text-10 text-slate-500 font-medium">
                              <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-slate-50 border border-slate-100 rounded-md">
                                <MapPin className="w-3 h-3 text-slate-400" /> {job.location.split(",")[0]}
                              </span>
                              <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-slate-50 border border-slate-100 rounded-md">
                                <Briefcase className="w-3 h-3 text-slate-400" /> {job.experience}
                              </span>
                              <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-slate-50 border border-slate-100 rounded-md">
                                <Laptop className="w-3 h-3 text-slate-400" /> {job.work_mode}
                              </span>
                            </div>

                            <div className="bg-slate-50 rounded-xl p-2.5 border border-slate-100/70 mb-3 flex items-start gap-2">
                              <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                              <div>
                                <h4 className="text-10 font-bold text-slate-700">Why It Matches</h4>
                                <p className="text-11 text-slate-600 mt-0.5 leading-relaxed line-clamp-2">{job.reasoning}</p>
                              </div>
                            </div>

                            <div className="space-y-1.5 text-10">
                              {job.matched_skills && job.matched_skills.length > 0 && (
                                <div className="flex flex-wrap items-center gap-1">
                                  <span className="font-bold text-emerald-650 uppercase tracking-wider mr-1">Matched:</span>
                                  {job.matched_skills.slice(0, 3).map(skill => (
                                    <span key={skill} className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-100 rounded-md">
                                      {skill}
                                    </span>
                                  ))}
                                </div>
                              )}

                              {job.missing_skills && job.missing_skills.length > 0 && (
                                <div className="flex flex-wrap items-center gap-1">
                                  <span className="font-bold text-rose-500 uppercase tracking-wider mr-1">Missing:</span>
                                  {job.missing_skills.slice(0, 3).map(skill => (
                                    <span key={skill} className="px-1.5 py-0.5 bg-rose-50 text-rose-700 border border-rose-100 rounded-md">
                                      {skill}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>

                          <div className="flex gap-2 pt-3 border-t border-slate-100 mt-auto">
                            <button
                              onClick={() => setSelectedJob(job)}
                              className="flex-1 flex items-center justify-center py-2 bg-slate-900 hover:bg-slate-800 text-white font-semibold rounded-xl text-xs transition cursor-pointer"
                            >
                              Details
                            </button>

                            {job.apply_url && (
                              <a
                                href={job.apply_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex-1 flex items-center justify-center gap-1 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl text-xs transition cursor-pointer"
                              >
                                Apply <ArrowUpRight className="w-3.5 h-3.5" />
                              </a>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Section 4: Recommended Learning Path */}
                {recommendations && (
                  <div className="grid grid-cols-1">
                    <RecommendedLearning recommendations={recommendations} />
                  </div>
                )}

                {/* Section 5: All Ranked Jobs */}
                <Card className="space-y-6">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <h2 className="text-lg font-bold text-foreground">All Ranked Opportunities</h2>
                      <p className="text-xs text-muted-foreground mt-0.5">Explore full ranked pipeline of matched listings</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <Input
                          type="text"
                          placeholder="Filter by keyword..."
                          value={searchQuery}
                          onChange={(e) => {
                            setSearchQuery(e.target.value);
                            setCurrentPage(1);
                          }}
                          className="pl-9 w-44 py-2 text-xs"
                        />
                      </div>

                      {uniqueSources.length > 1 && (
                        <Select
                          value={selectedSource}
                          onChange={(e) => {
                            setSelectedSource(e.target.value);
                            setCurrentPage(1);
                          }}
                          className="py-2 text-xs w-32"
                        >
                          {uniqueSources.map(src => (
                            <option key={src} value={src}>{src}</option>
                          ))}
                        </Select>
                      )}
                    </div>
                  </div>

                  {filteredRemainingJobs.length === 0 ? (
                    <div className="text-center py-10">
                      <p className="text-sm text-slate-400">No additional ranked jobs match your filters.</p>
                    </div>
                  ) : (
                    <>
                      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                        {paginatedJobs.map((job) => {
                          const styles = getMatchStyles(job.match_score);
                          const isSaved = savedJobIds.has(job.id);
                          return (
                            <Card
                              key={job.id}
                              hoverEffect
                              className="p-5 bg-slate-50/50 hover:bg-white hover:border-blue-100 transition duration-200 flex flex-col justify-between"
                            >
                              <div>
                                <div className="flex items-start justify-between gap-3 mb-3">
                                  <div className="min-w-0">
                                    <h4 className="font-bold text-slate-800 text-sm leading-snug line-clamp-2 min-h-10 flex items-center">
                                      {job.title}
                                    </h4>
                                    <p className="text-slate-500 font-semibold text-xs mt-0.5 truncate">
                                      {job.company}
                                    </p>
                                  </div>
                                  <span className={`px-2 py-0.5 border rounded-lg text-10 font-extrabold shrink-0 flex items-center gap-1 ${styles.bg} ${styles.text}`}>
                                    {job.match_score}%
                                  </span>
                                </div>

                                <div className="flex flex-wrap gap-1.5 mb-4 text-11 text-slate-500 font-medium">
                                  <span className="flex items-center gap-0.5"><MapPin className="w-3 h-3" /> {job.location}</span>
                                  <span>•</span>
                                  <span className="flex items-center gap-0.5"><Briefcase className="w-3 h-3" /> {job.experience}</span>
                                </div>

                                <div className="flex flex-wrap gap-1 mb-4">
                                  {job.skills.slice(0, 3).map(skill => (
                                    <span key={skill} className="px-1.5 py-0.5 bg-blue-50/60 text-blue-700 border border-blue-100/50 rounded-md text-10 font-semibold">
                                      {skill}
                                    </span>
                                  ))}
                                </div>
                              </div>

                              <div className="flex items-center justify-between pt-3 border-t border-slate-100/80">
                                <div className="flex flex-wrap items-center gap-1.5 text-9 font-bold">
                                  <span className={`px-2 py-0.5 border rounded-full uppercase tracking-wider ${getSourceBadgeStyles(job.source)}`}>
                                    💼 {job.source}
                                  </span>
                                </div>

                                <div className="flex items-center gap-2">
                                  <button
                                    onClick={() => handleSaveJob(job)}
                                    className={`p-1.5 rounded-lg border transition ${
                                      isSaved
                                        ? "bg-blue-50 border-blue-200 text-blue-600"
                                        : "bg-white border-slate-200 text-slate-400 hover:text-slate-600"
                                    }`}
                                  >
                                    {isSaved ? <BookmarkCheck className="w-4 h-4" /> : <Bookmark className="w-4 h-4" />}
                                  </button>
                                  <button
                                    onClick={() => setSelectedJob(job)}
                                    className="text-xs font-bold text-blue-600 hover:text-blue-800 transition flex items-center gap-0.5"
                                  >
                                    Details <ArrowRight className="w-3 h-3" />
                                  </button>
                                </div>
                              </div>
                            </Card>
                          );
                        })}
                      </div>

                      {totalPages > 1 && (
                        <div className="flex items-center justify-between pt-4 border-t border-slate-50">
                          <p className="text-xs text-slate-500">
                            Showing page {currentPage} of {totalPages} ({filteredRemainingJobs.length} total remaining)
                          </p>

                          <div className="flex items-center gap-2">
                            <button
                              disabled={currentPage === 1}
                              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                              className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-40"
                            >
                              <ChevronLeft className="w-4 h-4" />
                            </button>
                            <button
                              disabled={currentPage === totalPages}
                              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                              className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-40"
                            >
                              <ChevronRight className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </Card>
              </>
            )}
          </>
        )}

        {/* TAB 2: PRE-COLLECTED JOB POOL */}
        {activeTab === "job_pool" && (
          <div className="space-y-6">
            {/* Tab Header explanation */}
            <Card className="p-6 bg-gradient-to-r from-blue-500/10 via-indigo-500/5 to-transparent border-blue-200/50">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center text-blue-600 shrink-0">
                  <Briefcase className="w-5.5 h-5.5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-foreground">Instant Job Pool Feed</h2>
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed max-w-3xl">
                    Discover jobs discovered in the background by autonomous crawlers (every 10 minutes) across direct Lever/Greenhouse APIs, RSS channels, and Google. Results are matches, rated with dynamic opportunity scores, and load instantly (&lt;100ms).
                  </p>
                </div>
              </div>
            </Card>

            {/* Filter controls */}
            <Card className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-50/50">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  type="text"
                  placeholder="Filter pool jobs (role, skills, company)..."
                  value={poolSearchQuery}
                  onChange={(e) => setPoolSearchQuery(e.target.value)}
                  className="pl-9 w-full text-xs py-2 bg-white"
                />
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Source</span>
                  <Select
                    value={poolSelectedSource}
                    onChange={(e) => setPoolSelectedSource(e.target.value)}
                    className="py-1 text-xs w-36 bg-white"
                  >
                    {poolSources.map(src => (
                      <option key={src} value={src}>{src}</option>
                    ))}
                  </Select>
                </div>

                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Mode</span>
                  <Select
                    value={poolSelectedWorkMode}
                    onChange={(e) => setPoolSelectedWorkMode(e.target.value)}
                    className="py-1 text-xs w-32 bg-white"
                  >
                    {poolWorkModes.map(mode => (
                      <option key={mode} value={mode}>{mode}</option>
                    ))}
                  </Select>
                </div>

                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Min Opp Score</span>
                  <Select
                    value={poolMinScore}
                    onChange={(e) => setPoolMinScore(Number(e.target.value))}
                    className="py-1 text-xs w-32 bg-white"
                  >
                    <option value="0">All Scores</option>
                    <option value="60">60% (Good+)</option>
                    <option value="75">75% (Strong+)</option>
                    <option value="90">90% (Top🔥)</option>
                  </Select>
                </div>

                <Button
                  onClick={fetchJobPool}
                  disabled={loadingJobPool}
                  variant="outline"
                  className="mt-5 text-xs py-2 h-[34px]"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingJobPool ? "animate-spin" : ""}`} />
                </Button>
              </div>
            </Card>

            {/* Grid */}
            {loadingJobPool ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[1, 2, 3].map(i => (
                  <div key={i} className="bg-card border border-border rounded-3xl p-6 h-64 animate-pulse">
                    <div className="h-6 bg-slate-200 dark:bg-slate-800 rounded w-1/4 mb-4" />
                    <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-3/4 mb-3" />
                    <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded w-1/2 mb-6" />
                    <div className="h-10 bg-slate-200 dark:bg-slate-800 rounded w-full mt-auto" />
                  </div>
                ))}
              </div>
            ) : filteredJobPool.length === 0 ? (
              <Card className="p-12 text-center">
                <Briefcase className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
                <h3 className="text-sm font-bold text-foreground">No Jobs in Pool</h3>
                <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                  Try tweaking your search keywords or filter values. You can also run the Search Agent to fetch fresh job updates.
                </p>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {filteredJobPool.map(job => {
                  const score = job.opportunity_score || 0;
                  const label = getOpportunityLabel(score);
                  const isSaved = savedJobIds.has(job.id);
                  const isApplying = applyingIds.has(job.id);
                  return (
                    <div
                      key={job.id}
                      className="bg-card text-card-foreground border border-border rounded-3xl p-6 shadow-xs hover:border-blue-300 hover:shadow-md transition-all duration-200 relative overflow-hidden flex flex-col justify-between"
                    >
                      {/* Opportunity Score Ring/Badge */}
                      <div className={`absolute top-0 right-0 px-3 py-1 rounded-bl-xl bg-gradient-to-tr font-extrabold text-[10px] flex items-center gap-1 shadow-sm uppercase tracking-wider ${getOpportunityBadgeStyles(score)}`}>
                        {label} ({score}%)
                      </div>

                      <div className="mb-4">
                        <div className="flex items-start justify-between gap-3 mb-3 mt-4">
                          <div className="flex items-start gap-2.5 min-w-0">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-slate-700 to-indigo-800 flex items-center justify-center text-white text-sm font-extrabold shrink-0 shadow-inner">
                              {job.company.charAt(0).toUpperCase()}
                            </div>
                            <div className="min-w-0 pr-6">
                              <h3 className="font-bold text-slate-800 text-sm leading-snug line-clamp-2 min-h-10 flex items-center">
                                {job.title}
                              </h3>
                              <p className="text-slate-500 font-semibold text-11 mt-0.5 truncate">
                                {job.company}
                              </p>
                            </div>
                          </div>
                          
                          <button
                            onClick={() => handleSaveJob(job)}
                            className={`p-1.5 rounded-lg border transition shrink-0 ${
                              isSaved
                                ? "bg-blue-50 border-blue-200 text-blue-600"
                                : "bg-white border-slate-200 text-slate-400 hover:text-slate-600"
                            }`}
                          >
                            {isSaved ? <BookmarkCheck className="w-3.5 h-3.5" /> : <Bookmark className="w-3.5 h-3.5" />}
                          </button>
                        </div>

                        <div className="flex flex-wrap items-center gap-1.5 mb-3 text-9 font-bold">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 border rounded-md uppercase tracking-wider ${getSourceBadgeStyles(job.source)}`}>
                            💼 {job.source}
                          </span>
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 border border-emerald-100 bg-emerald-50 text-emerald-700 rounded-md uppercase tracking-wider">
                            🎯 Match: {job.match_score}%
                          </span>
                        </div>

                        <div className="flex flex-wrap items-center gap-1.5 mb-4 text-10 text-slate-500 font-medium">
                          <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-slate-50 border border-slate-100 rounded-md">
                            <MapPin className="w-3 h-3 text-slate-400" /> {job.location.split(",")[0]}
                          </span>
                          {job.experience && (
                            <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-slate-50 border border-slate-100 rounded-md">
                              <Briefcase className="w-3 h-3 text-slate-400" /> {job.experience}
                            </span>
                          )}
                          <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-slate-50 border border-slate-100 rounded-md">
                            <Laptop className="w-3 h-3 text-slate-400" /> {job.work_mode}
                          </span>
                        </div>

                        {job.skills && job.skills.length > 0 && (
                          <div className="space-y-1.5 text-10">
                            <div className="flex flex-wrap items-center gap-1">
                              <span className="font-bold text-slate-500 uppercase tracking-wider mr-1">Skills:</span>
                              {job.skills.slice(0, 3).map(skill => (
                                <span key={skill} className="px-1.5 py-0.5 bg-blue-50/70 text-blue-700 border border-blue-100/30 rounded-md">
                                  {skill}
                                </span>
                              ))}
                              {job.skills.length > 3 && (
                                <span className="px-1 py-0.5 bg-slate-100 text-slate-500 rounded-md text-[9px] font-bold">
                                  +{job.skills.length - 3}
                                </span>
                              )}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Action buttons */}
                      <div className="flex flex-col gap-2 pt-3 border-t border-slate-100 mt-auto">
                        <div className="flex gap-2">
                          <button
                            onClick={() => setSelectedJob(job)}
                            className="flex-1 flex items-center justify-center py-2 bg-slate-900 hover:bg-slate-800 text-white font-semibold rounded-xl text-xs transition cursor-pointer"
                          >
                            Details
                          </button>
                          
                          {job.apply_url && (
                            <a
                              href={job.apply_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex-1 flex items-center justify-center gap-1 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl text-xs transition cursor-pointer"
                            >
                              Apply Directly <ArrowUpRight className="w-3.5 h-3.5" />
                            </a>
                          )}
                        </div>

                        <button
                          onClick={() => handleAutoApply(job.id)}
                          disabled={isApplying || !consents.app_submission?.granted}
                          className={`w-full py-2 flex items-center justify-center gap-1.5 font-bold rounded-xl text-xs transition cursor-pointer ${
                            consents.app_submission?.granted
                              ? "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white"
                              : "bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200"
                          }`}
                        >
                          <Zap className={`w-3.5 h-3.5 ${isApplying ? "animate-pulse" : ""}`} />
                          {isApplying ? "Queuing Apply..." : consents.app_submission?.granted ? "Queue Auto-Apply" : "Auto-Apply (Needs Consent)"}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* TAB 3: SAVED JOBS */}
        {activeTab === "saved" && (
          <div className="space-y-6">
            <Card className="p-6 bg-gradient-to-r from-emerald-500/10 via-emerald-500/5 to-transparent border-emerald-200/50">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center text-emerald-600 shrink-0">
                  <Bookmark className="w-5.5 h-5.5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-foreground">Saved Pipeline</h2>
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed max-w-3xl">
                    Review and submit applications for jobs you have bookmarked. Work with the autonomous agent to auto-apply or view descriptions.
                  </p>
                </div>
              </div>
            </Card>

            {loadingSavedJobs ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[1, 2].map(i => (
                  <div key={i} className="bg-card border border-border rounded-3xl p-6 h-48 animate-pulse" />
                ))}
              </div>
            ) : savedJobs.length === 0 ? (
              <Card className="p-12 text-center bg-slate-50/30 border-dashed border-2">
                <Bookmark className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                <h3 className="text-sm font-bold text-foreground">No Saved Jobs</h3>
                <p className="text-xs text-muted-foreground mt-1 max-w-xs mx-auto">
                  Bookmark jobs from the AI Search Agent or Job Pool feed to build your personal pipeline.
                </p>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {savedJobs.map(sj => {
                  const jobItem = sj.job;
                  if (!jobItem) return null;
                  const isApplying = applyingIds.has(String(jobItem.id));
                  
                  // Wrap DB job in a LiveJob compatible structure
                  const liveCompatible: LiveJob = {
                    id: String(jobItem.id),
                    title: jobItem.title,
                    company: jobItem.department,
                    location: jobItem.location,
                    experience: jobItem.experience_level,
                    work_mode: "On-site",
                    skills: jobItem.required_skills ? jobItem.required_skills.split(",").map((s: string) => s.trim()) : [],
                    apply_url: jobItem.source_url || "",
                    posted_date: "Saved",
                    source: jobItem.source_platform || "Database",
                    description: jobItem.description,
                    match_score: jobItem.match_score || 70,
                    reasoning: "Manually Bookmarked"
                  };

                  return (
                    <div
                      key={sj.id}
                      className="bg-card text-card-foreground border border-border rounded-3xl p-6 shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-start justify-between gap-3 mb-3">
                          <div className="min-w-0">
                            <h3 className="font-bold text-slate-800 text-sm leading-snug line-clamp-2 min-h-10 flex items-center">
                              {jobItem.title}
                            </h3>
                            <p className="text-slate-500 font-semibold text-11 mt-0.5 truncate">
                              {jobItem.department}
                            </p>
                          </div>
                          
                          <button
                            onClick={() => handleSaveJob(liveCompatible)}
                            className="p-1.5 rounded-lg border border-blue-200 bg-blue-50 text-blue-600 transition shrink-0"
                          >
                            <BookmarkCheck className="w-3.5 h-3.5" />
                          </button>
                        </div>

                        <div className="flex flex-wrap items-center gap-1.5 mb-3 text-10 text-slate-500 font-medium">
                          <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-slate-50 border border-slate-100 rounded-md">
                            <MapPin className="w-3 h-3 text-slate-400" /> {jobItem.location}
                          </span>
                          <span className="inline-flex items-center gap-0.5 px-2 py-0.5 bg-slate-50 border border-slate-100 rounded-md">
                            <Briefcase className="w-3 h-3 text-slate-400" /> {jobItem.experience_level}
                          </span>
                        </div>

                        <div className="flex flex-wrap gap-1 mb-4">
                          {liveCompatible.skills.slice(0, 3).map((skill: string) => (
                            <span key={skill} className="px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded-md text-10 font-medium">
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Action buttons */}
                      <div className="flex flex-col gap-2 pt-3 border-t border-slate-100 mt-auto">
                        <div className="flex gap-2">
                          <button
                            onClick={() => setSelectedJob(liveCompatible)}
                            className="flex-1 flex items-center justify-center py-2 bg-slate-900 hover:bg-slate-800 text-white font-semibold rounded-xl text-xs transition cursor-pointer"
                          >
                            Details
                          </button>
                          
                          {jobItem.source_url && (
                            <a
                              href={jobItem.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex-1 flex items-center justify-center gap-1 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl text-xs transition cursor-pointer"
                            >
                              Apply Directly <ArrowUpRight className="w-3.5 h-3.5" />
                            </a>
                          )}
                        </div>

                        <button
                          onClick={() => handleAutoApply(String(jobItem.id))}
                          disabled={isApplying || !consents.app_submission?.granted}
                          className={`w-full py-2 flex items-center justify-center gap-1.5 font-bold rounded-xl text-xs transition cursor-pointer ${
                            consents.app_submission?.granted
                              ? "bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white"
                              : "bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200"
                          }`}
                        >
                          <Zap className={`w-3.5 h-3.5 ${isApplying ? "animate-pulse" : ""}`} />
                          {isApplying ? "Queuing Apply..." : consents.app_submission?.granted ? "Queue Auto-Apply" : "Auto-Apply (Needs Consent)"}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Description Modal */}
      {selectedJob && (
        <Modal
          isOpen={!!selectedJob}
          onClose={() => setSelectedJob(null)}
          title={selectedJob.title}
          className="max-w-2xl max-h-[85vh]"
        >
          <div className="flex flex-col h-full -m-6">
            <div className="px-6 py-4 border-b border-border bg-muted/20 flex items-center justify-between gap-3 shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-slate-700 to-slate-900 flex items-center justify-center text-white text-sm font-extrabold shrink-0">
                  {selectedJob.company.charAt(0).toUpperCase()}
                </div>
                <div>
                  <h4 className="font-bold text-foreground text-sm">{selectedJob.company}</h4>
                </div>
              </div>

              {selectedJob.opportunity_score !== undefined && (
                <div className={`px-3 py-1.5 rounded-xl text-xs font-bold bg-gradient-to-r shadow-xs ${getOpportunityBadgeStyles(selectedJob.opportunity_score)}`}>
                  Opportunity: {selectedJob.opportunity_score}%
                </div>
              )}
            </div>

            {/* Scrollable Body */}
            <div className="p-6 overflow-y-auto space-y-6 text-sm text-muted-foreground flex-1">
              <div className="bg-muted/30 rounded-xl p-4 border border-border flex items-start gap-3">
                <Target className="w-5 h-5 text-primary shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-bold text-foreground">Detailed AI Match Summary</h4>
                  <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{selectedJob.reasoning}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-muted/20 rounded-xl p-3.5 border border-border flex flex-col gap-1.5">
                  <span className="text-10 text-muted-foreground font-bold uppercase tracking-wider">Source Platform</span>
                  <span className={`text-11 font-bold inline-flex items-center gap-1.5 px-3 py-1 border rounded-lg w-max ${getSourceBadgeStyles(selectedJob.source)}`}>
                    💼 {selectedJob.source}
                  </span>
                </div>
                <div className="bg-muted/20 rounded-xl p-3.5 border border-border flex flex-col gap-1.5">
                  <span className="text-10 text-muted-foreground font-bold uppercase tracking-wider">Landed Page Consistency</span>
                  <span className={`text-11 font-bold inline-flex items-center gap-1.5 px-3 py-1 border rounded-lg w-max ${getVerificationBadge(selectedJob.verification_score || 100, selectedJob.verification_status || "Fully Verified").bg}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${getVerificationBadge(selectedJob.verification_score || 100, selectedJob.verification_status || "Fully Verified").dot}`} />
                    {getVerificationBadge(selectedJob.verification_score || 100, selectedJob.verification_status || "Fully Verified").text}
                  </span>
                </div>
              </div>

              <div>
                <h4 className="text-xs font-bold text-foreground uppercase tracking-wider mb-2">Job Description</h4>
                <div className="text-xs leading-relaxed whitespace-pre-wrap">{selectedJob.description}</div>
              </div>

              <div>
                <h4 className="text-xs font-bold text-foreground uppercase tracking-wider mb-2">Target Skills</h4>
                <div className="flex flex-wrap gap-1.5">
                  {selectedJob.skills.map(skill => {
                    const isMatched = selectedJob.matched_skills ? selectedJob.matched_skills.includes(skill) : true;
                    return (
                      <span
                        key={skill}
                        className={`px-2.5 py-0.5 border rounded-md text-xs font-medium ${
                          isMatched
                            ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-600 dark:text-emerald-450"
                            : "bg-destructive/10 border-destructive/20 text-destructive"
                        }`}
                      >
                        {skill} {isMatched ? "✓" : "✗"}
                      </span>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="p-4 bg-muted/10 border-t border-border flex gap-3 shrink-0">
              <Button
                onClick={() => {
                  handleSaveJob(selectedJob);
                  setSelectedJob(prev => prev ? { ...prev, is_saved: !savedJobIds.has(prev.id) } : null);
                }}
                variant={savedJobIds.has(selectedJob.id) ? "secondary" : "outline"}
                className="flex items-center gap-2"
              >
                {savedJobIds.has(selectedJob.id) ? <BookmarkCheck className="w-4.5 h-4.5" /> : <Bookmark className="w-4.5 h-4.5" />}
                <span>{savedJobIds.has(selectedJob.id) ? "Saved" : "Save Job"}</span>
              </Button>

              {selectedJob.apply_url && (
                <a
                  href={selectedJob.apply_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1"
                >
                  <Button className="w-full flex items-center justify-center gap-1.5">
                    Apply Directly <ArrowUpRight className="w-4 h-4" />
                  </Button>
                </a>
              )}
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
