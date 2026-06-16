"use client";

import { useEffect, useState, useCallback } from "react";
import { apiService } from "@/services/api";
import {
  MapPin, Search, X, Briefcase, Bookmark, BookmarkCheck,
  ArrowUpRight, RefreshCw, Zap, Building2,
  Clock, Target, AlertCircle, Laptop, Sparkles, CheckCircle2,
  ArrowRight, ShieldCheck, HelpCircle, ChevronLeft, ChevronRight
} from "lucide-react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
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
  matched_skills: string[];
  missing_skills: string[];
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
    return "bg-indigo-50 text-indigo-700 border-indigo-150";
  }
  if (lower.includes("linkedin")) return "bg-blue-50 text-blue-700 border-blue-150";
  if (lower.includes("naukri")) return "bg-orange-50 text-orange-700 border-orange-150";
  if (lower.includes("foundit")) return "bg-green-50 text-green-700 border-green-150";
  if (lower.includes("internshala")) return "bg-purple-50 text-purple-700 border-purple-150";
  if (lower.includes("wellfound")) return "bg-rose-50 text-rose-700 border-rose-150";
  if (lower.includes("cutshort")) return "bg-teal-50 text-teal-700 border-teal-150";
  if (lower.includes("instahyre")) return "bg-cyan-50 text-cyan-700 border-cyan-150";
  if (lower.includes("hirist")) return "bg-amber-50 text-amber-700 border-amber-150";
  return "bg-slate-50 text-slate-600 border-slate-150";
}

function getVerificationBadge(score: number, status: string) {
  if (status === "Fully Verified" || score >= 85) {
    return {
      dot: "bg-emerald-500",
      text: "Fully Verified",
      bg: "bg-emerald-50/70 text-emerald-700 border-emerald-150"
    };
  }
  if (status === "Partially Verified" || score >= 50) {
    return {
      dot: "bg-amber-500",
      text: "Partially Verified",
      bg: "bg-amber-50/70 text-amber-700 border-amber-150"
    };
  }
  return {
    dot: "bg-rose-500",
    text: "Rejected",
    bg: "bg-rose-50/70 text-rose-700 border-rose-150"
  };
}

