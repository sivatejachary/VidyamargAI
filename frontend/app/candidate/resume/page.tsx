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
import AutonomousWorkflowVisualizer from "@/components/AutonomousWorkflowVisualizer";
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
  const [fastMode, setFastMode] = useState(false);

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
    if (typeof window !== "undefined" && !localStorage.getItem("cache_resume_intelligence")) {
      setLoading(true);
    }
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

        if (typeof window !== "undefined") {
          localStorage.setItem("cache_resume_intelligence", JSON.stringify({
            versions: resumeList,
            profile: profData,
            careerDna: dnaData,
            skillsGraph: skillsData,
            roles: rolesData,
            careerPaths: pathsData || [],
            skillGaps: gapsData,
            opportunities: oppsData,
            marketIntel: marketData,
            improvements: impData
          }));
        }

        if (profData?.personal_info?.name && profData.personal_info.name !== fullName) {
          updateUser(profData.personal_info.name, profData.personal_info.email || email);
        }
      }
    } catch (err: any) {
      console.error("Failed to load Career Intelligence:", err);
      if (typeof window !== "undefined" && !localStorage.getItem("cache_resume_intelligence")) {
        setErrorMsg("Failed to load Career Intelligence. Please upload a resume to start.");
      }
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
    if (typeof window !== "undefined") {
      const cached = localStorage.getItem("cache_resume_intelligence");
      if (cached) {
        try {
          const data = JSON.parse(cached);
          setVersions(data.versions || []);
          setProfile(data.profile);
          setCareerDna(data.careerDna);
          setSkillsGraph(data.skillsGraph);
          setRoles(data.roles);
          setCareerPaths(data.careerPaths || []);
          setSkillGaps(data.skillGaps);
          setOpportunities(data.opportunities);
          setMarketIntel(data.marketIntel);
          setImprovements(data.improvements);
          setLoading(false);
        } catch (e) {
          console.error(e);
        }
      }
    }
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
    if (selectedFile.type !== "application/pdf") {
      setErrorMsg("Please upload a PDF file only.");
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

  const runAIAnalysis = async (force: boolean = false) => {
    setAnalysisLoading(true);
    try {
      await apiService.analyzeResume(force);
      await loadIntelligence();
      setSuccessMsg("AI Analysis refreshed successfully!");
      setTimeout(() => setSuccessMsg(""), 3000);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to analyze resume.");
    } finally {
      setAnalysisLoading(false);
    }
  };  const downloadActiveResume = () => {
    const activeVer = resumeVersions.find(v => v.isLatest);
    if (activeVer) {
      handleDownloadResumeUrl(activeVer.url, activeVer.version);
    } else if (versions && versions.length > 0) {
      handleDownloadResumeUrl(versions[0].resume_url, versions[0].resume_url.split("/").pop() || "resume.pdf");
    } else {
      setErrorMsg("No active resume version available.");
    }
  };

  const ROLE_SKILLS_MAP: Record<string, string[]> = {
    "ai engineer": ["python", "machine learning", "pytorch", "tensorflow", "deep learning", "nlp", "llm", "openai", "transformers"],
    "ml engineer": ["python", "machine learning", "tensorflow", "pytorch", "scikit-learn", "numpy", "pandas", "computer vision", "nlp"],
    "data scientist": ["python", "r", "sql", "machine learning", "pandas", "numpy", "statistics", "data analysis", "tableau"],
    "data analyst": ["sql", "excel", "tableau", "power bi", "python", "data analysis", "statistics", "data visualization"],
    "software engineer": ["python", "java", "c++", "javascript", "typescript", "git", "docker", "aws", "sql", "rest api"],
    "backend engineer": ["python", "node.js", "go", "java", "sql", "postgresql", "mongodb", "docker", "aws", "apis", "redis"],
    "frontend engineer": ["javascript", "typescript", "react", "next.js", "vue", "html", "css", "tailwind", "webpack"],
    "fullstack engineer": ["javascript", "typescript", "react", "node.js", "sql", "html", "css", "docker", "aws"],
    "devops engineer": ["docker", "kubernetes", "aws", "ci/cd", "jenkins", "terraform", "linux", "git", "bash"],
    "cloud architect": ["aws", "azure", "gcp", "terraform", "kubernetes", "cloud architecture", "security"],
    "nlp engineer": ["nlp", "python", "pytorch", "transformers", "llm", "bert", "gpt", "spacy", "nltk"],
    "computer vision engineer": ["computer vision", "opencv", "pytorch", "tensorflow", "python", "cnn", "image processing"],
    "product manager": ["product management", "agile", "scrum", "roadmap", "user stories", "analytics"],
    "project manager": ["project management", "agile", "scrum", "jira", "budgeting", "risk management"],
    "qa engineer": ["testing", "selenium", "cypress", "jest", "qa", "automation", "bug tracking"],
  };

  const getMatchedSkillsForRole = (roleName: string, candidateSkills: string[]): string[] => {
    if (!candidateSkills || candidateSkills.length === 0) return [];
    const normalizedRole = roleName.toLowerCase();
    
    let matchedGroup: string[] = [];
    for (const [key, skills] of Object.entries(ROLE_SKILLS_MAP)) {
      if (normalizedRole.includes(key) || key.includes(normalizedRole)) {
        matchedGroup = skills;
        break;
      }
    }
    
    const intersection = candidateSkills.filter(skill => {
      const normSkill = skill.toLowerCase();
      if (matchedGroup.includes(normSkill)) return true;
      return matchedGroup.some(gSkill => gSkill.includes(normSkill) || normSkill.includes(gSkill));
    });
    
    if (intersection.length > 0) {
      return intersection.slice(0, 3);
    }
    
    return candidateSkills.slice(0, 3);
  };

  if (loading && !uploading) {
    return (
      <div className="flex-1 min-h-screen bg-slate-955 text-slate-100 p-6 md:p-8 flex items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="animate-spin text-violet-500 mx-auto" size={40} />
          <p className="text-sm font-semibold text-slate-400">Loading Career Intelligence Operating System...</p>
        </div>
      </div>
    );
  }

  if (versions.length === 0) {
    return (
      <div className="flex-1 min-h-screen bg-slate-955 text-slate-100 p-6 md:p-8 flex items-center justify-center font-sans">
        <div className="max-w-md w-full space-y-4">
          {errorMsg && <Alert variant="error">{errorMsg}</Alert>}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleResumeUpload}
            accept=".pdf"
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
        accept=".pdf"
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
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-violet-650 to-indigo-650 flex items-center justify-center text-white shadow-lg">
              <Sparkles size={22} className="animate-pulse" />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-2">
                My Resume Profile
                <Badge className="bg-violet-500/20 text-violet-400 border border-violet-800/50 py-0.5 text-[9px] font-black uppercase tracking-wider">Active</Badge>
              </h1>
              <p className="text-slate-400 mt-1 text-xs font-medium">Upload, analyze, and map your resume to AI-recommended career paths and jobs.</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button variant="outline" size="sm" onClick={triggerUpload} className="bg-slate-850 border-slate-750 text-slate-200 hover:bg-slate-800 text-xs">
              <Upload size={14} className="mr-1.5" />
              Upload New Version
            </Button>
            <Button variant="outline" size="sm" onClick={() => setIsEditOpen(true)} className="bg-slate-850 border-slate-750 text-slate-200 hover:bg-slate-800 text-xs">
              <Eye size={14} className="mr-1.5" />
              View Profile Details
            </Button>
            <Button variant="outline" size="sm" onClick={downloadActiveResume} className="bg-slate-850 border-slate-750 text-slate-200 hover:bg-slate-800 text-xs">
              <Download size={14} className="mr-1.5" />
              Download Resume
            </Button>
          </div>
        </div>

        {/* Analysis Status Banner */}
        {profile?.analysis_status && (
          <div className={`p-4 rounded-2xl border flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
            profile.analysis_status.source_type === "GEMINI" 
              ? "bg-emerald-950/20 border-emerald-800/40 text-emerald-400" 
              : "bg-amber-950/20 border-amber-800/40 text-amber-400"
          }`}>
            <div className="flex items-center gap-3">
              {profile.analysis_status.source_type === "GEMINI" ? (
                <CheckCircle2 className="text-emerald-500 flex-shrink-0" size={20} />
              ) : (
                <AlertTriangle className="text-amber-500 flex-shrink-0" size={20} />
              )}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider">
                  {profile.analysis_status.source_type === "GEMINI" 
                    ? "AI Analysis Completed" 
                    : "Basic Resume Analysis Generated"}
                </h4>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  {profile.analysis_status.source_type === "GEMINI"
                    ? `Powered by Gemini 3.5. Confidence Level: ${profile.analysis_status.confidence_score || "HIGH"}.`
                    : "Emergency fallback pipeline was used because the AI services were temporarily unavailable. A simplified profile has been generated."}
                </p>
              </div>
            </div>
            {profile.analysis_status.source_type === "FALLBACK" && (
              <Button 
                onClick={() => runAIAnalysis(true)} 
                disabled={analysisLoading}
                size="sm" 
                className="bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs flex-shrink-0"
              >
                {analysisLoading ? (
                  <>
                    <Loader2 size={12} className="animate-spin mr-1.5" />
                    Retrying...
                  </>
                ) : (
                  <>
                    <Sparkles size={12} className="mr-1.5" />
                    Retry AI Analysis
                  </>
                )}
              </Button>
            )}
          </div>
        )}

        {/* Main Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left Column: Spans 2 cols on desktop */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Profile Card */}
            <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-6 shadow-xl relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-32 h-32 bg-violet-600/10 rounded-full blur-3xl pointer-events-none group-hover:bg-violet-600/20 transition-all duration-500" />
              <div className="flex flex-col md:flex-row justify-between gap-4">
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-2xl bg-violet-550/10 text-violet-400 flex items-center justify-center shrink-0 border border-violet-550/20 shadow-md">
                      <User size={24} />
                    </div>
                    <div>
                      <h2 className="text-2xl font-black tracking-tight text-white">
                        {profile?.personal_info?.name || fullName || "Not Specified"}
                      </h2>
                      <p className="text-sm font-bold text-violet-400 mt-0.5">
                        {profile?.current_role || (profile?.career_classification?.experience_level && profile?.career_classification?.career_family 
                          ? `${profile.career_classification.experience_level} • ${profile.career_classification.career_family}` 
                          : "Professional Profile")}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2 text-xs text-slate-400 font-medium">
                    <MapPin size={14} className="text-slate-500" />
                    <span>{profile?.personal_info?.location || "Remote"}</span>
                  </div>
                </div>
                
                <div className="shrink-0 flex items-start">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => setIsEditOpen(true)} 
                    className="bg-slate-850 border-slate-750 text-slate-200 hover:bg-slate-800 text-xs font-bold w-full md:w-auto"
                  >
                    View Full Details
                  </Button>
                </div>
              </div>
            </Card>

            {/* Recommended Career Paths ⭐ */}
            <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-6 shadow-xl space-y-6">
              <div className="flex items-center gap-2.5 border-b border-slate-850 pb-4">
                <div className="w-9 h-9 rounded-xl bg-violet-600/10 text-violet-400 flex items-center justify-center shrink-0 border border-violet-650/20 shadow-sm">
                  <Sparkles size={18} className="animate-pulse" />
                </div>
                <div>
                  <h3 className="text-lg font-black text-white flex items-center gap-1.5">
                    Recommended Career Paths
                    <span className="text-amber-400">⭐</span>
                  </h3>
                  <p className="text-xs text-slate-400">AI-recommended career pathways customized to your profile data.</p>
                </div>
              </div>

              <div className="space-y-6">
                {[
                  { key: "core", title: "Core Roles", desc: "Best-fit careers aligned with your core experience and strengths." },
                  { key: "related", title: "Related Roles", desc: "Complementary pathways that leverage your transferable skills." },
                  { key: "future", title: "Future Roles", desc: "Long-term, high-growth target roles for career progression." },
                  { key: "government", title: "Government Roles", desc: "Eligible public sector and research pathways." },
                  { key: "adjacent", title: "Adjacent Roles", desc: "Alternative sectors that value your skill profiles." },
                  { key: "leadership", title: "Leadership Roles", desc: "Management and strategic leadership opportunities." }
                ].map((category) => {
                  const categoryRoles = roles?.[category.key] || [];
                  if (categoryRoles.length === 0) return null;

                  return (
                    <div key={category.key} className="space-y-3">
                      <div>
                        <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-violet-500" />
                          {category.title}
                        </h4>
                        <p className="text-[10px] text-slate-500 font-medium mt-0.5">{category.desc}</p>
                      </div>

                      <div className="space-y-3">
                        {categoryRoles.map((r: any, idx: number) => {
                          const matchedSkills = getMatchedSkillsForRole(r.role, skillsList);
                          return (
                            <div key={idx} className="p-4 rounded-2xl bg-slate-950/40 border border-slate-850 flex flex-col md:flex-row justify-between md:items-center gap-4 transition-all hover:border-slate-800 hover:bg-slate-900/40">
                              <div className="space-y-1">
                                <h5 className="text-sm font-black text-slate-100">{r.role}</h5>
                                {matchedSkills.length > 0 && (
                                  <div className="text-xs text-slate-400">
                                    <span className="font-semibold text-slate-500">Matched Skills: </span>
                                    <span className="font-medium">{matchedSkills.join(" • ")}</span>
                                  </div>
                                )}
                              </div>
                              <div className="shrink-0">
                                <Link href="/candidate/job-agent">
                                  <Button size="sm" className="bg-violet-650 hover:bg-violet-750 text-white border border-violet-600/30 text-xs font-bold py-1.5 px-4 rounded-xl transition-all shadow-md">
                                    View Jobs
                                  </Button>
                                </Link>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}

                {/* If all categories empty */}
                {(!roles || Object.values(roles).every((arr: any) => !arr || arr.length === 0)) && (
                  <div className="text-center py-8 border border-dashed border-slate-800 rounded-2xl space-y-2">
                    <Compass size={36} className="text-slate-600 mx-auto" />
                    <p className="text-xs text-slate-550 font-semibold">No career path recommendations available. Upload resume to discover paths.</p>
                  </div>
                )}
              </div>
            </Card>

            {/* Resume Summary */}
            <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-6 shadow-xl space-y-6">
              <div className="flex items-center gap-2.5 border-b border-slate-850 pb-4">
                <div className="w-9 h-9 rounded-xl bg-violet-600/10 text-violet-400 flex items-center justify-center shrink-0 border border-violet-650/20 shadow-sm">
                  <FileText size={18} />
                </div>
                <div>
                  <h3 className="text-lg font-black text-white">Resume Summary</h3>
                  <p className="text-xs text-slate-400">Extracted professional highlights and structural metric counts.</p>
                </div>
              </div>

              {profile?.personal_info?.summary && (
                <div className="space-y-2">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Overview</span>
                  <p className="text-xs text-slate-300 leading-relaxed font-medium bg-slate-950/40 p-4 rounded-xl border border-slate-850 whitespace-pre-wrap">
                    {profile.personal_info.summary}
                  </p>
                </div>
              )}

              {/* Stats Count Breakdown Row */}
              <div className="space-y-3">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Extracted Component Counts</span>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  {[
                    { label: "Skills", count: skillsList.length, icon: Code },
                    { label: "Experience", count: editForm.experienceList.length || 0, icon: Briefcase },
                    { label: "Education", count: editForm.educationList.length || 0, icon: GraduationCap },
                    { label: "Projects", count: editForm.projectList.length || 0, icon: Folder },
                    { label: "Certifications", count: editForm.certifications ? editForm.certifications.split(',').filter((s: string) => s.trim().length > 0).length : 0, icon: Award }
                  ].map((stat, idx) => {
                    const Icon = stat.icon;
                    return (
                      <div key={idx} className="p-3.5 rounded-xl border border-slate-850 bg-slate-950/30 flex flex-col items-center justify-center text-center space-y-1.5 transition-all hover:bg-slate-900/30">
                        <div className="w-8 h-8 rounded-lg bg-violet-500/10 border border-violet-550/15 text-violet-400 flex items-center justify-center">
                          <Icon size={14} />
                        </div>
                        <div>
                          <span className="text-lg font-black text-slate-100 block">{stat.count}</span>
                          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wide block mt-0.5">{stat.label}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </Card>

          </div>

          {/* Right Column: Spans 1 col on desktop */}
          <div className="lg:col-span-1 space-y-6">
            
            {/* AI Insights Card */}
            <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-5 shadow-xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-850 pb-3">
                <h3 className="text-sm font-black text-white">AI Insights</h3>
              </div>

              <div className="space-y-4">
                <div className="space-y-1 bg-slate-950/30 border border-slate-850/50 p-3 rounded-xl">
                  <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block">Best Career Match</span>
                  <span className="text-sm font-black text-slate-150 block truncate">
                    {roles?.core?.[0]?.role || profile?.current_role || "AI Engineer"}
                  </span>
                </div>

                <div className="space-y-1 bg-slate-950/30 border border-slate-850/50 p-3 rounded-xl">
                  <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block">Top Missing Skill</span>
                  <span className="text-sm font-black text-slate-150 block truncate">
                    {skillGaps?.missing_skills?.[0] || "AWS"}
                  </span>
                </div>

                <div className="space-y-2 bg-slate-950/30 border border-slate-850/50 p-3 rounded-xl">
                  <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block">Next Step</span>
                  <Link href="/candidate/job-agent" className="flex items-center justify-between group cursor-pointer">
                    <span className="text-xs font-bold text-violet-400 group-hover:text-violet-300 transition-colors">
                      Open AI Job Agent
                    </span>
                    <ChevronRight size={14} className="text-violet-400 group-hover:translate-x-1 transition-transform" />
                  </Link>
                </div>
              </div>
            </Card>

            {/* Career Opportunities Card */}
            <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-5 shadow-xl space-y-4">
              <div className="border-b border-slate-850 pb-3">
                <h3 className="text-sm font-black text-white">Career Opportunities</h3>
              </div>

              <div className="space-y-3">
                {[
                  { label: "Private Jobs", score: opportunities?.opportunity_scores?.private_score || 85 },
                  { label: "Remote Jobs", score: opportunities?.opportunity_scores?.remote_score || 80 },
                  { label: "International", score: opportunities?.opportunity_scores?.international_score || 65 },
                  { label: "Government", score: opportunities?.opportunity_scores?.government_score || 45 }
                ].map((opp, idx) => {
                  let indicator = "🟢";
                  if (opp.score < 50) indicator = "🔴";
                  else if (opp.score < 80) indicator = "🟡";

                  return (
                    <div key={idx} className="flex items-center justify-between p-2.5 rounded-xl border border-slate-850/60 bg-slate-955/20 transition-all hover:bg-slate-950/40">
                      <span className="text-xs font-bold text-slate-200">{opp.label}</span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs">{indicator}</span>
                        <span className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">
                          {opp.score >= 80 ? "High" : opp.score >= 50 ? "Medium" : "Low"}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>

            {/* Top Skills Card */}
            <Card className="bg-slate-900/60 backdrop-blur-md border-slate-850 p-5 shadow-xl space-y-4">
              <div className="border-b border-slate-850 pb-3">
                <h3 className="text-sm font-black text-white">Top Skills</h3>
              </div>

              <div className="flex flex-wrap gap-1.5">
                {skillsList.slice(0, 12).map((skill: string, idx: number) => (
                  <span key={idx} className="text-[10px] font-bold px-2.5 py-1.5 rounded-xl bg-slate-955/80 border border-slate-850 hover:border-slate-700 hover:text-white transition-all text-slate-300">
                    {skill}
                  </span>
                ))}
                {skillsList.length === 0 && (
                  <span className="text-xs text-slate-550 italic font-semibold">No skills extracted.</span>
                )}
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
      <AutonomousWorkflowVisualizer defaultWorkflow="resume" isExecuting={uploading || analysisLoading} />
    </div>
  );
}
