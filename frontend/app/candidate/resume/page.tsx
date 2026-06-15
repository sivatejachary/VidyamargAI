"use client";

import { useEffect, useState, useRef } from "react";
import { apiService } from "@/services/api";
import { useAuthStore } from "@/store/authStore";
import { 
  Download, Trash2, Edit, Eye, RotateCcw, Upload, Plus, 
  Sparkles, CheckCircle2, Loader2, FileText, ChevronRight, 
  X, Check, AlertCircle, ShieldCheck, TrendingUp, Zap, 
  AlertTriangle, Award, Link2, ExternalLink, GraduationCap, 
  Briefcase, MapPin, Mail, Phone, Camera, Code, Folder, Trophy,
  Globe, Languages, User
} from "lucide-react";

interface ResumeVersion {
  id: number;
  url: string;
  date: string;
  version: string;
  isLatest: boolean;
}

interface ProfileSectionItem {
  id: string;
  name: string;
  desc: string;
  icon: any;
  completed: boolean;
}

export default function ResumeBuilder() {
  const { fullName, email } = useAuthStore();
  const [profile, setProfile] = useState<any>(null);
  const [resumeVersions, setResumeVersions] = useState<ResumeVersion[]>([]);
  const [analysisData, setAnalysisData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  // Edit Drawer State
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<string>("personal");
  const [editForm, setEditForm] = useState<any>({
    name: "",
    email: "",
    phone: "",
    address: "",
    summary: "",
    skills: "",
    certifications: "",
    languages: "",
    linkedin: "",
    github: "",
    portfolio: "",
    educationList: [],
    experienceList: [],
    projectList: [],
    achievementsList: [],
  });

  // Preview Modal State
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load all dashboard data
  const loadDashboardData = async () => {
    try {
      const prof = await apiService.getProfile();
      setProfile(prof);

      // Initialize Edit Form values
      let parsedEdu = [];
      try { parsedEdu = prof.education ? JSON.parse(prof.education) : []; } catch { parsedEdu = []; }
      
      let parsedExp = [];
      try { parsedExp = prof.experience ? JSON.parse(prof.experience) : []; } catch { parsedExp = []; }
      
      let parsedProj = [];
      try { parsedProj = prof.projects ? JSON.parse(prof.projects) : []; } catch { parsedProj = []; }

      let parsedAch = [];
      try { parsedAch = prof.achievements ? JSON.parse(prof.achievements) : []; } catch { parsedAch = []; }

      setEditForm({
        name: prof.parsed_name || "",
        email: prof.parsed_email || "",
        phone: prof.phone || "",
        address: prof.address || "",
        summary: prof.summary || "",
        skills: prof.skills || "",
        certifications: prof.certifications || "",
        languages: prof.languages || "",
        linkedin: prof.linkedin || "",
        github: prof.github || "",
        portfolio: prof.portfolio || "",
        educationList: parsedEdu,
        experienceList: parsedExp,
        projectList: parsedProj,
        achievementsList: parsedAch,
      });

      // Load resume versions
      try {
        const resumes = await apiService.getResumes();
        if (resumes && Array.isArray(resumes)) {
          const formattedResumes = resumes.map((res: any, idx: number) => {
            const rawDate = typeof res.uploaded_at === "string" ? res.uploaded_at.replace(" ", "T") : res.uploaded_at;
            const dateObj = new Date(rawDate);
            const dateStr = isNaN(dateObj.getTime())
              ? "Unknown Date"
              : dateObj.toLocaleString("en-US", {
                  day: "2-digit",
                  month: "short",
                  year: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                  hour12: true,
                });
            return {
              id: res.id,
              url: res.resume_url,
              date: dateStr,
              version: `v${resumes.length - idx}.0`,
              isLatest: idx === 0,
            };
          });
          setResumeVersions(formattedResumes);
        }
      } catch (err) {
        console.error("Failed to load resume versions:", err);
      }

      // Load AI analysis
      setAnalysisLoading(true);
      try {
        const analysis = await apiService.analyzeResume();
        if (analysis) {
          setAnalysisData(analysis);
        }
      } catch (err) {
        console.error("Failed to load AI analysis:", err);
      } finally {
        setAnalysisLoading(false);
      }

    } catch (err) {
      console.error("Failed to load profile data:", err);
      setErrorMsg("Failed to load profile data. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const triggerUpload = () => {
    fileInputRef.current?.click();
  };

  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const selectedFile = e.target.files[0];
    if (selectedFile.type !== "application/pdf") {
      setErrorMsg("Please upload a PDF file only.");
      setTimeout(() => setErrorMsg(""), 4000);
      return;
    }

    setUploading(true);
    setErrorMsg("");
    setSuccessMsg("");

    try {
      await apiService.uploadResume(selectedFile);
      setSuccessMsg("Resume uploaded and parsed successfully! AI scores are updating...");
      setTimeout(() => setSuccessMsg(""), 5000);
      await loadDashboardData();
    } catch (err: any) {
      setErrorMsg(err.message || "Resume upload failed.");
      setTimeout(() => setErrorMsg(""), 5000);
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteResumeVersion = async (id: number) => {
    if (!confirm("Are you sure you want to delete this resume version?")) return;
    try {
      await apiService.deleteResumeVersion(id);
      setSuccessMsg("Resume version deleted successfully.");
      setTimeout(() => setSuccessMsg(""), 3000);
      await loadDashboardData();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to delete resume version.");
      setTimeout(() => setErrorMsg(""), 3000);
    }
  };

  const handleDownloadLatestResume = () => {
    if (resumeVersions.length === 0) {
      setErrorMsg("No resume uploaded yet.");
      setTimeout(() => setErrorMsg(""), 3000);
      return;
    }
    const latest = resumeVersions[0];
    handleDownloadResumeUrl(latest.url, latest.version);
  };

  const handleDownloadResumeUrl = (url: string, version: string) => {
    const backendUrl = typeof window !== "undefined" && window.location.hostname === "localhost"
      ? "http://127.0.0.1:8000"
      : `http://${window.location.hostname}:8000`;
    
    const downloadLink = document.createElement("a");
    downloadLink.href = `${backendUrl}${url}`;
    downloadLink.target = "_blank";
    downloadLink.download = `Resume_${fullName || "Candidate"}_${version}.pdf`;
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
  };

  const handlePreviewResume = (url: string) => {
    setPreviewUrl(url);
    setShowPreviewModal(true);
  };

  const runAIAnalysis = async () => {
    setAnalysisLoading(true);
    setErrorMsg("");
    try {
      const analysis = await apiService.analyzeResume();
      if (analysis) {
        setAnalysisData(analysis);
        setSuccessMsg("Analysis refreshed successfully!");
        setTimeout(() => setSuccessMsg(""), 3000);
      }
    } catch (err) {
      console.error("AI analysis failed:", err);
      setErrorMsg("AI analysis refresh failed.");
      setTimeout(() => setErrorMsg(""), 3000);
    } finally {
      setAnalysisLoading(false);
    }
  };

  // Profile Drawer Form Helper Methods
  const handleAddEducation = () => {
    setEditForm((prev: any) => ({
      ...prev,
      educationList: [...prev.educationList, { degree: "", school: "", year: "" }],
    }));
  };

  const handleRemoveEducation = (index: number) => {
    setEditForm((prev: any) => ({
      ...prev,
      educationList: prev.educationList.filter((_: any, i: number) => i !== index),
    }));
  };

  const handleEducationChange = (index: number, field: string, val: string) => {
    const updated = [...editForm.educationList];
    updated[index] = { ...updated[index], [field]: val };
    setEditForm((prev: any) => ({ ...prev, educationList: updated }));
  };

  const handleAddExperience = () => {
    setEditForm((prev: any) => ({
      ...prev,
      experienceList: [...prev.experienceList, { role: "", company: "", years: 1, description: "" }],
    }));
  };

  const handleRemoveExperience = (index: number) => {
    setEditForm((prev: any) => ({
      ...prev,
      experienceList: prev.experienceList.filter((_: any, i: number) => i !== index),
    }));
  };

  const handleExperienceChange = (index: number, field: string, val: any) => {
    const updated = [...editForm.experienceList];
    updated[index] = { ...updated[index], [field]: val };
    setEditForm((prev: any) => ({ ...prev, experienceList: updated }));
  };

  const handleAddProject = () => {
    setEditForm((prev: any) => ({
      ...prev,
      projectList: [...prev.projectList, { name: "", description: "", link: "" }],
    }));
  };

  const handleRemoveProject = (index: number) => {
    setEditForm((prev: any) => ({
      ...prev,
      projectList: prev.projectList.filter((_: any, i: number) => i !== index),
    }));
  };

  const handleProjectChange = (index: number, field: string, val: string) => {
    const updated = [...editForm.projectList];
    updated[index] = { ...updated[index], [field]: val };
    setEditForm((prev: any) => ({ ...prev, projectList: updated }));
  };

  const handleAddAchievement = () => {
    setEditForm((prev: any) => ({
      ...prev,
      achievementsList: [...prev.achievementsList, ""],
    }));
  };

  const handleRemoveAchievement = (index: number) => {
    setEditForm((prev: any) => ({
      ...prev,
      achievementsList: prev.achievementsList.filter((_: any, i: number) => i !== index),
    }));
  };

  const handleAchievementChange = (index: number, val: string) => {
    const updated = [...editForm.achievementsList];
    updated[index] = val;
    setEditForm((prev: any) => ({ ...prev, achievementsList: updated }));
  };

  const handleSaveProfile = async () => {
    try {
      setLoading(true);
      
      const payload = {
        phone: editForm.phone,
        address: editForm.address,
        skills: editForm.skills,
        certifications: editForm.certifications,
        summary: editForm.summary,
        languages: editForm.languages,
        linkedin: editForm.linkedin,
        github: editForm.github,
        portfolio: editForm.portfolio,
        education: JSON.stringify(editForm.educationList),
        experience: JSON.stringify(editForm.experienceList),
        projects: JSON.stringify(editForm.projectList),
        achievements: JSON.stringify(editForm.achievementsList),
      };

      await apiService.updateProfile(payload);
      setSuccessMsg("Profile saved and updated successfully!");
      setIsEditOpen(false);
      setTimeout(() => setSuccessMsg(""), 3000);
      await loadDashboardData();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to update profile.");
      setTimeout(() => setErrorMsg(""), 3000);
    } finally {
      setLoading(false);
    }
  };

  const handleSectionClick = (sectionId: string) => {
    setActiveTab(sectionId);
    setIsEditOpen(true);
  };

  const handleCompleteNow = () => {
    // Find first incomplete section
    const firstIncomplete = profileSections.find(s => !s.completed);
    if (firstIncomplete) {
      setActiveTab(firstIncomplete.id);
    } else {
      setActiveTab("personal");
    }
    setIsEditOpen(true);
  };

  const handleImproveWithAI = () => {
    alert("AI optimization tips: Ensure your experience description uses strong action verbs like 'Engineered', 'Optimized', and 'Scaled' with specific metrics (e.g. 'boosted performance by 25%'). Run a new resume upload to re-parse with Gemini!");
  };

  // Computations
  const displayName = profile?.parsed_name || fullName || "Not specified";
  const displayEmail = profile?.parsed_email || email || "Not specified";
  const avatarLetter = profile?.parsed_name ? profile.parsed_name[0].toUpperCase() : (fullName ? fullName[0].toUpperCase() : "?");
  const completionScore = analysisData?.profile_completion?.score ?? 0;
  const aiQualityScore = analysisData?.ai_quality?.score ?? 0;
  const aiQualityBreakdown = analysisData?.ai_quality?.breakdown ?? {
    grammar: 0,
    formatting: 0,
    readability: 0,
    project_quality: 0,
    achievement_quality: 0,
    structure: 0,
  };

  // Skills List
  const skillsList = profile?.skills 
    ? profile.skills.split(",").map((s: string) => s.trim()).filter((s: string) => s.length > 0)
    : [];

  // Keywords found
  const keywordsList = skillsList.slice(0, 10);

  // Dynamic missing fields based on empty candidate fields
  const missingItems: string[] = [];
  if (!profile?.certifications) missingItems.push("Certifications");
  if (!profile?.achievements || profile?.achievements === "[]") missingItems.push("Achievements");
  if (!profile?.linkedin) missingItems.push("LinkedIn Profile");
  if (!profile?.portfolio) missingItems.push("Portfolio Link");

  // Summaries
  let educationCount = 0;
  try { educationCount = profile?.education ? JSON.parse(profile.education).length : 0; } catch { educationCount = 0; }

  let experienceYears = 0;
  try {
    const expArr = profile?.experience ? JSON.parse(profile.experience) : [];
    experienceYears = expArr.reduce((sum: number, exp: any) => sum + (Number(exp.years) || 0), 0);
  } catch {
    experienceYears = 0;
  }

  const getFirstRole = () => {
    if (!profile?.experience) return "Not specified";
    try {
      const parsed = JSON.parse(profile.experience);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed[0]?.role || "Not specified";
      }
    } catch {
      // safe fallback
    }
    return "Not specified";
  };

  let projectsCount = 0;
  try { projectsCount = profile?.projects ? JSON.parse(profile.projects).length : 0; } catch { projectsCount = 0; }

  let certificationsCount = 0;
  if (profile?.certifications) {
    certificationsCount = profile.certifications.split(",").filter((c: string) => c.trim().length > 0).length;
  }

  let achievementsCount = 0;
  try { achievementsCount = profile?.achievements ? JSON.parse(profile.achievements).length : 0; } catch { achievementsCount = 0; }

  // Profile Sections checklist
  const profileSections: ProfileSectionItem[] = [
    { 
      id: "personal", 
      name: "Personal Information", 
      desc: "Name, contact details, location", 
      icon: MapPin, 
      completed: !!(profile?.phone || profile?.address) 
    },
    { 
      id: "summary", 
      name: "Summary", 
      desc: "Professional summary about you", 
      icon: FileText, 
      completed: !!profile?.summary 
    },
    { 
      id: "skills", 
      name: "Skills", 
      desc: "Your technical and soft skills", 
      icon: Code, 
      completed: skillsList.length > 0 
    },
    { 
      id: "experience", 
      name: "Experience", 
      desc: "Your work experience details", 
      icon: Briefcase, 
      completed: experienceYears > 0 
    },
    { 
      id: "education", 
      name: "Education", 
      desc: "Schools, degrees, graduation", 
      icon: GraduationCap, 
      completed: educationCount > 0 
    },
    { 
      id: "projects", 
      name: "Projects", 
      desc: "Academic or professional creations", 
      icon: Folder, 
      completed: projectsCount > 0 
    },
    { 
      id: "certifications", 
      name: "Certifications", 
      desc: "Professional training & credentials", 
      icon: Award, 
      completed: certificationsCount > 0 
    },
    { 
      id: "achievements", 
      name: "Achievements", 
      desc: "Honors, accomplishments, rewards", 
      icon: Trophy, 
      completed: achievementsCount > 0 
    },
    { 
      id: "languages", 
      name: "Languages", 
      desc: "Tongues you speak or write", 
      icon: Languages, 
      completed: !!profile?.languages 
    },
    { 
      id: "socials", 
      name: "Social Links", 
      desc: "LinkedIn, GitHub, Portfolios", 
      icon: Globe, 
      completed: !!(profile?.linkedin || profile?.github || profile?.portfolio) 
    },
  ];

  // AI Insights
  const strongestSkill = skillsList[0] || "Not specified";
  const improvementArea = skillsList.length === 0 ? "Upload resume to determine" : (projectsCount < 3 ? "Add more projects" : "Include certifications");
  const profileStrength = skillsList.length === 0 ? "N/A" : (completionScore >= 80 ? "Strong" : (completionScore >= 60 ? "Good" : "Needs Work"));
  const recommendedStep = skillsList.length === 0 ? "Upload resume to get insights" : (!profile?.certifications ? "Add certifications" : (!profile?.achievements ? "Add achievements" : "Optimize summary"));

  if (loading) {
    return (
      <div className="flex-1 min-h-screen flex items-center justify-center bg-slate-50/50 dark:bg-[#09090b]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 size={36} className="animate-spin text-slate-800 dark:text-white" />
          <span className="text-sm font-semibold text-slate-500 dark:text-slate-400">Loading Resume Dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 min-h-screen bg-slate-50/50 dark:bg-[#09090b] text-slate-800 dark:text-slate-100 p-6 md:p-8 font-sans transition-colors duration-300">
      
      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleResumeUpload}
        accept="application/pdf"
        className="hidden"
      />

      <div className="max-w-[1440px] mx-auto space-y-6">
        
        {/* Status Alerts */}
        {successMsg && (
          <div className="p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-250 dark:border-emerald-800/40 text-emerald-800 dark:text-emerald-400 text-xs font-semibold flex items-center gap-2 animate-fadeIn">
            <CheckCircle2 size={16} className="text-emerald-500 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {errorMsg && (
          <div className="p-4 rounded-2xl bg-red-50 dark:bg-red-950/20 border border-red-250 dark:border-red-800/40 text-red-800 dark:text-red-400 text-xs font-semibold flex items-center gap-2 animate-fadeIn">
            <AlertTriangle size={16} className="text-red-500 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* 1. Header Area */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-black tracking-tight text-slate-900 dark:text-white">My Resume Profile</h1>
            <p className="text-slate-500 dark:text-slate-455 mt-1.5 text-sm leading-relaxed max-w-2xl font-medium">
              Your resume has been parsed and your profile is ready. Keep it updated for better opportunities.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button 
              onClick={handleDownloadLatestResume}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-bold text-slate-700 dark:text-slate-300 transition-all shadow-sm shrink-0 cursor-pointer"
            >
              <Download size={14} />
              <span>Download Resume</span>
            </button>
            <button 
              onClick={() => setIsEditOpen(true)}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-bold text-slate-700 dark:text-slate-300 transition-all shadow-sm shrink-0 cursor-pointer"
            >
              <Eye size={14} />
              <span>View Profile Details</span>
            </button>
          </div>
        </div>

        {/* 2. Main content 3-column Grid layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* LEFT 2 COLUMNS */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* MOBILE ONLY VERSION OF THE PROFILE CARD (Shown on screens < md) */}
            <div className="block md:hidden rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800/80 p-6 shadow-sm">
              <div className="flex flex-col gap-6">
                
                {/* Bio Column */}
                <div className="flex flex-col items-center gap-4">
                  <div className="relative shrink-0">
                    <div className="w-24 h-24 rounded-full overflow-hidden border border-slate-200/60 dark:border-slate-800 shadow-sm bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-800 dark:text-slate-200 text-3xl font-black">
                      {avatarLetter}
                    </div>
                    <button 
                      onClick={triggerUpload}
                      disabled={uploading}
                      className="absolute bottom-0 right-0 w-8 h-8 rounded-full bg-white dark:bg-slate-800 text-slate-500 dark:text-slate-350 flex items-center justify-center border border-slate-200 dark:border-slate-700 hover:bg-slate-55 dark:hover:bg-slate-750 transition-all shadow-sm cursor-pointer"
                      title="Upload Resume to Update Profile"
                    >
                      {uploading ? <Loader2 size={13} className="animate-spin" /> : <Upload size={13} />}
                    </button>
                  </div>
                  
                  <div className="space-y-2 text-center min-w-0 w-full">
                    <div className="flex items-center justify-center gap-2">
                      <h2 className="text-xl font-black text-slate-900 dark:text-white truncate max-w-[200px]" title={displayName || undefined}>
                        {displayName}
                      </h2>
                      <span className="inline-flex px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/30 text-[9px] font-bold text-emerald-600 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-900/40">
                        Verified Profile
                      </span>
                    </div>
                    
                    <div className="space-y-1.5 text-xs font-semibold text-slate-600 dark:text-slate-400 inline-block text-left">
                      <div className="flex items-center gap-2">
                        <User size={14} className="text-slate-400 shrink-0" />
                        <span className="truncate">{getFirstRole() || "Not specified"}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <MapPin size={14} className="text-slate-400 shrink-0" />
                        <span className="truncate">{profile?.address || "Not specified"}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Mail size={14} className="text-slate-400 shrink-0" />
                        <span className="truncate">{displayEmail}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Phone size={14} className="text-slate-400 shrink-0" />
                        <span>{profile?.phone || "Not specified"}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Completion Column */}
                <div className="flex flex-col items-center justify-center w-full">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 mb-3">Profile Completion</span>
                  
                  <div className="relative flex items-center justify-center my-1">
                    <svg width="100" height="100" className="transform -rotate-90">
                      <circle cx="50" cy="50" r="43" fill="none" strokeWidth="8" className="text-slate-100 dark:text-slate-800" stroke="currentColor" />
                      <circle cx="50" cy="50" r="43" fill="none" strokeWidth="8" strokeDasharray={2 * Math.PI * 43} strokeDashoffset={2 * Math.PI * 43 - (completionScore / 100) * (2 * Math.PI * 43)} strokeLinecap="round" stroke="#10b981" className="transition-all duration-700 ease-out" />
                    </svg>
                    <div className="absolute text-2xl font-black text-slate-900 dark:text-white">{completionScore}%</div>
                  </div>
                  
                  <span className="text-xs font-black text-emerald-600 dark:text-emerald-400 mt-3">
                    {completionScore >= 75 ? "Good Progress!" : (completionScore > 0 ? "Started" : "No Resume Uploaded")}
                  </span>
                </div>

              </div>

              {/* Horizontal Divider Line */}
              <div className="border-t border-slate-200/60 dark:border-slate-800/80 my-5" />

              {/* Missing Section */}
              <div className="space-y-4">
                <span className="text-xs font-black text-slate-400 dark:text-slate-500 uppercase tracking-wider block">
                  Missing ({100 - completionScore}%)
                </span>
                
                {/* Mobile Missing Cards */}
                <div className="space-y-3">
                  {missingItems.length > 0 ? (
                    missingItems.map((item, idx) => {
                      let IconComponent = Award;
                      if (item === "Achievements") IconComponent = Trophy;
                      else if (item.includes("LinkedIn")) IconComponent = Link2;
                      else if (item.includes("Portfolio")) IconComponent = Globe;
                      
                      return (
                        <div 
                          key={idx} 
                          onClick={handleCompleteNow} 
                          className="flex items-center justify-between p-4 rounded-xl border border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 text-emerald-600 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-900/40 shrink-0">
                              <IconComponent size={18} />
                            </div>
                            <span className="text-sm font-semibold text-slate-850 dark:text-slate-200">{item}</span>
                          </div>
                          
                          <div className="flex items-center gap-2">
                            <span className="px-2.5 py-0.5 rounded-full bg-red-50 dark:bg-red-950/30 text-[10px] font-bold text-red-500 dark:text-red-400 border border-red-100 dark:border-red-950/20">
                              Missing
                            </span>
                            <ChevronRight size={16} className="text-slate-400" />
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="p-4 rounded-xl border border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900 text-center text-xs text-emerald-600 dark:text-emerald-400 font-bold">
                      All sections complete! ✓
                    </div>
                  )}
                </div>

                {/* Complete your profile box */}
                <div className="p-5 rounded-2xl bg-emerald-50/20 dark:bg-slate-900/30 border border-emerald-100/50 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div className="flex items-center gap-4 text-left w-full sm:w-auto">
                    <div className="w-12 h-12 rounded-xl bg-white dark:bg-slate-800 border border-emerald-100 dark:border-emerald-700 flex items-center justify-center shrink-0 shadow-sm text-emerald-600 dark:text-emerald-400">
                      <FileText size={22} />
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-sm font-black text-slate-900 dark:text-white">Complete your profile</h4>
                      <p className="text-xs text-slate-550 dark:text-slate-400 mt-0.5 leading-relaxed">
                        Add missing information to improve your profile and get better job opportunities.
                      </p>
                    </div>
                  </div>
                  
                  <button 
                    onClick={handleCompleteNow}
                    className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-[#0e9f6e] hover:bg-emerald-700 text-xs font-black text-white transition-all shadow-sm shadow-emerald-500/10 cursor-pointer text-center shrink-0"
                  >
                    Update Profile
                  </button>
                </div>
                
              </div>

            </div>

            {/* DESKTOP ONLY VERSION OF THE PROFILE CARD (Shown on screens >= md) */}
            <div className="hidden md:grid grid-cols-1 md:grid-cols-2 gap-6 p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-855 shadow-sm">
              
              {/* Bio Column */}
              <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6 md:border-r border-slate-155 dark:border-slate-800/80 md:pr-6">
                <div className="relative shrink-0">
                  <div className="w-24 h-24 rounded-full overflow-hidden border-2 border-slate-100 dark:border-slate-800 shadow-sm bg-blue-600 flex items-center justify-center text-white text-3xl font-black">
                    {avatarLetter}
                  </div>
                  <button 
                    onClick={triggerUpload}
                    disabled={uploading}
                    className="absolute bottom-0 right-0 w-8 h-8 rounded-full bg-slate-950 dark:bg-slate-800 text-white flex items-center justify-center border border-white dark:border-slate-900 hover:bg-slate-900 transition-all animate-pulse cursor-pointer"
                    title="Upload Resume to Update Profile"
                  >
                    {uploading ? <Loader2 size={13} className="animate-spin" /> : <Upload size={13} />}
                  </button>
                </div>
                
                <div className="space-y-2 text-center sm:text-left min-w-0">
                  <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
                    <h2 className="text-xl font-black text-slate-900 dark:text-white truncate max-w-[150px]" title={displayName || undefined}>
                      {displayName}
                    </h2>
                    <span className="inline-flex px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950/40 text-[9px] font-bold text-blue-600 dark:text-blue-400 border border-blue-100 dark:border-blue-800/50">
                      Verified Profile
                    </span>
                  </div>
                  <p className="text-xs font-bold text-slate-505 dark:text-slate-400">
                    {getFirstRole()}
                  </p>
                  
                  <div className="space-y-1.5 pt-1 text-xs font-semibold text-slate-455 dark:text-slate-450">
                    <div className="flex items-center gap-2 justify-center sm:justify-start">
                      <MapPin size={12} className="text-slate-400 shrink-0" />
                      <span className="truncate">{profile?.address || "Not specified"}</span>
                    </div>
                    <div className="flex items-center gap-2 justify-center sm:justify-start">
                      <Mail size={12} className="text-slate-400 shrink-0" />
                      <span className="truncate">{displayEmail}</span>
                    </div>
                    <div className="flex items-center gap-2 justify-center sm:justify-start">
                      <Phone size={12} className="text-slate-400 shrink-0" />
                      <span>{profile?.phone || "Not specified"}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Completion Column */}
              <div className="flex flex-col sm:flex-row items-center gap-6 pl-0 md:pl-2 justify-between">
                <div className="flex flex-col items-center gap-1 shrink-0">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">Profile Completion</span>
                  
                  <div className="relative flex items-center justify-center my-1.5">
                    <svg width="86" height="86" className="transform -rotate-90">
                      <circle cx="43" cy="43" r="37" fill="none" strokeWidth="6" className="text-slate-100 dark:text-slate-800" stroke="currentColor" />
                      <circle cx="43" cy="43" r="37" fill="none" strokeWidth="6" strokeDasharray={2 * Math.PI * 37} strokeDashoffset={2 * Math.PI * 37 - (completionScore / 100) * (2 * Math.PI * 37)} strokeLinecap="round" stroke="#0ea5e9" className="transition-all duration-700 ease-out" />
                    </svg>
                    <div className="absolute text-lg font-black text-slate-900 dark:text-white">{completionScore}%</div>
                  </div>
                  <span className="text-[10px] font-bold text-emerald-500 dark:text-emerald-400">
                    {completionScore >= 75 ? "Good Progress!" : (completionScore > 0 ? "Started" : "No Resume Uploaded")}
                  </span>
                </div>

                <div className="flex-1 flex flex-col justify-between h-full gap-3 w-full text-center sm:text-left min-w-0">
                  <div>
                    <span className="text-[10px] font-bold text-slate-450 dark:text-slate-400 uppercase tracking-wider block">Missing ({100 - completionScore}%)</span>
                    <div className="mt-1.5 space-y-1 inline-block text-left">
                      {missingItems.length > 0 ? (
                        missingItems.map((item, idx) => (
                          <div key={idx} className="flex items-center gap-1.5 text-xs text-slate-505 dark:text-slate-400 font-bold">
                            <span className="w-1.5 h-1.5 rounded-full bg-teal-505 shrink-0" />
                            <span>{item}</span>
                          </div>
                        ))
                      ) : (
                        <span className="text-xs text-emerald-500 font-black">All sections complete! ✓</span>
                      )}
                    </div>
                  </div>
                  
                  <button 
                    onClick={handleCompleteNow}
                    className="w-full py-2 rounded-xl bg-teal-505 hover:bg-teal-600 text-xs font-extrabold text-white transition-all shadow-sm shadow-teal-500/10 cursor-pointer"
                  >
                    View Profile Gaps
                  </button>
                </div>
              </div>

            </div>

            {/* Row 2: Profile Summary Grid (6 widgets) */}
            <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-855 rounded-3xl p-6 shadow-sm space-y-4">
              <h3 className="text-base font-black text-slate-900 dark:text-white">Profile Summary</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                
                {/* Skills */}
                <div className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50/20 dark:bg-slate-900/40 flex items-center gap-4">
                  <div className="w-11 h-11 rounded-xl bg-blue-50 dark:bg-blue-950/40 text-blue-550 flex items-center justify-center shrink-0 border border-blue-100/50 dark:border-blue-800/30">
                    <Code size={18} />
                  </div>
                  <div className="min-w-0">
                    <span className="text-[9px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">Skills</span>
                    <div className="flex items-baseline gap-1 mt-0.5">
                      <span className="text-lg font-black text-slate-955 dark:text-slate-100">{skillsList.length}</span>
                      <span className="text-[9px] font-bold text-slate-400">Extracted</span>
                    </div>
                  </div>
                </div>

                {/* Experience */}
                <div className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50/20 dark:bg-slate-900/40 flex items-center gap-4">
                  <div className="w-11 h-11 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 text-emerald-555 flex items-center justify-center shrink-0 border border-emerald-100/50 dark:border-emerald-800/30">
                    <Briefcase size={18} />
                  </div>
                  <div className="min-w-0">
                    <span className="text-[9px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">Experience</span>
                    <div className="flex items-baseline gap-1 mt-0.5">
                      <span className="text-lg font-black text-slate-955 dark:text-slate-100">{experienceYears.toFixed(1)}</span>
                      <span className="text-[9px] font-bold text-slate-400">Years</span>
                    </div>
                  </div>
                </div>

                {/* Education */}
                <div className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50/20 dark:bg-slate-900/40 flex items-center gap-4">
                  <div className="w-11 h-11 rounded-xl bg-purple-50 dark:bg-purple-950/40 text-purple-555 flex items-center justify-center shrink-0 border border-purple-100/50 dark:border-purple-800/30">
                    <GraduationCap size={18} />
                  </div>
                  <div className="min-w-0">
                    <span className="text-[9px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">Education</span>
                    <div className="flex items-baseline gap-1 mt-0.5">
                      <span className="text-lg font-black text-slate-955 dark:text-slate-100">{educationCount}</span>
                      <span className="text-[9px] font-bold text-slate-400">{educationCount === 1 ? "Degree" : "Degrees"}</span>
                    </div>
                  </div>
                </div>

                {/* Projects */}
                <div className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50/20 dark:bg-slate-900/40 flex items-center gap-4">
                  <div className="w-11 h-11 rounded-xl bg-amber-50 dark:bg-amber-955/40 text-amber-555 flex items-center justify-center shrink-0 border border-amber-100/50 dark:border-amber-800/30">
                    <Folder size={18} />
                  </div>
                  <div className="min-w-0">
                    <span className="text-[9px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">Projects</span>
                    <div className="flex items-baseline gap-1 mt-0.5">
                      <span className="text-lg font-black text-slate-955 dark:text-slate-100">{projectsCount}</span>
                      <span className="text-[9px] font-bold text-slate-400">Added</span>
                    </div>
                  </div>
                </div>

                {/* Certifications */}
                <div className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50/20 dark:bg-slate-900/40 flex items-center gap-4">
                  <div className="w-11 h-11 rounded-xl bg-rose-50 dark:bg-rose-950/40 text-rose-555 flex items-center justify-center shrink-0 border border-rose-100/50 dark:border-rose-800/30">
                    <Award size={18} />
                  </div>
                  <div className="min-w-0">
                    <span className="text-[9px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">Certifications</span>
                    <div className="flex items-baseline gap-1 mt-0.5">
                      <span className="text-lg font-black text-slate-955 dark:text-slate-100">{certificationsCount}</span>
                      <span className="text-[9px] font-bold text-slate-400">Added</span>
                    </div>
                  </div>
                </div>

                {/* Achievements */}
                <div className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50/20 dark:bg-slate-900/40 flex items-center gap-4">
                  <div className="w-11 h-11 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 text-indigo-555 flex items-center justify-center shrink-0 border border-indigo-100/50 dark:border-indigo-800/30">
                    <Trophy size={18} />
                  </div>
                  <div className="min-w-0">
                    <span className="text-[9px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">Achievements</span>
                    <div className="flex items-baseline gap-1 mt-0.5">
                      <span className="text-lg font-black text-slate-955 dark:text-slate-100">{achievementsCount}</span>
                      <span className="text-[9px] font-bold text-slate-400">Added</span>
                    </div>
                  </div>
                </div>

              </div>
            </div>

            {/* Row 3: Detailed Profile Overview + Top Skills side-by-side */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Detailed Profile Overview */}
              <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-855 rounded-3xl p-6 shadow-sm flex flex-col">
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 mb-4 shrink-0">
                  <h3 className="text-base font-black text-slate-900 dark:text-white">Detailed Profile Overview</h3>
                  <button 
                    onClick={() => setIsEditOpen(true)}
                    className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
                  >
                    View Extracted Details
                  </button>
                </div>
                
                <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1 flex-1">
                  {profileSections.map((sec, idx) => {
                    const SecIcon = sec.icon;
                    return (
                      <div 
                        key={idx} 
                        onClick={() => handleSectionClick(sec.id)}
                        className="p-2.5 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50/10 dark:bg-slate-900/40 hover:bg-slate-50/50 dark:hover:bg-slate-800/60 hover:border-slate-200 dark:hover:border-slate-700 flex items-center justify-between cursor-pointer transition-all"
                      >
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 shrink-0">
                            <SecIcon size={15} />
                          </div>
                          <div>
                            <span className="text-xs font-bold text-slate-800 dark:text-slate-200 block">{sec.name}</span>
                            <span className="text-[10px] text-slate-400 dark:text-slate-505 font-semibold block">{sec.desc}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 ${
                            sec.completed 
                              ? "bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 dark:text-emerald-450 border border-emerald-100 dark:border-emerald-800/40" 
                              : "bg-amber-50 dark:bg-amber-950/20 text-amber-600 dark:text-amber-455 border border-amber-100 dark:border-amber-800/40"
                          }`}>
                            {sec.completed ? <Check size={8} /> : <AlertCircle size={8} />}
                            <span>{sec.completed ? "Complete" : "Incomplete"}</span>
                          </span>
                          <ChevronRight size={13} className="text-slate-400" />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Top Skills & Keywords */}
              <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-855 rounded-3xl p-6 shadow-sm flex flex-col gap-6">
                <div>
                  <h3 className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-3 block">Top Skills</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {skillsList.map((skill: string, idx: number) => (
                      <span key={idx} className="text-[11px] font-semibold px-2.5 py-1 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-150 dark:border-slate-750 text-slate-705 dark:text-slate-300">
                        {skill}
                      </span>
                    ))}
                    {skillsList.length === 0 && (
                      <span className="text-xs text-slate-400 italic">No skills extracted.</span>
                    )}
                  </div>
                </div>

                <div className="border-t border-slate-100 dark:border-slate-800 pt-4 flex-1">
                  <h3 className="text-[10px] font-bold text-slate-400 dark:text-slate-505 uppercase tracking-wider mb-3 block">Top Keywords Found</h3>
                  <div className="grid grid-cols-2 gap-2 text-xs font-bold text-slate-650 dark:text-slate-400">
                    {keywordsList.map((kw: string, idx: number) => (
                      <div key={idx} className="flex items-center gap-2">
                        <Check size={12} className="text-emerald-500 shrink-0" />
                        <span>{kw}</span>
                      </div>
                    ))}
                    {keywordsList.length === 0 && (
                      <span className="col-span-2 text-xs text-slate-400 italic">No keywords extracted.</span>
                    )}
                  </div>
                </div>
              </div>

            </div>

          </div>

          {/* RIGHT SIDEBAR (AI Insights, AI Quality Score, Resume Versions) */}
          <div className="space-y-6">
            
            {/* AI Insights Card */}
            <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-855 rounded-3xl p-6 shadow-sm">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
                <h3 className="text-base font-black text-slate-900 dark:text-white">AI Insights</h3>
                <button className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer">View All</button>
              </div>

              <div className="space-y-4">
                {/* Strongest skill */}
                <div className="flex items-start gap-4">
                  <div className="w-9 h-9 rounded-xl bg-teal-50 dark:bg-teal-950/40 text-teal-600 dark:text-teal-400 flex items-center justify-center shrink-0 border border-teal-100/40 dark:border-teal-850">
                    <Code size={16} />
                  </div>
                  <div>
                    <span className="text-[11px] font-bold text-slate-400 dark:text-slate-500 block">Your strongest skill</span>
                    <span className="text-xs font-black text-slate-800 dark:text-slate-200 mt-0.5 block">{strongestSkill}</span>
                  </div>
                </div>

                {/* Top improvement area */}
                <div className="flex items-start gap-4">
                  <div className="w-9 h-9 rounded-xl bg-amber-50 dark:bg-amber-955/40 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0 border border-amber-100/40 dark:border-amber-850">
                    <TrendingUp size={16} />
                  </div>
                  <div>
                    <span className="text-[11px] font-bold text-slate-400 dark:text-slate-500 block">Top improvement area</span>
                    <span className="text-xs font-black text-slate-800 dark:text-slate-200 mt-0.5 block">{improvementArea}</span>
                  </div>
                </div>

                {/* Profile strength */}
                <div className="flex items-start gap-4">
                  <div className="w-9 h-9 rounded-xl bg-purple-50 dark:bg-purple-950/40 text-purple-650 dark:text-purple-400 flex items-center justify-center shrink-0 border border-purple-100/40 dark:border-purple-850">
                    <ShieldCheck size={16} />
                  </div>
                  <div>
                    <span className="text-[11px] font-bold text-slate-400 dark:text-slate-500 block">Profile strength</span>
                    <span className="text-xs font-black text-slate-800 dark:text-slate-200 mt-0.5 block">{profileStrength}</span>
                  </div>
                </div>

                {/* Recommended next step */}
                <div className="flex items-start gap-4">
                  <div className="w-9 h-9 rounded-xl bg-blue-50 dark:bg-blue-955/40 text-blue-650 dark:text-blue-400 flex items-center justify-center shrink-0 border border-blue-100/40 dark:border-blue-850">
                    <FileText size={16} />
                  </div>
                  <div>
                    <span className="text-[11px] font-bold text-slate-400 dark:text-slate-500 block">Recommended next step</span>
                    <span className="text-xs font-black text-slate-800 dark:text-slate-200 mt-0.5 block">{recommendedStep}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* AI Quality Score Card */}
            <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-855 rounded-3xl p-6 shadow-sm space-y-6">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                <h3 className="text-base font-black text-slate-900 dark:text-white">AI Quality Score</h3>
                <button 
                  onClick={runAIAnalysis}
                  disabled={analysisLoading}
                  className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer disabled:opacity-50"
                >
                  {analysisLoading ? "Analyzing..." : "Re-analyze"}
                </button>
              </div>

              <div className="flex items-center gap-6 justify-between">
                {/* Circular progress */}
                <div className="flex flex-col items-center shrink-0">
                  <div className="relative flex items-center justify-center">
                    <svg width="84" height="84" className="transform -rotate-90">
                      <circle cx="42" cy="42" r="36" fill="none" strokeWidth="6" className="text-slate-100 dark:text-slate-800" stroke="currentColor" />
                      <circle cx="42" cy="42" r="36" fill="none" strokeWidth="6" strokeDasharray={2 * Math.PI * 36} strokeDashoffset={2 * Math.PI * 36 - (aiQualityScore * 10 / 100) * (2 * Math.PI * 36)} strokeLinecap="round" stroke="#6366f1" className="transition-all duration-700 ease-out" />
                    </svg>
                    <div className="absolute flex flex-col items-center">
                      <span className="text-lg font-black text-slate-900 dark:text-white">{aiQualityScore}</span>
                      <span className="text-[8px] font-bold text-slate-400 dark:text-slate-500">/10</span>
                    </div>
                  </div>
                  <span className="text-[10px] font-bold text-indigo-500 mt-1.5 uppercase">
                    {skillsList.length === 0 ? "N/A" : (aiQualityScore >= 8 ? "Excellent" : (aiQualityScore >= 6 ? "Good" : "Needs Work"))}
                  </span>
                </div>

                {/* Score list */}
                <div className="flex-1 space-y-1.5 text-xs font-bold text-slate-655 dark:text-slate-400 min-w-0">
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-slate-450 dark:text-slate-505">Grammar</span>
                    <span>{skillsList.length === 0 ? 0 : aiQualityBreakdown.grammar}/10</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-slate-450 dark:text-slate-505">Formatting</span>
                    <span>{skillsList.length === 0 ? 0 : aiQualityBreakdown.formatting}/10</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-slate-455 dark:text-slate-505">Readability</span>
                    <span>{skillsList.length === 0 ? 0 : aiQualityBreakdown.readability}/10</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-slate-455 dark:text-slate-505">Projects</span>
                    <span>{skillsList.length === 0 ? 0 : aiQualityBreakdown.project_quality}/10</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-slate-455 dark:text-slate-505">Achievements</span>
                    <span>{skillsList.length === 0 ? 0 : aiQualityBreakdown.achievement_quality}/10</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-slate-455 dark:text-slate-505">Structure</span>
                    <span>{skillsList.length === 0 ? 0 : aiQualityBreakdown.structure}/10</span>
                  </div>
                </div>
              </div>

              <button 
                onClick={handleImproveWithAI}
                className="w-full py-2.5 rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50/30 dark:bg-indigo-950/20 text-indigo-655 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/45 text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-sm"
              >
                <Sparkles size={13} className="animate-pulse" />
                <span>Improve with AI</span>
              </button>
            </div>

            {/* Resume Versions Card */}
            <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-855 rounded-3xl p-6 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                <h3 className="text-base font-black text-slate-900 dark:text-white">Resume Versions</h3>
                <button className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer">View All</button>
              </div>

              <div className="space-y-2.5 max-h-[260px] overflow-y-auto pr-1">
                {resumeVersions.map((ver, idx) => (
                  <div key={idx} className="p-3 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50/10 dark:bg-slate-900/40 flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-655 dark:text-slate-455 flex items-center justify-center shrink-0">
                        <FileText size={15} />
                      </div>
                      <div className="min-w-0">
                        <span className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1 truncate">
                          {ver.version}
                          {ver.isLatest && (
                            <span className="text-[9px] font-bold px-1 py-0.2 bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 rounded border border-blue-100 dark:border-blue-800/40 shrink-0">
                              Latest
                            </span>
                          )}
                        </span>
                        <span className="text-[9px] text-slate-400 dark:text-slate-500 font-semibold block mt-0.5">{ver.date}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <button 
                        onClick={() => handlePreviewResume(ver.url)}
                        className="p-1 rounded bg-white dark:bg-slate-900 border border-slate-150 dark:border-slate-850 text-slate-450 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer hover:bg-slate-50"
                        title="Preview"
                      >
                        <Eye size={12} />
                      </button>
                      <button 
                        onClick={() => handleDownloadResumeUrl(ver.url, ver.version)}
                        className="p-1 rounded bg-white dark:bg-slate-900 border border-slate-150 dark:border-slate-850 text-slate-450 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer hover:bg-slate-50"
                        title="Download"
                      >
                        <Download size={12} />
                      </button>
                      <button 
                        onClick={() => handleDeleteResumeVersion(ver.id)}
                        className="p-1 rounded bg-white dark:bg-slate-900 border border-slate-155 border-slate-150 dark:border-slate-850 text-slate-455 hover:text-red-500 hover:border-red-205 cursor-pointer hover:bg-red-50"
                        title="Delete"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                ))}

                {resumeVersions.length === 0 && (
                  <div className="text-center py-6 text-xs text-slate-400 italic font-semibold">
                    No resume uploaded yet.
                  </div>
                )}
              </div>

              <button 
                onClick={triggerUpload}
                disabled={uploading}
                className="w-full py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-305 text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-sm disabled:opacity-50"
              >
                {uploading ? (
                  <>
                    <Loader2 size={13} className="animate-spin" />
                    <span>Uploading CV...</span>
                  </>
                ) : (
                  <>
                    <Upload size={13} />
                    <span>Upload New Resume</span>
                  </>
                )}
              </button>
            </div>

          </div>

        </div>

      </div>

      {/* 3. Slide-over Profile Edit Drawer (READ-ONLY Extracted Viewer) */}
      {isEditOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden" aria-labelledby="slide-over-title" role="dialog" aria-modal="true">
          <div className="absolute inset-0 overflow-hidden">
            {/* Backdrop */}
            <div 
              onClick={() => setIsEditOpen(false)}
              className="absolute inset-0 bg-slate-950/40 dark:bg-black/60 backdrop-blur-xs transition-opacity duration-300" 
            />
            {/* Panel */}
            <div className="absolute inset-y-0 right-0 pl-0 md:pl-10 max-w-full flex">
              <div className="w-screen max-w-2xl transform transition-all duration-300 ease-in-out bg-white dark:bg-[#0c0c0e] border-l border-slate-150 dark:border-slate-855 shadow-2xl flex flex-col h-full">
                
                {/* Header */}
                <div className="px-6 py-5 border-b border-slate-155 dark:border-slate-855 flex items-center justify-between shrink-0">
                  <div>
                    <h2 className="text-lg font-black text-slate-900 dark:text-white" id="slide-over-title">
                      Extracted Profile Details
                    </h2>
                    <p className="text-xs text-slate-400 dark:text-slate-550 font-semibold mt-1">
                      Details parsed automatically from your resume. Manual editing is disabled.
                    </p>
                  </div>
                  <button 
                    onClick={() => setIsEditOpen(false)}
                    className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors cursor-pointer"
                  >
                    <X size={18} />
                  </button>
                </div>

                {/* Info Note Banner */}
                <div className="bg-slate-50 dark:bg-slate-900/40 px-6 py-3 border-b border-slate-100 dark:border-slate-855 text-[11px] font-semibold text-slate-500 dark:text-slate-400 flex items-start gap-2 shrink-0">
                  <AlertCircle size={14} className="text-slate-400 mt-0.5 shrink-0" />
                  <span>
                    Your profile is synchronized automatically with your latest resume. To make changes or fix inaccuracies, update your resume and upload it again.
                  </span>
                </div>

                {/* Body: Tabs on left/top, Content on right/bottom */}
                <div className="flex-1 overflow-hidden flex flex-col md:flex-row min-h-0">
                  
                  {/* Tabs Selector List */}
                  <div className="w-full md:w-48 bg-slate-50/50 dark:bg-slate-900/20 border-b md:border-b-0 md:border-r border-slate-100 dark:border-slate-855 overflow-x-auto md:overflow-y-auto py-2 md:py-4 flex md:flex-col shrink-0 scrollbar-none">
                    {profileSections.map((sec) => {
                      const TabIcon = sec.icon;
                      const isTabActive = activeTab === sec.id;
                      return (
                        <button
                          key={sec.id}
                          onClick={() => setActiveTab(sec.id)}
                          className={`px-4 py-2.5 text-xs font-bold flex items-center gap-2.5 transition-all border-b-2 md:border-b-0 md:border-l-2 shrink-0 ${
                            isTabActive
                              ? "bg-slate-100 dark:bg-slate-800 text-slate-905 dark:text-white border-slate-950 dark:border-white"
                              : "text-slate-455 dark:text-slate-550 border-transparent hover:text-slate-700 dark:hover:text-slate-300"
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
                    {activeTab === "personal" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <MapPin size={16} className="text-slate-400" />
                          <span>Personal Information</span>
                        </h4>
                        <div className="space-y-4">
                          <div>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-1">Full Name</span>
                            <div className="px-3.5 py-2.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-900/30 text-xs font-semibold text-slate-800 dark:text-slate-200">
                              {editForm.name || "Not specified"}
                            </div>
                          </div>
                          <div>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-1">Email Address</span>
                            <div className="px-3.5 py-2.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-900/30 text-xs font-semibold text-slate-800 dark:text-slate-200">
                              {editForm.email || "Not specified"}
                            </div>
                          </div>
                          <div>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-1">Phone Number</span>
                            <div className="px-3.5 py-2.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-900/30 text-xs font-semibold text-slate-800 dark:text-slate-200">
                              {editForm.phone || "Not specified"}
                            </div>
                          </div>
                          <div>
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-1">Location / Address</span>
                            <div className="px-3.5 py-2.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-900/30 text-xs font-semibold text-slate-800 dark:text-slate-200">
                              {editForm.address || "Not specified"}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* SUMMARY TAB */}
                    {activeTab === "summary" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <FileText size={16} className="text-slate-400" />
                          <span>Professional Summary</span>
                        </h4>
                        <div>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-1.5">Summary</span>
                          <div className="px-4 py-3 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-900/30 text-xs font-semibold text-slate-700 dark:text-slate-350 leading-relaxed whitespace-pre-wrap">
                            {editForm.summary || "No professional summary extracted."}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* SKILLS TAB */}
                    {activeTab === "skills" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <Code size={16} className="text-slate-400" />
                          <span>Extracted Skills</span>
                        </h4>
                        <div>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-3">Skills List</span>
                          <div className="flex flex-wrap gap-2">
                            {skillsList.map((skill: string, idx: number) => (
                              <span key={idx} className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-slate-50 dark:bg-slate-850 border border-slate-100 dark:border-slate-750 text-slate-700 dark:text-slate-300">
                                {skill}
                              </span>
                            ))}
                            {skillsList.length === 0 && (
                              <span className="text-xs text-slate-450 italic font-semibold">No skills extracted.</span>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* EXPERIENCE TAB */}
                    {activeTab === "experience" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <Briefcase size={16} className="text-slate-400" />
                          <span>Work Experience</span>
                        </h4>
                        <div className="space-y-4">
                          {editForm.experienceList.map((exp: any, index: number) => (
                            <div key={index} className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50/10 dark:bg-slate-900/20 space-y-2">
                              <div className="flex justify-between items-start">
                                <div>
                                  <h5 className="text-xs font-bold text-slate-900 dark:text-white">{exp.role || "Role not specified"}</h5>
                                  <p className="text-[11px] text-slate-550 dark:text-slate-400 font-semibold">{exp.company || "Company not specified"}</p>
                                </div>
                                {exp.years ? (
                                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                                    {exp.years} yrs
                                  </span>
                                ) : null}
                              </div>
                              {exp.description && (
                                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed whitespace-pre-wrap pt-1 border-t border-slate-100/50 dark:border-slate-800/50">
                                  {exp.description}
                                </p>
                              )}
                            </div>
                          ))}
                          {editForm.experienceList.length === 0 && (
                            <div className="text-center py-8 text-xs text-slate-400 border border-dashed border-slate-200 dark:border-slate-800 rounded-2xl font-semibold">
                              No experience history extracted.
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* EDUCATION TAB */}
                    {activeTab === "education" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <GraduationCap size={16} className="text-slate-400" />
                          <span>Education</span>
                        </h4>
                        <div className="space-y-4">
                          {editForm.educationList.map((edu: any, index: number) => (
                            <div key={index} className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50/10 dark:bg-slate-900/20 flex justify-between items-start">
                              <div className="space-y-1">
                                <h5 className="text-xs font-bold text-slate-900 dark:text-white">{edu.degree || "Degree not specified"}</h5>
                                <p className="text-[11px] text-slate-550 dark:text-slate-400 font-semibold">{edu.school || "School/University not specified"}</p>
                              </div>
                              {edu.year && (
                                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                                  {edu.year}
                                </span>
                              )}
                            </div>
                          ))}
                          {editForm.educationList.length === 0 && (
                            <div className="text-center py-8 text-xs text-slate-400 border border-dashed border-slate-200 dark:border-slate-800 rounded-2xl font-semibold">
                              No education history extracted.
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* PROJECTS TAB */}
                    {activeTab === "projects" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <Folder size={16} className="text-slate-400" />
                          <span>Projects</span>
                        </h4>
                        <div className="space-y-4">
                          {editForm.projectList.map((proj: any, index: number) => (
                            <div key={index} className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50/10 dark:bg-slate-900/20 space-y-2">
                              <div className="flex justify-between items-center">
                                <h5 className="text-xs font-bold text-slate-900 dark:text-white">{proj.name || "Project name not specified"}</h5>
                                {proj.link && (
                                  <a 
                                    href={proj.link} 
                                    target="_blank" 
                                    rel="noopener noreferrer" 
                                    className="text-[10px] font-bold text-blue-605 dark:text-blue-400 hover:underline flex items-center gap-1 cursor-pointer"
                                  >
                                    <span>Link</span>
                                    <Globe size={10} />
                                  </a>
                                )}
                              </div>
                              {proj.description && (
                                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed whitespace-pre-wrap pt-1 border-t border-slate-100/50 dark:border-slate-800/50">
                                  {proj.description}
                                </p>
                              )}
                            </div>
                          ))}
                          {editForm.projectList.length === 0 && (
                            <div className="text-center py-8 text-xs text-slate-400 border border-dashed border-slate-200 dark:border-slate-800 rounded-2xl font-semibold">
                              No projects history extracted.
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* CERTIFICATIONS TAB */}
                    {activeTab === "certifications" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <Award size={16} className="text-slate-400" />
                          <span>Certifications</span>
                        </h4>
                        <div>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-505 block mb-3">Extracted Certifications</span>
                          <div className="flex flex-wrap gap-2">
                            {editForm.certifications ? (
                              editForm.certifications.split(",").map((cert: string, idx: number) => {
                                const clean = cert.trim();
                                if (!clean) return null;
                                return (
                                  <span key={idx} className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-750 text-slate-700 dark:text-slate-300">
                                    {clean}
                                  </span>
                                );
                              })
                            ) : null}
                            {(!editForm.certifications || !editForm.certifications.trim()) && (
                              <span className="text-xs text-slate-455 italic font-semibold">No certifications extracted.</span>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* ACHIEVEMENTS TAB */}
                    {activeTab === "achievements" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <Trophy size={16} className="text-slate-400" />
                          <span>Achievements</span>
                        </h4>
                        <div className="space-y-3">
                          {editForm.achievementsList.map((ach: string, index: number) => {
                            if (!ach.trim()) return null;
                            return (
                              <div key={index} className="flex gap-2.5 items-start p-3 rounded-2xl border border-slate-100 dark:border-slate-800 bg-slate-50/10 dark:bg-slate-900/20 text-xs font-semibold text-slate-700 dark:text-slate-300">
                                <CheckCircle2 size={14} className="text-emerald-500 mt-0.5 shrink-0" />
                                <span className="leading-relaxed">{ach}</span>
                              </div>
                            );
                          })}
                          {editForm.achievementsList.length === 0 && (
                            <div className="text-center py-8 text-xs text-slate-400 border border-dashed border-slate-200 dark:border-slate-800 rounded-2xl font-semibold">
                              No achievements extracted.
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* LANGUAGES TAB */}
                    {activeTab === "languages" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <Languages size={16} className="text-slate-400" />
                          <span>Languages</span>
                        </h4>
                        <div>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-505 block mb-3">Extracted Languages</span>
                          <div className="flex flex-wrap gap-2">
                            {editForm.languages ? (
                              editForm.languages.split(",").map((lang: string, idx: number) => {
                                const clean = lang.trim();
                                if (!clean) return null;
                                return (
                                  <span key={idx} className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-750 text-slate-700 dark:text-slate-300">
                                    {clean}
                                  </span>
                                );
                              })
                            ) : null}
                            {(!editForm.languages || !editForm.languages.trim()) && (
                              <span className="text-xs text-slate-455 italic font-semibold">No languages extracted.</span>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* SOCIAL LINKS TAB */}
                    {activeTab === "socials" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <Globe size={16} className="text-slate-400" />
                          <span>Social Links</span>
                        </h4>
                        <div className="space-y-4">
                          {editForm.linkedin && (
                            <div>
                              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-1">LinkedIn Profile URL</span>
                              <a 
                                href={editForm.linkedin} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                className="px-3.5 py-2.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-900/30 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-2"
                              >
                                <Globe size={13} />
                                <span>{editForm.linkedin}</span>
                              </a>
                            </div>
                          )}
                          {editForm.github && (
                            <div>
                              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-505 block mb-1">GitHub Profile URL</span>
                              <a 
                                href={editForm.github} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                className="px-3.5 py-2.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-900/30 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-2"
                              >
                                <Code size={13} />
                                <span>{editForm.github}</span>
                              </a>
                            </div>
                          )}
                          {editForm.portfolio && (
                            <div>
                              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-1">Portfolio Website URL</span>
                              <a 
                                href={editForm.portfolio} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                className="px-3.5 py-2.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-900/30 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-2"
                              >
                                <Globe size={13} />
                                <span>{editForm.portfolio}</span>
                              </a>
                            </div>
                          )}
                          {!editForm.linkedin && !editForm.github && !editForm.portfolio && (
                            <div className="text-center py-8 text-xs text-slate-400 border border-dashed border-slate-200 dark:border-slate-800 rounded-2xl font-semibold">
                              No social links extracted.
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                  </div>

                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-slate-150 dark:border-slate-850 bg-slate-50/50 dark:bg-slate-900/30 flex items-center justify-between gap-3 shrink-0">
                  <button 
                    onClick={() => {
                      setIsEditOpen(false);
                      triggerUpload();
                    }}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-950 dark:bg-slate-50 hover:bg-slate-900 dark:hover:bg-slate-205 text-white dark:text-slate-955 text-xs font-bold cursor-pointer transition-all shadow-md"
                  >
                    <Upload size={13} />
                    <span>Upload Resume to Update</span>
                  </button>
                  <button 
                    onClick={() => setIsEditOpen(false)}
                    className="px-4 py-2 border border-slate-200 dark:border-slate-800 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-bold text-slate-700 dark:text-slate-300 cursor-pointer transition-colors"
                  >
                    Close
                  </button>
                </div>

              </div>
            </div>

          </div>
        </div>
      )}\n
      {/* 4. PDF Preview Modal */}
      {showPreviewModal && previewUrl && (
        <div className="fixed inset-0 z-50 bg-black/50 dark:bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 rounded-3xl w-full max-w-4xl h-[85vh] shadow-2xl flex flex-col overflow-hidden">
            
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-150 dark:border-slate-800 px-6 py-4">
              <div className="flex items-center gap-2">
                <FileText size={16} className="text-indigo-505" />
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">Resume Preview</h3>
                <span className="text-[9px] font-bold text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded uppercase tracking-wider">PDF</span>
              </div>
              <div className="flex items-center gap-2">
                <a 
                  href={`${typeof window !== "undefined" && window.location.hostname === "localhost" ? "http://127.0.0.1:8000" : `http://${window.location.hostname}:8000`}${previewUrl}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-bold text-slate-655 dark:text-slate-350 transition-colors"
                >
                  <ExternalLink size={12} />
                  <span>Open in new tab</span>
                </a>
                <button 
                  onClick={() => setShowPreviewModal(false)}
                  className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors cursor-pointer"
                >
                  <X size={18} />
                </button>
              </div>
            </div>
            
            {/* PDF Embed */}
            <div className="flex-1 bg-slate-100 dark:bg-slate-950">
              <iframe
                src={`${typeof window !== "undefined" && window.location.hostname === "localhost" ? "http://127.0.0.1:8000" : `http://${window.location.hostname}:8000`}${previewUrl}`}
                className="w-full h-full border-none"
                title="Resume Preview"
              />
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