function getMatchStyles(score: number) {
  if (score >= 80) return { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-150", dot: "bg-emerald-500", glow: "shadow-emerald-100" };
  if (score >= 60) return { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-150", dot: "bg-amber-500", glow: "shadow-amber-100" };
  return { bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-150", dot: "bg-rose-500", glow: "shadow-rose-100" };
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

  const [jobs, setJobs] = useState<LiveJob[]>(() => getCachedValue("jobs_list", []));
  const [skillGaps, setSkillGaps] = useState<SkillGap[]>(() => getCachedValue("jobs_skill_gaps", []));
  const [recommendations, setRecommendations] = useState<Recommendations | null>(() => getCachedValue("jobs_recommendations", null));
  
  // Agent Run States
  const [runId, setRunId] = useState<number | null>(() => getCachedValue("jobs_run_id", null));
  const [agentStatus, setAgentStatus] = useState<string>(() => getCachedValue("jobs_agent_status", "idle")); // idle, running, completed, failed
  const [logs, setLogs] = useState<any[]>(() => getCachedValue("jobs_agent_logs", []));

  // Page level states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [savedJobIds, setSavedJobIds] = useState<Set<string>>(new Set());

  // Search & Filter within Ranked Jobs
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSource, setSelectedSource] = useState("All");
  const [showAllOpportunities, setShowAllOpportunities] = useState(false);

  // Pagination for remaining ranked jobs
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 3;

  // Selected job details modal
  const [selectedJob, setSelectedJob] = useState<LiveJob | null>(null);

  // Trigger a fresh agent run
  const triggerAgentRun = async () => {
    try {
      setLoading(true);
      setError("");
      // NOTE: We DO NOT clear jobs, skillGaps, and recommendations here so they remain displayed instantly!
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
          // Trigger first agent run automatically
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
      try {
        await apiService.unsaveJob(job.id);
      } catch {
        newSaved.add(job.id);
        setSavedJobIds(new Set(newSaved));
      }
    } else {
      newSaved.add(job.id);
      setSavedJobIds(newSaved);
      try {
        await apiService.saveJob(job.id);
      } catch {
        newSaved.delete(job.id);
        setSavedJobIds(new Set(newSaved));
      }
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

        {/* Show results sections if completed or logs exist */}
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
                    className="text-xs font-bold text-blue-600 hover:text-blue-800 transition flex items-center gap-1 cursor-pointer bg-blue-50/50 px-3 py-1.5 rounded-lg border border-blue-100 hover:border-blue-200 font-semibold"
                  >
                    {showAllOpportunities ? "Show Less" : "View All"}
                    <ArrowRight className={`w-3.5 h-3.5 transition-transform duration-200 ${showAllOpportunities ? "rotate-90" : ""}`} />
                  </button>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {topOpportunities.map((job, idx) => {
                  const styles = getMatchStyles(job.match_score);
                  const isSaved = savedJobIds.has(job.id);
                  return (
                    <motion.div
                      key={job.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: idx * 0.1 }}
                      className="bg-card text-card-foreground border border-border rounded-3xl p-6 shadow-xs hover:border-muted-foreground/30 hover:shadow-md transition-all duration-200 relative overflow-hidden flex flex-col justify-between"
                    >
                      {/* Match ribbon */}
                      <div className={`absolute top-0 right-0 px-2.5 py-1 rounded-bl-lg border-l border-b border-border text-[10px] font-extrabold flex items-center gap-1 ${styles.bg} ${styles.text}`}>
                        <span className={`w-1 h-1 rounded-full ${styles.dot}`} />
                        {job.match_score}%
                      </div>

                      <div className="mb-4">
                        {/* Role Header */}
                        <div className="flex items-start justify-between gap-3 mb-3 mt-3">
                          <div className="flex items-start gap-2.5 min-w-0">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-slate-700 to-slate-900 flex items-center justify-center text-white text-sm font-extrabold shrink-0 shadow-inner">
                              {job.company.charAt(0).toUpperCase()}
                            </div>
                            <div className="min-w-0 pr-6">
                              <h3 className="font-bold text-slate-800 text-sm leading-snug line-clamp-2 min-h-[40px] flex items-center">
                                {job.title}
                              </h3>
                              <p className="text-slate-500 font-semibold text-[11px] mt-0.5 truncate">
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

                        {/* Source & Verification Badges */}
                        <div className="flex flex-wrap items-center gap-1.5 mb-2.5 text-[9px] font-bold">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 border rounded-md uppercase tracking-wider ${getSourceBadgeStyles(job.source)}`}>
                            {job.source.toLowerCase().includes("telegram") ? "📢" : "💼"} {job.source}
                          </span>
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 border rounded-md uppercase tracking-wider ${getVerificationBadge(job.verification_score || 100, job.verification_status || "Fully Verified").bg}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${getVerificationBadge(job.verification_score || 100, job.verification_status || "Fully Verified").dot}`} />
                            {getVerificationBadge(job.verification_score || 100, job.verification_status || "Fully Verified").text} ({job.verification_score || 100}%)
                          </span>
                        </div>

                        {/* Meta details */}
                        <div className="flex flex-wrap items-center gap-1.5 mb-3 text-[10px] text-slate-500 font-medium">
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

                        {/* Reasoning */}
                        <div className="bg-slate-50 rounded-xl p-2.5 border border-slate-100/70 mb-3 flex items-start gap-2">
                          <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                          <div>
                            <h4 className="text-[10px] font-bold text-slate-700">Why It Matches</h4>
                            <p className="text-[11px] text-slate-600 mt-0.5 leading-relaxed line-clamp-2">{job.reasoning}</p>
                          </div>
                        </div>

                        {/* Skills badges */}
                        <div className="space-y-1.5 text-[10px]">
                          {job.matched_skills.length > 0 && (
                            <div className="flex flex-wrap items-center gap-1">
                              <span className="font-bold text-emerald-600 uppercase tracking-wider mr-1">Matched:</span>
                              {job.matched_skills.slice(0, 3).map(skill => (
                                <span key={skill} className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-100 rounded-md">
                                  {skill}
                                </span>
                              ))}
                              {job.matched_skills.length > 3 && (
                                <span className="px-1 py-0.5 bg-slate-100 text-slate-500 rounded-md">
                                  +{job.matched_skills.length - 3}
                                </span>
                              )}
                            </div>
                          )}

                          {job.missing_skills.length > 0 && (
                            <div className="flex flex-wrap items-center gap-1">
                              <span className="font-bold text-rose-500 uppercase tracking-wider mr-1">Missing:</span>
                              {job.missing_skills.slice(0, 3).map(skill => (
                                <span key={skill} className="px-1.5 py-0.5 bg-rose-50 text-rose-700 border border-rose-100 rounded-md">
                                  {skill}
                                </span>
                              ))}
                              {job.missing_skills.length > 3 && (
                                <span className="px-1 py-0.5 bg-slate-100 text-slate-500 rounded-md">
                                  +{job.missing_skills.length - 3}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Footer buttons */}
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
                    </motion.div>
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
                                <h4 className="font-bold text-slate-800 text-sm leading-snug line-clamp-2 min-h-[40px] flex items-center">
                                  {job.title}
                                </h4>
                                <p className="text-slate-500 font-semibold text-xs mt-0.5 truncate">
                                  {job.company}
                                </p>
                              </div>
                              <span className={`px-2 py-0.5 border rounded-lg text-[10px] font-extrabold shrink-0 flex items-center gap-1 ${styles.bg} ${styles.text}`}>
                                {job.match_score}%
                              </span>
                            </div>

                            <div className="flex flex-wrap gap-1.5 mb-4 text-[11px] text-slate-500 font-medium">
                              <span className="flex items-center gap-0.5"><MapPin className="w-3 h-3" /> {job.location}</span>
                              <span>•</span>
                              <span className="flex items-center gap-0.5"><Briefcase className="w-3 h-3" /> {job.experience}</span>
                            </div>

                            <div className="flex flex-wrap gap-1 mb-4">
                              {job.skills.slice(0, 3).map(skill => (
                                <span key={skill} className="px-1.5 py-0.5 bg-blue-50/60 text-blue-700 border border-blue-100/50 rounded-md text-[10px] font-semibold">
                                  {skill}
                                </span>
                              ))}
                              {job.skills.length > 3 && (
                                <span className="px-1.5 py-0.5 bg-slate-100 text-slate-500 rounded-md text-[10px] font-semibold">
                                  +{job.skills.length - 3}
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center justify-between pt-3 border-t border-slate-100/80">
                            <div className="flex flex-wrap items-center gap-1.5 text-[9px] font-bold">
                              <span className={`px-2 py-0.5 border rounded-full uppercase tracking-wider ${getSourceBadgeStyles(job.source)}`}>
                                {job.source.toLowerCase().includes("telegram") ? "📢" : "💼"} {job.source}
                              </span>
                              <span className={`px-2 py-0.5 border rounded-full flex items-center gap-1 uppercase tracking-wider ${getVerificationBadge(job.verification_score || 100, job.verification_status || "Fully Verified").bg}`}>
                                <span className={`w-1.5 h-1.5 rounded-full ${getVerificationBadge(job.verification_score || 100, job.verification_status || "Fully Verified").dot}`} />
                                {job.verification_score || 100}%
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

                  {/* Pagination controls */}
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
            {/* Modal Subheader info */}
            <div className="px-6 py-4 border-b border-border bg-muted/20 flex items-center gap-3 shrink-0">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-slate-700 to-slate-900 flex items-center justify-center text-white text-sm font-extrabold shrink-0">
                {selectedJob.company.charAt(0).toUpperCase()}
              </div>
              <div>
                <h4 className="font-bold text-foreground text-sm">{selectedJob.company}</h4>
              </div>
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

              {/* Source & Verification Badges in Modal */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-muted/20 rounded-xl p-3.5 border border-border flex flex-col gap-1.5">
                  <span className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider">Source Platform</span>
                  <span className={`text-[11px] font-bold inline-flex items-center gap-1.5 px-3 py-1 border rounded-lg w-max ${getSourceBadgeStyles(selectedJob.source)}`}>
                    {selectedJob.source.toLowerCase().includes("telegram") ? "📢" : "💼"} {selectedJob.source}
                  </span>
                </div>
                <div className="bg-muted/20 rounded-xl p-3.5 border border-border flex flex-col gap-1.5">
                  <span className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider">Landed Page Consistency</span>
                  <span className={`text-[11px] font-bold inline-flex items-center gap-1.5 px-3 py-1 border rounded-lg w-max ${getVerificationBadge(selectedJob.verification_score || 100, selectedJob.verification_status || "Fully Verified").bg}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${getVerificationBadge(selectedJob.verification_score || 100, selectedJob.verification_status || "Fully Verified").dot}`} />
                    {getVerificationBadge(selectedJob.verification_score || 100, selectedJob.verification_status || "Fully Verified").text} ({selectedJob.verification_score || 100}%)
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
                    const isMatched = selectedJob.matched_skills.includes(skill);
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
