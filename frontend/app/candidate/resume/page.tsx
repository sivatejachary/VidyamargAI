"use client";

import { useEffect, useState, useRef } from "react";
import { apiService, getBackendBaseUrl } from "@/services/api";
import { useAuthStore } from "@/store/authStore";
import { useWebSockets } from "@/hooks/useWebSockets";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { 
  Download, Trash2, Eye, Upload, Sparkles, CheckCircle2, 
  Loader2, FileText, ChevronRight, Check, AlertCircle, 
  ShieldCheck, TrendingUp, Zap, AlertTriangle, Award, 
  Link2, GraduationCap, Briefcase, MapPin, Mail, Phone, 
  Code, Folder, Trophy, Globe, Languages, User, LayoutDashboard,
  Dna, Route, Compass, FileCheck, X, ExternalLink
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { ProgressBar } from "@/components/ui/Progress";

const profileSections = [
  { id: "personal", name: "Personal Info", icon: User },
  { id: "summary", name: "Summary", icon: FileText },
  { id: "skills", name: "Skills", icon: Code },
  { id: "experience", name: "Experience", icon: Briefcase },
  { id: "education", name: "Education", icon: GraduationCap },
  { id: "projects", name: "Projects", icon: Folder },
  { id: "certifications", name: "Certifications", icon: Award },
  { id: "achievements", name: "Achievements", icon: Trophy },
  { id: "languages", name: "Languages", icon: Languages },
  { id: "socials", name: "Social Links", icon: Globe }
];

export default function ResumeIntelligenceDashboard() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const { fullName, email, updateUser } = useAuthStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Layout and Tab States
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [activeDrawerTab, setActiveDrawerTab] = useState<string>("personal");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadStep, setUploadStep] = useState(0);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [fastMode, setFastMode] = useState(true);

  // Slide-over & Preview States
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [analysisLoading, setAnalysisLoading] = useState(false);

  // Career Intelligence Data States
  const [profile, setProfile] = useState<any>(null);
  const [versions, setVersions] = useState<any[]>([]);
  const [careerDna, setCareerDna] = useState<any>(null);
  const [skillsGraph, setSkillsGraph] = useState<any>(null);
  const [roles, setRoles] = useState<any>(null);
  const [careerPaths, setCareerPaths] = useState<any[]>([]);
  const [skillGaps, setSkillGaps] = useState<any>(null);
  const [opportunities, setOpportunities] = useState<any>(null);
  const [marketIntel, setMarketIntel] = useState<any>(null);
  const [improvements, setImprovements] = useState<any>(null);

  // Loading Job Agent
  const [agentCreating, setAgentCreating] = useState(false);

  // Read-only Drawer Form State
  const [editForm, setEditForm] = useState<any>({
    name: "",
    email: "",
    phone: "",
    address: "",
    summary: "",
    experienceList: [],
    projectList: [],
    educationList: [],
    certifications: "",
    achievementsList: [],
    languages: "",
    linkedin: "",
    github: "",
    portfolio: ""
  });

  // Load intelligence details from backend
  const loadIntelligence = async () => {
    setLoading(true);
    setErrorMsg("");
    try {
      const resumeList = await apiService.getResumes();
      setVersions(resumeList || []);

      if (resumeList && resumeList.length > 0) {
        const [
          profData,
          dnaData,
          skillsData,
          rolesData,
          pathsData,
          gapsData,
          oppsData,
          marketData,
          impData
        ] = await Promise.all([
          apiService.getResumeProfile(),
          apiService.getResumeCareerDna(),
          apiService.getResumeSkills(),
          apiService.getResumeRoles(),
          apiService.getResumeCareerPaths(),
          apiService.getResumeSkillGaps(),
          apiService.getResumeOpportunities(),
          apiService.getResumeMarketIntelligence(),
          apiService.getResumeImprovements()
        ]);

        setProfile(profData);
        setCareerDna(dnaData);
        setSkillsGraph(skillsData);
        setRoles(rolesData);
        setCareerPaths(pathsData || []);
        setSkillGaps(gapsData);
        setOpportunities(oppsData);
        setMarketIntel(marketData);
        setImprovements(impData);

        if (profData?.personal_info?.name && profData.personal_info.name !== fullName) {
          updateUser(profData.personal_info.name, profData.personal_info.email || email);
        }
      }
    } catch (err: any) {
      console.error("Failed to load Career Intelligence:", err);
      setErrorMsg("Failed to load Career Intelligence. Please upload a resume to start.");
    } finally {
      setLoading(false);
    }
  };

  // WebSockets for real-time progress
  const clientId = profile?.id ? `candidate_${profile.id}` : "";
  const { addMessageListener } = useWebSockets(clientId);

  useEffect(() => {
    if (!clientId) return;
    const removeListener = addMessageListener((event: any) => {
      if (event.type === "resume_processing") {
        setUploading(true);
        let stepNum = 1;
        if (event.status === "uploading") stepNum = 1;
        else if (event.status === "extracting_text") stepNum = 2;
        else if (event.status === "parsing_resume") stepNum = 3;
        else if (event.status === "building_profile") stepNum = 4;
        else if (event.status === "generating_embeddings") stepNum = 5;
        setUploadStep(stepNum);
        setUploadProgress(event.progress || 0);
      } else if (event.type === "resume_processed") {
        setUploadProgress(100);
        setSuccessMsg("Resume uploaded and parsed successfully! Career DNA active.");
        setUploading(false);
        setTimeout(() => setSuccessMsg(""), 5000);
        loadIntelligence();
      }
    });
    return () => removeListener();
  }, [clientId, addMessageListener]);

  useEffect(() => {
    loadIntelligence();
  }, []);

  // Update Drawer form state whenever profile changes
  useEffect(() => {
    if (profile) {
      let expList = [];
      try {
        expList = typeof profile.experience === "string" ? JSON.parse(profile.experience) : (profile.experience || []);
      } catch(e) {
        expList = [];
      }
      
      let projList = [];
      try {
        projList = typeof profile.projects === "string" ? JSON.parse(profile.projects) : (profile.projects || []);
      } catch(e) {
        projList = [];
      }

      let eduList = [];
      try {
        eduList = typeof profile.education === "string" ? JSON.parse(profile.education) : (profile.education || []);
      } catch(e) {
        eduList = [];
      }

      let achList = [];
      try {
        achList = typeof profile.achievements === "string" ? JSON.parse(profile.achievements) : (profile.achievements || []);
      } catch(e) {
        achList = typeof profile.achievements === "string" ? profile.achievements.split("\n") : (profile.achievements || []);
      }

      setEditForm({
        name: profile.personal_info?.name || fullName || "",
        email: profile.personal_info?.email || email || "",
        phone: profile.personal_info?.phone || "",
        address: profile.personal_info?.location || "",
        summary: profile.personal_info?.summary || "",
        experienceList: expList,
        projectList: projList,
        educationList: eduList,
        certifications: profile.certifications || "",
        achievementsList: achList,
        languages: profile.languages || "",
        linkedin: profile.linkedin || "",
        github: profile.github || "",
        portfolio: profile.portfolio || ""
      });
    }
  }, [profile]);

  // Derived / Computed Properties
  const skillsList = skillsGraph?.skills 
    ? skillsGraph.skills.map((s: any) => typeof s === "string" ? s : s.name) 
    : (profile?.skills ? String(profile.skills).split(", ") : []);

  const keywordsList = improvements?.keyword_matching?.matched_keywords || (skillsList.slice(0, 8));
  const missingSkills = skillGaps?.missing_skills || [];
  const recommendedCourses = skillGaps?.learning_roadmap 
    ? skillGaps.learning_roadmap.map((item: any) => ({
        title: item.resources?.[0] || `Master ${item.skill}`,
        skills: [item.skill]
      }))
    : [];

  const strongestSkill = skillsList[0] || "Software Engineering";
  const improvementArea = improvements?.improvement_suggestions?.[0] || "Add quantifiable achievements in current role";
  const profileStrength = `${profile?.career_classification?.profile_strength || 75}%`;
  const recommendedStep = "Create your AI Job Agent to begin auto-discovery";

  const aiQualityScore = improvements ? Math.round((improvements.ats_score || 70) / 10) : 7;
  const aiQualityBreakdown = {
    grammar: improvements ? Math.round((improvements.content_score || 70) / 10) : 7,
    formatting: improvements ? Math.round((improvements.formatting_score || 75) / 10) : 8,
    readability: improvements ? Math.round((improvements.content_score || 68) / 10) : 7,
    project_quality: improvements ? Math.round((improvements.content_score || 72) / 10) : 7,
    achievement_quality: improvements ? Math.round((improvements.content_score || 65) / 10) : 6,
    structure: improvements ? Math.round((improvements.formatting_score || 78) / 10) : 8
  };

  const resumeVersions = versions.map((v: any, idx: number) => ({
    id: v.id,
    version: v.resume_url?.split("/").pop() || `Resume_v${versions.length - idx}`,
    date: new Date(v.uploaded_at).toLocaleDateString() + " " + new Date(v.uploaded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    url: v.resume_url,
    isLatest: idx === 0
  }));

  // Actions
  const triggerUpload = () => {
    fileInputRef.current?.click();
  };

  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const selectedFile = e.target.files[0];
    if (selectedFile.type !== "application/pdf" && !selectedFile.name.endsWith(".docx")) {
      setErrorMsg("Please upload a PDF or DOCX file only.");
      return;
    }

    setUploading(true);
    setUploadStep(1);
    setUploadProgress(10);
    setErrorMsg("");
    setSuccessMsg("");

    try {
      await apiService.uploadResume(selectedFile, fastMode);
      setSuccessMsg("Resume uploaded successfully! Ingesting...");
      setTimeout(() => setSuccessMsg(""), 3000);
      
      setTimeout(async () => {
        await loadIntelligence();
        setUploading(false);
      }, 1500);
    } catch (err: any) {
      setErrorMsg(err.message || "Resume upload failed.");
      setUploading(false);
    }
  };

  const handleActivateVersion = async (id: number) => {
    setLoading(true);
    try {
      const res = await fetch(`${getBackendBaseUrl()}/api/v1/candidates/resume/${id}/activate`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("token") || ""}`
        }
      });
      if (res.ok) {
        setSuccessMsg("Resume version activated.");
        setTimeout(() => setSuccessMsg(""), 3000);
        await loadIntelligence();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteResumeVersion = async (id: number) => {
    if (!confirm("Delete this resume version?")) return;
    try {
      await apiService.deleteResumeVersion(id);
      setSuccessMsg("Resume version deleted.");
      setTimeout(() => setSuccessMsg(""), 3000);
      await loadIntelligence();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to delete.");
    }
  };

  const handleCreateAgent = async () => {
    setAgentCreating(true);
    try {
      await apiService.createResumeAgent();
      setSuccessMsg("⚡ AI Job Agent successfully initialized for your profile! Re-routing to Job Agent...");
      setTimeout(() => {
        router.push("/candidate/job-agent");
      }, 2000);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to initialize agent.");
      setAgentCreating(false);
    }
  };

  const handlePreviewResume = (url: string) => {
    setPreviewUrl(url);
    setShowPreviewModal(true);
  };

  const handleDownloadResumeUrl = (url: string, filename: string) => {
    const link = document.createElement("a");
    link.href = `${getBackendBaseUrl()}${url}`;
    link.download = filename;
    link.target = "_blank";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const runAIAnalysis = async () => {
    setAnalysisLoading(true);
    try {
      await apiService.analyzeResume();
      await loadIntelligence();
      setSuccessMsg("AI Analysis refreshed successfully!");
      setTimeout(() => setSuccessMsg(""), 3000);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to analyze resume.");
    } finally {
      setAnalysisLoading(false);
    }
  };

  const handleImproveWithAI = () => {
    setActiveTab("improvements");
  };

  if (loading && !uploading) {
    return (
      <div className="flex-1 min-h-screen bg-slate-950 text-slate-100 p-6 md:p-8 flex items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="animate-spin text-violet-500 mx-auto" size={40} />
          <p className="text-sm font-semibold text-slate-400">Loading Career Intelligence Operating System...</p>
        </div>
      </div>
    );
  }

  if (versions.length === 0) {
    return (
      <div className="flex-1 min-h-screen bg-slate-950 text-slate-100 p-6 md:p-8 flex items-center justify-center font-sans">
        <div className="max-w-md w-full space-y-4">
          {errorMsg && <Alert variant="error">{errorMsg}</Alert>}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleResumeUpload}
            accept=".pdf,.docx"
            className="hidden"
          />
          <EmptyState
            title="No Resume Uploaded"
            description="Your resume is the entry point into the Career Intelligence Operating System. Upload it to analyze skills, generate career DNA, and map opportunities."
            icon={<FileText size={36} className="text-violet-500" />}
            action={
              <div className="flex flex-col items-center gap-3 w-full">
                <Button onClick={triggerUpload} className="w-full sm:w-auto mt-4 bg-violet-650 hover:bg-violet-750 text-white">
                  <Upload size={16} className="mr-2" />
                  Upload Resume / CV
                </Button>
                <label className="flex items-center gap-2 text-xs cursor-pointer mt-2 bg-white/5 border border-white/10 rounded-lg py-1.5 px-3 hover:bg-white/10 transition-colors">
                  <input
                    type="checkbox"
                    checked={fastMode}
                    onChange={(e) => setFastMode(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-900 text-violet-600 focus:ring-violet-500"
                  />
                  <span className="font-medium text-slate-350">⚡ Instant Mode (milliseconds fallback)</span>
                </label>
              </div>
            }
          />
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 min-h-screen bg-slate-950 text-slate-100 p-6 md:p-8 font-sans transition-all duration-300">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleResumeUpload}
        accept=".pdf,.docx"
        className="hidden"
      />

      {/* Uploading Progress Modal */}
      {uploading && (
        <Modal isOpen={uploading} onClose={() => {}} title="Analyzing Resume with AI Ingestion" className="max-w-md bg-slate-900 border border-slate-800">
          <div className="flex flex-col gap-6 py-2 text-slate-200">
            <div className="space-y-1 text-center">
              <span className="text-[10px] font-bold text-violet-400 uppercase tracking-wider">Career Intelligence Ingestion</span>
              <p className="text-xs text-slate-400 leading-relaxed">Extracting skills, career stage, opportunity tracks and resume improvements.</p>
            </div>
            <div className="space-y-3">
              {[
                { step: 1, label: "Uploading Document" },
                { step: 2, label: "Classifying Career Family (Gov vs Private)" },
                { step: 3, label: "Calculating Employability & DNA" },
                { step: 4, label: "Mapping Skill Graphs & Career Paths" },
                { step: 5, label: "Syncing Opportunity Matrix & ATS suggestions" }
              ].map((s) => (
                <div key={s.step} className="flex items-center gap-3.5">
                  <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold border transition-all ${
                    uploadStep > s.step ? "bg-emerald-500 border-emerald-500 text-white" : uploadStep === s.step ? "bg-violet-600 border-violet-600 text-white animate-pulse" : "border-slate-800 text-slate-500"
                  }`}>
                    {uploadStep > s.step ? <Check size={12} strokeWidth={3} /> : s.step}
                  </div>
                  <span className={`text-xs font-semibold ${uploadStep === s.step ? "text-slate-100" : uploadStep > s.step ? "text-slate-400 line-through opacity-70" : "text-slate-500"}`}>{s.label}</span>
                </div>
              ))}
            </div>
            <div className="space-y-2 mt-2">
              <div className="flex justify-between items-center text-xs font-semibold">
                <span className="text-slate-400">Pipeline Ingestion</span>
                <span className="text-slate-100">{uploadProgress}%</span>
              </div>
              <div className="w-full bg-slate-850 h-2 rounded-full overflow-hidden">
                <div className="bg-violet-500 h-full transition-all duration-300" style={{ width: `${uploadProgress}%` }} />
              </div>
            </div>
          </div>
        </Modal>
      )}

      {/* Main Container */}
      <div className="max-w-7xl mx-auto space-y-6">
        {successMsg && <Alert variant="success" className="bg-emerald-950/40 border border-emerald-800 text-emerald-300">{successMsg}</Alert>}
        {errorMsg && <Alert variant="error" className="bg-red-950/40 border border-red-800 text-red-300">{errorMsg}</Alert>}

        {/* Header Banner */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 bg-slate-900/60 backdrop-blur-md border border-slate-850 rounded-3xl p-6 shadow-xl">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-650 flex items-center justify-center text-white shadow-lg">
              <Sparkles size={22} className="animate-pulse" />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
                Career Intelligence OS
                <Badge className="bg-violet-500/20 text-violet-400 border border-violet-800/50 py-0.5 text-[9px] font-black uppercase tracking-wider">v2.0 Active</Badge>
              </h1>
              <p className="text-slate-400 mt-1 text-xs font-medium">Everything starts from Resume Intelligence. Managed by principal systems architects.</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button variant="outline" size="sm" onClick={triggerUpload} className="bg-slate-850 border-slate-750 text-slate-205 hover:bg-slate-800 text-xs">
              <Upload size={14} className="mr-1.5" />
              Upload New Version
            </Button>
            <Button onClick={handleCreateAgent} disabled={agentCreating} className="bg-gradient-to-r from-violet-600 to-indigo-650 hover:from-violet-750 hover:to-indigo-750 text-white font-bold text-xs shadow-lg shadow-violet-500/20">
              {agentCreating ? <Loader2 size={14} className="animate-spin mr-1.5" /> : <Zap size={14} className="mr-1.5 fill-current" />}
              Create AI Job Agent
            </Button>
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="bg-slate-900/40 border-slate-850 p-4">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Career Family</span>
            <span className="text-lg font-black text-slate-100 mt-1 block">
              {profile?.career_classification?.career_family || "Engineering"}
            </span>
          </Card>
          <Card className="bg-slate-900/40 border-slate-850 p-4">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Profile Strength</span>
            <div className="flex items-center gap-2 mt-1">
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div className="bg-violet-500 h-full" style={{ width: `${profile?.career_classification?.profile_strength || 75}%` }} />
              </div>
              <span className="text-sm font-black text-slate-100">{profile?.career_classification?.profile_strength || 75}%</span>
            </div>
          </Card>
          <Card className="bg-slate-900/40 border-slate-850 p-4">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Employability Score</span>
            <div className="flex items-center gap-2 mt-1">
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div className="bg-emerald-500 h-full" style={{ width: `${profile?.career_classification?.employability_score || 80}%` }} />
              </div>
              <span className="text-sm font-black text-slate-100">{profile?.career_classification?.employability_score || 80}%</span>
            </div>
          </Card>
          <Card className="bg-slate-900/40 border-slate-850 p-4">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Experience Level</span>
            <span className="text-lg font-black text-slate-100 mt-1 block">
              {profile?.career_classification?.experience_level || "Mid-Level"}
            </span>
          </Card>
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          
          {/* Column 1: Left Sidebar (1 col) */}
          <div className="lg:col-span-1 space-y-4">
            <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-3 shadow-xl">
              <span className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider px-3 py-2 block">Intelligence Tabs</span>
              <div className="space-y-1">
                {[
                  { id: "overview", label: "Candidate Profile", icon: LayoutDashboard },
                  { id: "dna", label: "Career DNA", icon: Dna },
                  { id: "skills", label: "Skill Graph Mapping", icon: Code },
                  { id: "roles", label: "Role Intelligence", icon: Compass },
                  { id: "paths", label: "Career Progress Graph", icon: Route },
                  { id: "opportunities", label: "Opportunity Engine", icon: ShieldCheck },
                  { id: "improvements", label: "Resume improvements", icon: FileCheck }
                ].map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-bold transition-all text-left ${
                        isActive 
                          ? "bg-violet-600/20 text-violet-300 border-l-4 border-violet-500" 
                          : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
                      }`}
                    >
                      <Icon size={16} />
                      {tab.label}
                    </button>
                  );
                })}
              </div>
              <div className="border-t border-slate-800/60 mt-3 pt-3 px-1">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => setIsEditOpen(true)} 
                  className="w-full text-[11px] h-8 bg-slate-900 border-slate-800 hover:bg-slate-800 text-slate-350"
                >
                  <Eye size={12} className="mr-1" />
                  View Parsed Raw Profile
                </Button>
              </div>
            </Card>

            <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-4 shadow-xl space-y-4">
              <div>
                <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2.5 block">Top Skills</h3>
                <div className="flex flex-wrap gap-1.5">
                  {skillsList.slice(0, 10).map((skill: string, idx: number) => (
                    <span key={idx} className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-800 border border-slate-750 text-slate-300">
                      {skill}
                    </span>
                  ))}
                  {skillsList.length === 0 && (
                    <span className="text-xs text-slate-500 italic">No skills extracted.</span>
                  )}
                </div>
              </div>

              <div className="border-t border-slate-850 pt-3">
                <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2.5 block">Key Keywords</h3>
                <div className="grid grid-cols-2 gap-2 text-[10px] font-bold text-slate-400">
                  {keywordsList.slice(0, 6).map((kw: string, idx: number) => (
                    <div key={idx} className="flex items-center gap-1.5">
                      <Check size={10} className="text-emerald-500 shrink-0" />
                      <span className="truncate">{kw}</span>
                    </div>
                  ))}
                  {keywordsList.length === 0 && (
                    <span className="col-span-2 text-xs text-slate-500 italic">No keywords.</span>
                  )}
                </div>
              </div>
            </Card>
          </div>

          {/* Column 2 & 3: Middle Workspace (2 cols) */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* OVERVIEW TAB */}
            {activeTab === "overview" && (
              <div className="space-y-6">
                <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-6 shadow-xl space-y-6">
                  <div className="flex items-center gap-3 border-b border-slate-850 pb-4">
                    <div className="w-10 h-10 rounded-2xl bg-violet-500/10 text-violet-400 flex items-center justify-center shrink-0 border border-violet-500/20">
                      <User size={20} />
                    </div>
                    <div>
                      <h3 className="text-lg font-black text-white">Candidate Profile</h3>
                      <p className="text-xs text-slate-400">Personal information and professional background details.</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Name</span>
                      <p className="text-xs font-semibold text-slate-200 bg-slate-950/40 p-3 rounded-xl border border-slate-850">{profile?.personal_info?.name || fullName || "Not specified"}</p>
                    </div>
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Email</span>
                      <p className="text-xs font-semibold text-slate-200 bg-slate-950/40 p-3 rounded-xl border border-slate-850">{profile?.personal_info?.email || email || "Not specified"}</p>
                    </div>
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Phone</span>
                      <p className="text-xs font-semibold text-slate-200 bg-slate-950/40 p-3 rounded-xl border border-slate-850">{profile?.personal_info?.phone || "Not specified"}</p>
                    </div>
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Location</span>
                      <p className="text-xs font-semibold text-slate-200 bg-slate-950/40 p-3 rounded-xl border border-slate-850">{profile?.personal_info?.location || "Remote"}</p>
                    </div>
                  </div>

                  {profile?.personal_info?.summary && (
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Professional Summary</span>
                      <p className="text-xs font-medium text-slate-300 leading-relaxed bg-slate-950/40 p-4 rounded-xl border border-slate-850 whitespace-pre-wrap">{profile.personal_info.summary}</p>
                    </div>
                  )}
                </Card>

                {/* AI Skills Gap Card */}
                <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-6 shadow-xl space-y-4">
                  <div className="flex items-center gap-3 border-b border-slate-850 pb-3">
                    <div className="w-9 h-9 rounded-xl bg-violet-600/10 text-violet-400 flex items-center justify-center shrink-0 border border-violet-650/20">
                      <Sparkles size={18} className="animate-pulse" />
                    </div>
                    <div>
                      <h3 className="text-base font-black text-white">AI Skill Gap & Recommendations</h3>
                      <p className="text-xs text-slate-400">Target roles upskilling priority index.</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-3">
                      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Identified Missing Skills</span>
                      {missingSkills.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {missingSkills.map((skill: any, idx: number) => (
                            <span key={idx} className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-[10px] font-bold">
                              <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse mr-1" />
                              {skill}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-400 font-bold flex items-center gap-2">
                          <CheckCircle2 size={14} />
                          No critical missing skills.
                        </div>
                      )}
                    </div>

                    <div className="space-y-3">
                      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Recommended Upskill Actions</span>
                      <div className="space-y-2">
                        {recommendedCourses.length > 0 ? (
                          recommendedCourses.slice(0, 3).map((course: any, idx: number) => (
                            <div key={idx} className="p-2.5 rounded-xl border border-slate-800 bg-slate-950/20 flex items-center justify-between gap-3">
                              <div className="min-w-0">
                                <span className="text-[11px] font-bold text-slate-200 block truncate">{course.title}</span>
                                <span className="text-[9px] text-slate-400 mt-0.5 block font-semibold">Focus: {course.skills.join(", ")}</span>
                              </div>
                              <Link href="/candidate/skill-lab">
                                <Button size="xs" variant="outline" className="text-[9px] py-1 h-auto font-bold bg-slate-900 border-slate-800 hover:bg-slate-850">
                                  Learn
                                </Button>
                              </Link>
                            </div>
                          ))
                        ) : (
                          <p className="text-xs text-slate-500 italic">No upskilling courses suggested.</p>
                        )}
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
            )}

            {/* CAREER DNA TAB */}
            {activeTab === "dna" && (
              <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-6 shadow-xl space-y-6">
                <div className="flex items-center gap-3 border-b border-slate-850 pb-4">
                  <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center shrink-0 border border-indigo-500/20">
                    <Dna size={20} className="animate-pulse" />
                  </div>
                  <div>
                    <h3 className="text-lg font-black text-white">Career DNA Analysis</h3>
                    <p className="text-xs text-slate-400">Archetype, behavioral traits, and leadership dynamics.</p>
                  </div>
                </div>

                <div className="p-5 rounded-2xl bg-gradient-to-r from-violet-650/25 to-indigo-650/25 border border-violet-850/40 space-y-3">
                  <span className="text-[10px] font-bold text-violet-400 uppercase tracking-wider block">Career Archetype</span>
                  <div className="flex items-center justify-between gap-4">
                    <h4 className="text-xl font-black text-white">{careerDna?.personality || "Builder"}</h4>
                    <Badge className="bg-violet-500/25 text-violet-300 border border-violet-550/40 font-bold text-[10px] px-2 py-0.5">High Potential</Badge>
                  </div>
                  <p className="text-xs text-slate-350 leading-relaxed font-medium">
                    This archetype describes candidates who focus on execution, engineering architecture, and scaling robust services. They excel in solving logical constraints and building systems.
                  </p>
                </div>

                <div className="space-y-4">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Core Career Traits</span>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-4 rounded-xl border border-slate-850 bg-slate-950/20 space-y-2">
                      <span className="text-[10px] font-bold text-slate-400 block">Working Style</span>
                      <p className="text-xs text-slate-300 font-semibold leading-relaxed">{careerDna?.traits?.working_style || "Autonomous / Direct Execution"}</p>
                    </div>
                    <div className="p-4 rounded-xl border border-slate-850 bg-slate-950/20 space-y-2">
                      <span className="text-[10px] font-bold text-slate-400 block">Growth Speed</span>
                      <p className="text-xs text-slate-300 font-semibold leading-relaxed">{careerDna?.traits?.growth_potential || "Fast / Adaptive Learner"}</p>
                    </div>
                    <div className="p-4 rounded-xl border border-slate-850 bg-slate-950/20 space-y-2">
                      <span className="text-[10px] font-bold text-slate-400 block">Leadership Archetype</span>
                      <p className="text-xs text-slate-300 font-semibold leading-relaxed">{careerDna?.traits?.leadership_potential || "System Thinker & Lead Mentor"}</p>
                    </div>
                  </div>
                </div>
              </Card>
            )}

            {/* SKILLS TAB */}
            {activeTab === "skills" && (
              <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-6 shadow-xl space-y-6">
                <div className="flex items-center gap-3 border-b border-slate-850 pb-4">
                  <div className="w-10 h-10 rounded-2xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center shrink-0 border border-emerald-500/20">
                    <Code size={20} />
                  </div>
                  <div>
                    <h3 className="text-lg font-black text-white">Skill Graph Mapping</h3>
                    <p className="text-xs text-slate-400">Structured layout of technology node associations.</p>
                  </div>
                </div>

                <div className="bg-slate-950/50 border border-slate-850 rounded-2xl p-6 min-h-[300px] flex flex-col justify-center items-center relative overflow-hidden">
                  {skillsGraph?.skills && skillsGraph.skills.length > 0 ? (
                    <div className="w-full space-y-6">
                      <div className="h-44 w-full relative flex items-center justify-center bg-slate-950 border border-slate-850/60 rounded-xl p-4">
                        <svg className="absolute inset-0 w-full h-full">
                          <line x1="20%" y1="50%" x2="50%" y2="25%" stroke="#6366f1" strokeWidth="2" strokeDasharray="3,3" className="opacity-60" />
                          <line x1="20%" y1="50%" x2="50%" y2="75%" stroke="#6366f1" strokeWidth="2" strokeDasharray="3,3" className="opacity-60" />
                          <line x1="50%" y1="25%" x2="80%" y2="50%" stroke="#4f46e5" strokeWidth="2" className="opacity-80" />
                          <line x1="50%" y1="75%" x2="80%" y2="50%" stroke="#4f46e5" strokeWidth="2" className="opacity-80" />
                        </svg>
                        
                        <div className="absolute left-[10%] top-[40%] bg-violet-600/30 text-violet-300 border border-violet-500 px-3 py-1.5 rounded-lg text-xs font-black shadow-md">
                          Core Experience
                        </div>
                        <div className="absolute left-[40%] top-[15%] bg-indigo-650/30 text-indigo-300 border border-indigo-500 px-3 py-1.5 rounded-lg text-xs font-black shadow-md">
                          {skillsGraph.skills[0]?.name || skillsList[0] || "Python"}
                        </div>
                        <div className="absolute left-[40%] top-[65%] bg-teal-650/30 text-teal-300 border border-teal-500 px-3 py-1.5 rounded-lg text-xs font-black shadow-md">
                          {skillsGraph.skills[1]?.name || skillsList[1] || "Database"}
                        </div>
                        <div className="absolute right-[10%] top-[40%] bg-blue-650/30 text-blue-300 border border-blue-500 px-3 py-1.5 rounded-lg text-xs font-black shadow-md">
                          Fullstack OS
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {skillsGraph.skills.map((skill: any, idx: number) => {
                          const name = typeof skill === "string" ? skill : skill.name;
                          const score = typeof skill === "string" ? (85 - idx * 5) : (skill.confidence || 80);
                          return (
                            <div key={idx} className="p-3.5 rounded-xl bg-slate-900 border border-slate-850 space-y-2">
                              <div className="flex justify-between items-center text-xs font-bold">
                                <span className="text-slate-200">{name}</span>
                                <span className="text-violet-400">{score}% Confidence</span>
                              </div>
                              <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
                                <div className="bg-gradient-to-r from-violet-500 to-indigo-500 h-full" style={{ width: `${score}%` }} />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center space-y-2">
                      <Code size={36} className="text-slate-600 mx-auto" />
                      <p className="text-xs text-slate-500 font-semibold">No structured skills graph found. Upload your resume to map taxonomy.</p>
                    </div>
                  )}
                </div>
              </Card>
            )}

            {/* ROLE INTELLIGENCE TAB */}
            {activeTab === "roles" && (
              <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-6 shadow-xl space-y-6">
                <div className="flex items-center gap-3 border-b border-slate-850 pb-4">
                  <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center shrink-0 border border-indigo-500/20">
                    <Compass size={20} />
                  </div>
                  <div>
                    <h3 className="text-lg font-black text-white">Role Discovery Engine</h3>
                    <p className="text-xs text-slate-400">AI generated roles matching your Career DNA.</p>
                  </div>
                </div>

                <div className="space-y-6">
                  {[
                    { title: "Core Focus Roles", key: "core", desc: "Highest match confidence based on direct experiences." },
                    { title: "Related Roles", key: "related", desc: "Strong match based on transferable engineering skills." },
                    { title: "Adjacent / Future Roles", key: "adjacent", desc: "Long-term career pathway suggestions." }
                  ].map((group) => {
                    const groupRoles = roles?.[group.key] || [];
                    return (
                      <div key={group.key} className="space-y-3">
                        <div>
                          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">{group.title}</h4>
                          <p className="text-[10px] text-slate-500 mt-0.5">{group.desc}</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {groupRoles.length > 0 ? (
                            groupRoles.map((r: any, idx: number) => (
                              <div key={idx} className="p-3.5 rounded-xl bg-slate-950/40 border border-slate-850 flex items-center justify-between gap-4">
                                <span className="text-xs font-bold text-slate-205">{r.role}</span>
                                <div className="flex items-center gap-2 shrink-0">
                                  <span className="text-[10px] font-bold text-violet-400">{r.confidence}% Match</span>
                                  <div className="w-8 h-8 rounded-lg bg-violet-500/10 flex items-center justify-center border border-violet-550/20">
                                    <TrendingUp size={12} className="text-violet-400" />
                                  </div>
                                </div>
                              </div>
                            ))
                          ) : (
                            <div className="col-span-2 p-4 text-center rounded-xl border border-dashed border-slate-800 text-[11px] text-slate-500 font-medium">
                              No roles discovered in this category.
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Card>
            )}

            {/* CAREER PATHS TAB */}
            {activeTab === "paths" && (
              <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-6 shadow-xl space-y-6">
                <div className="flex items-center gap-3 border-b border-slate-850 pb-4">
                  <div className="w-10 h-10 rounded-2xl bg-violet-500/10 text-violet-400 flex items-center justify-center shrink-0 border border-violet-500/20">
                    <Route size={20} />
                  </div>
                  <div>
                    <h3 className="text-lg font-black text-white">Career Path Progression</h3>
                    <p className="text-xs text-slate-400">AI generated career roadmaps and promotion milestones.</p>
                  </div>
                </div>

                <div className="space-y-6">
                  {careerPaths && careerPaths.length > 0 ? (
                    careerPaths.map((path, idx) => (
                      <div key={idx} className="p-5 rounded-2xl border border-slate-850 bg-slate-950/20 space-y-4">
                        <div className="flex items-center justify-between gap-4">
                          <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider">{path.path_name} Roadmap</h4>
                          <Badge className="bg-indigo-500/20 text-indigo-400 border border-indigo-850/40 text-[9px] font-black uppercase">Suggested Path</Badge>
                        </div>

                        <div className="relative border-l border-slate-800 ml-2.5 pl-6 space-y-6 py-2">
                          {path.steps?.map((step: string, sIdx: number) => (
                            <div key={sIdx} className="relative">
                              <span className="absolute left-[-29px] top-1 flex h-2.5 w-2.5 items-center justify-center rounded-full bg-violet-500 border border-violet-500 shadow-sm" />
                              <div className="space-y-1">
                                <h5 className="text-xs font-bold text-slate-202">{step}</h5>
                                <p className="text-[10px] text-slate-500 font-semibold">
                                  Milestone: {path.milestones?.[sIdx] || "Acquire leadership duties and scale service frameworks"}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-10 space-y-2 border border-dashed border-slate-800 rounded-2xl">
                      <Route size={36} className="text-slate-600 mx-auto" />
                      <p className="text-xs text-slate-500 font-semibold">No career path projections loaded. Upload resume to generate.</p>
                    </div>
                  )}
                </div>
              </Card>
            )}

            {/* OPPORTUNITIES TAB */}
            {activeTab === "opportunities" && (
              <div className="space-y-6">
                
                {/* Score Dials Card */}
                <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-6 shadow-xl space-y-6">
                  <div className="flex items-center gap-3 border-b border-slate-850 pb-4">
                    <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center shrink-0 border border-indigo-500/20">
                      <ShieldCheck size={20} />
                    </div>
                    <div>
                      <h3 className="text-lg font-black text-white">Opportunity Intelligence</h3>
                      <p className="text-xs text-slate-400">Match score matrices across government, remote, and private opportunities.</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    {[
                      { label: "Government", score: opportunities?.opportunity_scores?.government_score || 45, color: "stroke-amber-500", text: "text-amber-400" },
                      { label: "Private Core", score: opportunities?.opportunity_scores?.private_score || 85, color: "stroke-violet-500", text: "text-violet-400" },
                      { label: "Remote Fit", score: opportunities?.opportunity_scores?.remote_score || 80, color: "stroke-emerald-500", text: "text-emerald-400" },
                      { label: "International", score: opportunities?.opportunity_scores?.international_score || 65, color: "stroke-blue-500", text: "text-blue-400" },
                      { label: "Leadership", score: opportunities?.opportunity_scores?.leadership_potential_score || 70, color: "stroke-purple-500", text: "text-purple-400" }
                    ].map((dial, idx) => (
                      <div key={idx} className="flex flex-col items-center p-3 rounded-xl bg-slate-950/40 border border-slate-850/60">
                        <div className="relative w-16 h-16 flex items-center justify-center">
                          <svg className="w-full h-full transform -rotate-90">
                            <circle cx="32" cy="32" r="26" fill="none" strokeWidth="4" className="text-slate-800" stroke="currentColor" />
                            <circle cx="32" cy="32" r="26" fill="none" strokeWidth="4" strokeDasharray={2*Math.PI*26} strokeDashoffset={2*Math.PI*26 - (dial.score / 100) * (2*Math.PI*26)} strokeLinecap="round" className={dial.color} />
                          </svg>
                          <span className="absolute text-xs font-black text-white">{dial.score}%</span>
                        </div>
                        <span className="text-[10px] font-bold text-slate-400 mt-2 block">{dial.label}</span>
                      </div>
                    ))}
                  </div>
                </Card>

                {/* Exam Eligibility Card */}
                <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-6 shadow-xl space-y-6">
                  <div className="border-b border-slate-850 pb-3 flex justify-between items-center">
                    <div>
                      <h4 className="text-base font-black text-white">Government Exam Eligibility & Age Matrix</h4>
                      <p className="text-[10px] text-slate-400 mt-0.5">Eligibility check matching your age, education and attempt logs.</p>
                    </div>
                    <Badge className="bg-amber-500/10 text-amber-400 border border-amber-850/40 text-[9px] font-bold">Government Pipeline</Badge>
                  </div>

                  <div className="space-y-4">
                    {opportunities?.eligible_exams && opportunities.eligible_exams.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {opportunities.eligible_exams.map((exam: any, idx: number) => (
                          <div key={idx} className="p-4 rounded-xl border border-slate-850 bg-slate-950/30 space-y-2">
                            <div className="flex justify-between items-start">
                              <span className="text-xs font-black text-slate-200">{exam.exam_name || exam.name || "Exam Title"}</span>
                              <Badge className={`text-[9px] font-black px-2 py-0.5 ${
                                String(exam.status).toLowerCase().includes("ineligible") ? "bg-red-500/10 text-red-400 border-red-500/20" : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                              } border`}>
                                {exam.status || "Eligible"}
                              </Badge>
                            </div>
                            <div className="space-y-1 text-[10px] text-slate-400 font-semibold">
                              <p>Age Criteria: {exam.age_status || "Pass"}</p>
                              <p>Edu Criteria: {exam.education_status || "Pass"}</p>
                              <p>Remaining Attempts: {exam.attempts_left ?? "N/A"}</p>
                              {exam.promotion_path && <p className="text-violet-400 mt-1 block">Promotion: {exam.promotion_path}</p>}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-6 text-xs text-slate-550 border border-dashed border-slate-800 rounded-xl font-semibold">
                        No government exam eligibility calculated. Upload details to check.
                      </div>
                    )}
                  </div>
                </Card>

                {/* Risks Card */}
                <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-6 shadow-xl space-y-4">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Career Risk Analysis</span>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                    {[
                      { label: "Demand Risk", value: opportunities?.risk_analysis?.demand_risk || "Low", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
                      { label: "Automation Risk", value: opportunities?.risk_analysis?.automation_risk || "Low", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
                      { label: "Market Competition", value: opportunities?.risk_analysis?.market_competition || "High", color: "text-red-400 bg-red-500/10 border-red-500/20" },
                      { label: "Future Growth", value: opportunities?.risk_analysis?.future_growth || "High", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" },
                      { label: "Salary Stability", value: opportunities?.risk_analysis?.salary_growth || "Stable", color: "text-violet-400 bg-violet-500/10 border-violet-500/20" }
                    ].map((risk, idx) => (
                      <div key={idx} className="p-3 rounded-lg border border-slate-850 bg-slate-950/20 text-center space-y-1">
                        <span className="text-[9px] font-bold text-slate-400 block">{risk.label}</span>
                        <Badge className={`text-[10px] font-black border ${risk.color} mt-1`}>{risk.value}</Badge>
                      </div>
                    ))}
                  </div>
                </Card>

                {/* Top Opportunities Table */}
                <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-6 shadow-xl space-y-4">
                  <div className="border-b border-slate-850 pb-3">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Top 100 Ranked Match Career Tracks</span>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs font-semibold">
                      <thead>
                        <tr className="border-b border-slate-850 text-slate-400 text-[10px] uppercase">
                          <th className="py-2.5 font-bold">Role/Exam Track</th>
                          <th className="py-2.5 font-bold">Category</th>
                          <th className="py-2.5 font-bold text-center">Confidence</th>
                          <th className="py-2.5 font-bold text-center">Growth</th>
                          <th className="py-2.5 font-bold text-right">Potential Pay</th>
                        </tr>
                      </thead>
                      <tbody>
                        {opportunities?.top_opportunities && opportunities.top_opportunities.length > 0 ? (
                          opportunities.top_opportunities.map((opp: any, idx: number) => (
                            <tr key={idx} className="border-b border-slate-850/60 hover:bg-slate-900/40 text-slate-300">
                              <td className="py-3 font-bold text-slate-200">{opp.role_title}</td>
                              <td className="py-3 text-[10px] font-bold text-slate-400">{opp.category}</td>
                              <td className="py-3 text-center text-violet-400 font-black">{opp.confidence_score}%</td>
                              <td className="py-3 text-center text-emerald-400 font-black">{opp.growth_score}%</td>
                              <td className="py-3 text-right font-black text-slate-200">{opp.salary_potential || "N/A"}</td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={5} className="py-6 text-center text-slate-500 italic font-semibold">No opportunity careers matching.</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </div>
            )}

            {/* IMPROVEMENTS TAB */}
            {activeTab === "improvements" && (
              <div className="space-y-6">
                <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-6 shadow-xl space-y-6">
                  <div className="flex items-center gap-3 border-b border-slate-850 pb-4">
                    <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center shrink-0 border border-indigo-500/20">
                      <FileCheck size={20} />
                    </div>
                    <div>
                      <h3 className="text-lg font-black text-white">ATS Improvements & Scores</h3>
                      <p className="text-xs text-slate-400">Score metrics checking for grammar, keyword matches, achievements and layout formats.</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {[
                      { label: "Overall ATS", score: improvements?.ats_score || 70, color: "text-violet-400" },
                      { label: "Grammar & Spelling", score: improvements?.formatting_score || 75, color: "text-indigo-400" },
                      { label: "Content Quality", score: improvements?.content_score || 68, color: "text-blue-400" },
                      { label: "Keyword Matching", score: improvements?.keyword_score || 70, color: "text-teal-400" }
                    ].map((s, idx) => (
                      <div key={idx} className="p-4 rounded-xl border border-slate-850 bg-slate-950/20 text-center space-y-2">
                        <span className="text-[10px] font-bold text-slate-400 block">{s.label}</span>
                        <span className={`text-2xl font-black block ${s.color}`}>{s.score}<span className="text-xs text-slate-500">/100</span></span>
                      </div>
                    ))}
                  </div>
                </Card>

                <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-6 shadow-xl space-y-4">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">AI Resume Improvement Suggestions</span>
                  <div className="space-y-3">
                    {improvements?.improvement_suggestions && improvements.improvement_suggestions.length > 0 ? (
                      improvements.improvement_suggestions.map((suggestion: string, idx: number) => (
                        <div key={idx} className="flex gap-2.5 items-start p-3.5 rounded-xl border border-slate-850 bg-slate-950/30 text-xs font-semibold text-slate-300">
                          <AlertTriangle size={14} className="text-amber-500 mt-0.5 shrink-0" />
                          <span className="leading-relaxed">{suggestion}</span>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-slate-500 italic">No recommendations calculated.</p>
                    )}
                  </div>
                </Card>

                <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-6 shadow-xl space-y-4">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Quantitative Achievement Rewrites (Before vs After)</span>
                  <div className="space-y-4">
                    {improvements?.achievement_suggestions && improvements.achievement_suggestions.length > 0 ? (
                      improvements.achievement_suggestions.map((sugg: any, idx: number) => (
                        <div key={idx} className="grid grid-cols-1 md:grid-cols-2 gap-4 border-b border-slate-850/60 pb-4 last:border-b-0 last:pb-0">
                          <div className="p-3.5 rounded-xl bg-red-500/5 border border-red-500/10 space-y-1">
                            <span className="text-[9px] font-black text-red-400 uppercase tracking-wider">Before (Vague description)</span>
                            <p className="text-xs text-slate-400 font-medium italic">"{sugg.before || sugg.original || sugg}"</p>
                          </div>
                          <div className="p-3.5 rounded-xl bg-emerald-500/5 border border-emerald-500/10 space-y-1">
                            <span className="text-[9px] font-black text-emerald-400 uppercase tracking-wider">Suggested AI Rewrite (Impact-driven)</span>
                            <p className="text-xs text-slate-200 font-semibold">"{sugg.after || sugg.rewritten || sugg}"</p>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-slate-500 italic">No specific achievements suggestions computed.</p>
                    )}
                  </div>
                </Card>
              </div>
            )}

          </div>

          {/* Column 4: Right Sidebar (1 col) */}
          <div className="lg:col-span-1 space-y-6">
            
            {/* AI Insights Card */}
            <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-5 shadow-xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-850 pb-3">
                <h3 className="text-sm font-black text-white">AI Career Insights</h3>
              </div>

              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-teal-500/10 text-teal-400 flex items-center justify-center shrink-0 border border-teal-550/20">
                    <Code size={14} />
                  </div>
                  <div>
                    <span className="text-[9px] font-bold text-slate-500 block">Strongest Competency</span>
                    <span className="text-xs font-black text-slate-200 mt-0.5 block truncate">{strongestSkill}</span>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center shrink-0 border border-amber-550/20">
                    <TrendingUp size={14} />
                  </div>
                  <div>
                    <span className="text-[9px] font-bold text-slate-500 block">Top Improvement Area</span>
                    <span className="text-xs font-black text-slate-200 mt-0.5 block line-clamp-2 leading-tight">{improvementArea}</span>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center shrink-0 border border-purple-550/20">
                    <ShieldCheck size={14} />
                  </div>
                  <div>
                    <span className="text-[9px] font-bold text-slate-500 block">Profile Strength Score</span>
                    <span className="text-xs font-black text-slate-200 mt-0.5 block">{profileStrength}</span>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center shrink-0 border border-blue-550/20">
                    <FileText size={14} />
                  </div>
                  <div>
                    <span className="text-[9px] font-bold text-slate-500 block">Next Action Step</span>
                    <span className="text-xs font-black text-slate-200 mt-0.5 block leading-tight">{recommendedStep}</span>
                  </div>
                </div>
              </div>
            </Card>

            {/* AI Quality Score Card */}
            <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-5 shadow-xl space-y-6">
              <div className="flex items-center justify-between border-b border-slate-850 pb-3">
                <h3 className="text-sm font-black text-white">ATS Quality Rating</h3>
                <button 
                  onClick={runAIAnalysis}
                  disabled={analysisLoading}
                  className="text-xs font-bold text-violet-400 hover:text-violet-300 hover:underline cursor-pointer disabled:opacity-50"
                >
                  {analysisLoading ? "Running..." : "Analyze"}
                </button>
              </div>

              <div className="flex items-center gap-6 justify-between">
                <div className="flex flex-col items-center shrink-0">
                  <div className="relative flex items-center justify-center">
                    <svg width="74" height="74" className="transform -rotate-90">
                      <circle cx="37" cy="37" r="32" fill="none" strokeWidth="4" className="text-slate-800" stroke="currentColor" />
                      <circle cx="37" cy="37" r="32" fill="none" strokeWidth="4" strokeDasharray={2 * Math.PI * 32} strokeDashoffset={2 * Math.PI * 32 - (aiQualityScore * 10 / 100) * (2 * Math.PI * 32)} strokeLinecap="round" stroke="#8b5cf6" className="transition-all duration-700 ease-out" />
                    </svg>
                    <div className="absolute flex flex-col items-center">
                      <span className="text-base font-black text-white">{aiQualityScore}</span>
                      <span className="text-[8px] font-bold text-slate-500">/10</span>
                    </div>
                  </div>
                  <span className="text-[9px] font-bold text-violet-400 mt-2 uppercase tracking-wide">
                    {skillsList.length === 0 ? "N/A" : (aiQualityScore >= 8 ? "Excellent" : (aiQualityScore >= 6 ? "Good" : "Needs Work"))}
                  </span>
                </div>

                <div className="flex-1 space-y-1.5 text-[10px] font-bold text-slate-400 min-w-0">
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-slate-500">Grammar</span>
                    <span>{skillsList.length === 0 ? 0 : aiQualityBreakdown.grammar}/10</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-slate-500">Format</span>
                    <span>{skillsList.length === 0 ? 0 : aiQualityBreakdown.formatting}/10</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-slate-500">Readability</span>
                    <span>{skillsList.length === 0 ? 0 : aiQualityBreakdown.readability}/10</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-slate-500">Structure</span>
                    <span>{skillsList.length === 0 ? 0 : aiQualityBreakdown.structure}/10</span>
                  </div>
                </div>
              </div>

              <button 
                onClick={handleImproveWithAI}
                className="w-full py-2 rounded-xl border border-violet-800 bg-violet-950/20 text-violet-300 hover:bg-violet-950/40 text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-sm"
              >
                <Sparkles size={12} className="animate-pulse" />
                <span>Improve with AI</span>
              </button>
            </Card>

            {/* Resume Versions Card */}
            <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-5 shadow-xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-850 pb-3">
                <h3 className="text-sm font-black text-white">Versions History</h3>
              </div>

              <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1 scrollbar-thin">
                {resumeVersions.map((ver, idx) => (
                  <div key={idx} className="p-2.5 rounded-xl border border-slate-850 bg-slate-950/30 flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-7 h-7 rounded bg-slate-900 border border-slate-800 text-slate-400 flex items-center justify-center shrink-0">
                        <FileText size={14} />
                      </div>
                      <div className="min-w-0">
                        <span className="text-[11px] font-bold text-slate-200 flex items-center gap-1 truncate">
                          {ver.version}
                          {ver.isLatest && (
                            <span className="text-[8px] font-bold px-1 bg-violet-500/20 text-violet-400 rounded border border-violet-850/40 shrink-0">
                              Active
                            </span>
                          )}
                        </span>
                        <span className="text-[8px] text-slate-500 font-semibold block mt-0.5">{ver.date}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <button 
                        onClick={() => handlePreviewResume(ver.url)}
                        className="p-1 rounded bg-slate-900 border border-slate-800 text-slate-450 hover:text-slate-200 cursor-pointer"
                        title="Preview"
                      >
                        <Eye size={11} />
                      </button>
                      <button 
                        onClick={() => handleDownloadResumeUrl(ver.url, ver.version)}
                        className="p-1 rounded bg-slate-900 border border-slate-800 text-slate-450 hover:text-slate-200 cursor-pointer"
                        title="Download"
                      >
                        <Download size={11} />
                      </button>
                      <button 
                        onClick={() => handleDeleteResumeVersion(ver.id)}
                        className="p-1 rounded bg-slate-900 border border-slate-800 text-slate-455 hover:text-red-400 cursor-pointer"
                        title="Delete"
                      >
                        <Trash2 size={11} />
                      </button>
                    </div>
                  </div>
                ))}

                {resumeVersions.length === 0 && (
                  <div className="text-center py-6 text-xs text-slate-555 italic font-semibold">
                    No versions.
                  </div>
                )}
              </div>

              <div className="flex flex-col gap-2 w-full pt-1">
                <button 
                  onClick={triggerUpload}
                  disabled={uploading}
                  className="w-full py-2.5 rounded-xl border border-slate-800 hover:bg-slate-800 text-slate-300 text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-sm disabled:opacity-50"
                >
                  {uploading ? (
                    <>
                      <Loader2 size={12} className="animate-spin" />
                      <span>Uploading...</span>
                    </>
                  ) : (
                    <>
                      <Upload size={12} />
                      <span>Upload New Version</span>
                    </>
                  )}
                </button>
                <label className="flex items-center gap-1.5 text-[9px] select-none cursor-pointer mt-0.5 justify-center bg-slate-900/40 border border-slate-850 rounded-lg py-1 px-2.5 hover:bg-slate-800/40 transition-colors">
                  <input
                    type="checkbox"
                    checked={fastMode}
                    onChange={(e) => setFastMode(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-900 text-violet-600 focus:ring-violet-500 h-3 w-3"
                  />
                  <span className="font-semibold text-slate-400">⚡ Instant Ingestion (Milliseconds)</span>
                </label>
              </div>
            </Card>

          </div>

        </div>
      </div>

      {/* Slide-over Profile Edit Drawer (READ-ONLY Extracted Viewer) */}
      {isEditOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden" aria-labelledby="slide-over-title" role="dialog" aria-modal="true">
          <div className="absolute inset-0 overflow-hidden">
            <div 
              onClick={() => setIsEditOpen(false)}
              className="absolute inset-0 bg-slate-950/40 dark:bg-black/60 backdrop-blur-sm transition-opacity duration-300" 
            />
            <div className="absolute inset-y-0 right-0 pl-10 max-w-full flex">
              <div className="w-screen max-w-2xl transform transition-all duration-300 ease-in-out bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col h-full text-slate-100">
                
                {/* Header */}
                <div className="px-6 py-5 border-b border-slate-800 flex items-center justify-between shrink-0">
                  <div>
                    <h2 className="text-lg font-black text-white" id="slide-over-title">
                      Extracted Profile Details
                    </h2>
                    <p className="text-xs text-slate-400 font-semibold mt-1">
                      Details parsed automatically from your resume. Manual editing is disabled.
                    </p>
                  </div>
                  <button 
                    onClick={() => setIsEditOpen(false)}
                    className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
                  >
                    <X size={18} />
                  </button>
                </div>

                {/* Info Note Banner */}
                <div className="bg-slate-950 px-6 py-3 border-b border-slate-800 text-xs font-semibold text-slate-400 flex items-start gap-2 shrink-0">
                  <AlertCircle size={14} className="text-slate-400 mt-0.5 shrink-0" />
                  <span>
                    Your profile is synchronized automatically with your latest resume. To make changes or fix inaccuracies, update your resume and upload it again.
                  </span>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-hidden flex flex-col md:flex-row min-h-0">
                  
                  {/* Tabs Selector List */}
                  <div className="w-full md:w-48 bg-slate-950/30 border-b md:border-b-0 md:border-r border-slate-800 overflow-x-auto md:overflow-y-auto py-2 md:py-4 flex md:flex-col shrink-0">
                    {profileSections.map((sec) => {
                      const TabIcon = sec.icon;
                      const isTabActive = activeDrawerTab === sec.id;
                      return (
                        <button
                          key={sec.id}
                          onClick={() => setActiveDrawerTab(sec.id)}
                          className={`px-4 py-2.5 text-xs font-bold flex items-center gap-2.5 transition-all border-b-2 md:border-b-0 md:border-l-2 shrink-0 ${
                            isTabActive
                              ? "bg-slate-800 text-white border-violet-500"
                              : "text-slate-400 border-transparent hover:text-slate-200"
                          }`}
                        >
                          <TabIcon size={14} className="shrink-0" />
                          <span>{sec.name}</span>
                        </button>
                      );
                    })}
                  </div>

                  {/* Read-Only display container */}
                  <div className="flex-1 overflow-y-auto p-6 min-w-0">
                    
                    {/* PERSONAL INFORMATION TAB */}
                    {activeDrawerTab === "personal" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-white border-b border-slate-800 pb-2 flex items-center gap-2">
                          <MapPin size={16} className="text-slate-400" />
                          <span>Personal Information</span>
                        </h4>
                        <div className="space-y-4">
                          <div>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Full Name</span>
                            <div className="px-3.5 py-2.5 rounded-xl border border-slate-800 bg-slate-950/30 text-xs font-semibold text-slate-200">
                              {editForm.name || "Not specified"}
                            </div>
                          </div>
                          <div>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Email Address</span>
                            <div className="px-3.5 py-2.5 rounded-xl border border-slate-800 bg-slate-950/30 text-xs font-semibold text-slate-200">
                              {editForm.email || "Not specified"}
                            </div>
                          </div>
                          <div>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Phone Number</span>
                            <div className="px-3.5 py-2.5 rounded-xl border border-slate-800 bg-slate-950/30 text-xs font-semibold text-slate-200">
                              {editForm.phone || "Not specified"}
                            </div>
                          </div>
                          <div>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Location / Address</span>
                            <div className="px-3.5 py-2.5 rounded-xl border border-slate-800 bg-slate-950/30 text-xs font-semibold text-slate-200">
                              {editForm.address || "Not specified"}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* SUMMARY TAB */}
                    {activeDrawerTab === "summary" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-white border-b border-slate-800 pb-2 flex items-center gap-2">
                          <FileText size={16} className="text-slate-400" />
                          <span>Professional Summary</span>
                        </h4>
                        <div>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1.5">Summary</span>
                          <div className="px-4 py-3 rounded-xl border border-slate-800 bg-slate-950/30 text-xs font-semibold text-slate-300 leading-relaxed whitespace-pre-wrap">
                            {editForm.summary || "No professional summary extracted."}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* SKILLS TAB */}
                    {activeDrawerTab === "skills" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-white border-b border-slate-800 pb-2 flex items-center gap-2">
                          <Code size={16} className="text-slate-400" />
                          <span>Extracted Skills</span>
                        </h4>
                        <div>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-3">Skills List</span>
                          <div className="flex flex-wrap gap-2">
                            {skillsList.map((skill: string, idx: number) => (
                              <span key={idx} className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-slate-800 border border-slate-750 text-slate-300">
                                {skill}
                              </span>
                            ))}
                            {skillsList.length === 0 && (
                              <span className="text-xs text-slate-500 italic font-semibold">No skills extracted.</span>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* EXPERIENCE TAB */}
                    {activeDrawerTab === "experience" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-white border-b border-slate-800 pb-2 flex items-center gap-2">
                          <Briefcase size={16} className="text-slate-400" />
                          <span>Work Experience</span>
                        </h4>
                        <div className="space-y-4">
                          {editForm.experienceList.map((exp: any, index: number) => (
                            <div key={index} className="p-4 rounded-2xl border border-slate-800 bg-slate-950/20 space-y-2">
                              <div className="flex justify-between items-start">
                                <div>
                                  <h5 className="text-xs font-bold text-white">{exp.role || "Role not specified"}</h5>
                                  <p className="text-[11px] text-slate-400 font-semibold">{exp.company || "Company not specified"}</p>
                                </div>
                                {exp.years ? (
                                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                                    {exp.years} yrs
                                  </span>
                                ) : null}
                              </div>
                              {exp.description && (
                                <p className="text-xs text-slate-400 leading-relaxed whitespace-pre-wrap pt-1 border-t border-slate-800/40">
                                  {exp.description}
                                </p>
                              )}
                            </div>
                          ))}
                          {editForm.experienceList.length === 0 && (
                            <div className="text-center py-8 text-xs text-slate-500 border border-dashed border-slate-800 rounded-2xl font-semibold">
                              No experience history extracted.
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* EDUCATION TAB */}
                    {activeDrawerTab === "education" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-white border-b border-slate-800 pb-2 flex items-center gap-2">
                          <GraduationCap size={16} className="text-slate-400" />
                          <span>Education</span>
                        </h4>
                        <div className="space-y-4">
                          {editForm.educationList.map((edu: any, index: number) => (
                            <div key={index} className="p-4 rounded-2xl border border-slate-800 bg-slate-950/20 flex justify-between items-start">
                              <div className="space-y-1">
                                <h5 className="text-xs font-bold text-white">{edu.degree || "Degree not specified"}</h5>
                                <p className="text-[11px] text-slate-400 font-semibold">{edu.school || "School/University not specified"}</p>
                              </div>
                              {edu.year && (
                                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-350">
                                  {edu.year}
                                </span>
                              )}
                            </div>
                          ))}
                          {editForm.educationList.length === 0 && (
                            <div className="text-center py-8 text-xs text-slate-550 border border-dashed border-slate-800 rounded-2xl font-semibold">
                              No education history extracted.
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* PROJECTS TAB */}
                    {activeDrawerTab === "projects" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-white border-b border-slate-880 pb-2 flex items-center gap-2">
                          <Folder size={16} className="text-slate-400" />
                          <span>Projects</span>
                        </h4>
                        <div className="space-y-4">
                          {editForm.projectList.map((proj: any, index: number) => (
                            <div key={index} className="p-4 rounded-2xl border border-slate-800 bg-slate-950/20 space-y-2">
                              <div className="flex justify-between items-center">
                                <h5 className="text-xs font-bold text-white">{proj.name || "Project name not specified"}</h5>
                                {proj.link && (
                                  <a 
                                    href={proj.link} 
                                    target="_blank" 
                                    rel="noopener noreferrer" 
                                    className="text-[10px] font-bold text-blue-400 hover:underline flex items-center gap-1 cursor-pointer"
                                  >
                                    <span>Link</span>
                                    <Globe size={10} />
                                  </a>
                                )}
                              </div>
                              {proj.description && (
                                <p className="text-xs text-slate-400 leading-relaxed whitespace-pre-wrap pt-1 border-t border-slate-800/40">
                                  {proj.description}
                                </p>
                              )}
                            </div>
                          ))}
                          {editForm.projectList.length === 0 && (
                            <div className="text-center py-8 text-xs text-slate-550 border border-dashed border-slate-800 rounded-2xl font-semibold">
                              No projects history extracted.
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* CERTIFICATIONS TAB */}
                    {activeDrawerTab === "certifications" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-white border-b border-slate-800 pb-2 flex items-center gap-2">
                          <Award size={16} className="text-slate-400" />
                          <span>Certifications</span>
                        </h4>
                        <div>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-3">Extracted Certifications</span>
                          <div className="flex flex-wrap gap-2">
                            {editForm.certifications ? (
                              editForm.certifications.split(",").map((cert: string, idx: number) => {
                                const clean = cert.trim();
                                if (!clean) return null;
                                return (
                                  <span key={idx} className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-slate-800 border border-slate-750 text-slate-300">
                                    {clean}
                                  </span>
                                );
                              })
                            ) : null}
                            {(!editForm.certifications || !editForm.certifications.trim()) && (
                              <span className="text-xs text-slate-500 italic font-semibold">No certifications extracted.</span>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* ACHIEVEMENTS TAB */}
                    {activeDrawerTab === "achievements" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-white border-b border-slate-800 pb-2 flex items-center gap-2">
                          <Trophy size={16} className="text-slate-400" />
                          <span>Achievements</span>
                        </h4>
                        <div className="space-y-3">
                          {editForm.achievementsList.map((ach: string, index: number) => {
                            if (!ach.trim()) return null;
                            return (
                              <div key={index} className="flex gap-2.5 items-start p-3 rounded-2xl border border-slate-800 bg-slate-950/20 text-xs font-semibold text-slate-305">
                                <CheckCircle2 size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                                <span className="leading-relaxed">{ach}</span>
                              </div>
                            );
                          })}
                          {editForm.achievementsList.length === 0 && (
                            <div className="text-center py-8 text-xs text-slate-550 border border-dashed border-slate-800 rounded-2xl font-semibold">
                              No achievements extracted.
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* LANGUAGES TAB */}
                    {activeDrawerTab === "languages" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-white border-b border-slate-800 pb-2 flex items-center gap-2">
                          <Languages size={16} className="text-slate-400" />
                          <span>Languages</span>
                        </h4>
                        <div>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-3">Extracted Languages</span>
                          <div className="flex flex-wrap gap-2">
                            {editForm.languages ? (
                              editForm.languages.split(",").map((lang: string, idx: number) => {
                                const clean = lang.trim();
                                if (!clean) return null;
                                return (
                                  <span key={idx} className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-slate-800 border border-slate-750 text-slate-300">
                                    {clean}
                                  </span>
                                );
                              })
                            ) : null}
                            {(!editForm.languages || !editForm.languages.trim()) && (
                              <span className="text-xs text-slate-555 italic font-semibold">No languages extracted.</span>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* SOCIAL LINKS TAB */}
                    {activeDrawerTab === "socials" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-white border-b border-slate-800 pb-2 flex items-center gap-2">
                          <Globe size={16} className="text-slate-400" />
                          <span>Social Links</span>
                        </h4>
                        <div className="space-y-4">
                          {editForm.linkedin && (
                            <div>
                              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">LinkedIn Profile URL</span>
                              <a 
                                href={editForm.linkedin} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                className="px-3.5 py-2.5 rounded-xl border border-slate-800 bg-slate-950/30 text-xs font-semibold text-blue-400 hover:underline flex items-center gap-2"
                              >
                                <Globe size={13} />
                                <span>{editForm.linkedin}</span>
                              </a>
                            </div>
                          )}
                          {editForm.github && (
                            <div>
                              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">GitHub Profile URL</span>
                              <a 
                                href={editForm.github} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                className="px-3.5 py-2.5 rounded-xl border border-slate-800 bg-slate-950/30 text-xs font-semibold text-blue-400 hover:underline flex items-center gap-2"
                              >
                                <Code size={13} />
                                <span>{editForm.github}</span>
                              </a>
                            </div>
                          )}
                          {editForm.portfolio && (
                            <div>
                              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">Portfolio Website URL</span>
                              <a 
                                href={editForm.portfolio} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                className="px-3.5 py-2.5 rounded-xl border border-slate-800 bg-slate-950/30 text-xs font-semibold text-blue-400 hover:underline flex items-center gap-2"
                              >
                                <Globe size={13} />
                                <span>{editForm.portfolio}</span>
                              </a>
                            </div>
                          )}
                          {!editForm.linkedin && !editForm.github && !editForm.portfolio && (
                            <div className="text-center py-8 text-xs text-slate-500 border border-dashed border-slate-800 rounded-2xl font-semibold">
                              No social links extracted.
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                  </div>

                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-slate-800 bg-slate-950 flex items-center justify-between gap-3 shrink-0">
                  <button 
                    onClick={() => {
                      setIsEditOpen(false);
                      triggerUpload();
                    }}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-violet-650 hover:bg-violet-750 text-white text-xs font-bold cursor-pointer transition-all shadow-md"
                  >
                    <Upload size={13} />
                    <span>Upload Resume to Update</span>
                  </button>
                  <button 
                    onClick={() => setIsEditOpen(false)}
                    className="px-4 py-2 border border-slate-800 rounded-xl hover:bg-slate-800 text-xs font-bold text-slate-300 cursor-pointer transition-colors"
                  >
                    Close
                  </button>
                </div>

              </div>
            </div>

          </div>
        </div>
      )}

      {/* PDF Preview Modal */}
      {showPreviewModal && previewUrl && (
        <Modal
          isOpen={showPreviewModal}
          onClose={() => setShowPreviewModal(false)}
          title="Resume Preview"
          className="max-w-4xl h-[85vh] bg-slate-900 border border-slate-800 text-slate-100"
        >
          <div className="flex flex-col h-full -m-6">
            <div className="flex justify-end p-4 border-b border-slate-800 shrink-0">
              <a 
                href={`${getBackendBaseUrl()}${previewUrl}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-800 hover:bg-slate-800 text-xs font-bold text-slate-300 transition-colors"
              >
                <ExternalLink size={12} />
                <span>Open in new tab</span>
              </a>
            </div>
            
            <div className="flex-1 bg-slate-950">
              <iframe
                src={`${getBackendBaseUrl()}${previewUrl}`}
                className="w-full h-full border-none"
                title="Resume Preview"
              />
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
