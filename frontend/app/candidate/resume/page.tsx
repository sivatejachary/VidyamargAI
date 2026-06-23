"use client";
 
import { useEffect, useState, useRef } from "react";
import { apiService, getBackendBaseUrl } from "@/services/api";
import { useAuthStore } from "@/store/authStore";
import { useWebSockets } from "@/hooks/useWebSockets";
import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { 
  Download, Trash2, Edit, Eye, RotateCcw, Upload, Plus, 
  Sparkles, CheckCircle2, Loader2, FileText, ChevronRight, 
  X, Check, AlertCircle, ShieldCheck, TrendingUp, Zap, 
  AlertTriangle, Award, Link2, ExternalLink, GraduationCap, 
  Briefcase, MapPin, Mail, Phone, Camera, Code, Folder, Trophy,
  Globe, Languages, User
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Drawer } from "@/components/ui/Drawer";
import { Modal } from "@/components/ui/Modal";
import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { ProgressBar, ProgressRing } from "@/components/ui/Progress";
import { Skeleton } from "@/components/ui/Skeleton";

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
  // Caching helper functions
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

  const queryClient = useQueryClient();
  const { fullName, email, updateUser } = useAuthStore();

  const clearCache = (newProfile?: any) => {
    if (typeof window !== "undefined") {
      // Clear Resume cache
      sessionStorage.removeItem("resume_profile");
      sessionStorage.removeItem("resume_versions");
      sessionStorage.removeItem("resume_analysis");
      
      // Clear Jobs cache
      sessionStorage.removeItem("jobs_list");
      sessionStorage.removeItem("jobs_skill_gaps");
      sessionStorage.removeItem("jobs_recommendations");
      sessionStorage.removeItem("jobs_run_id");

      // Clear Skill Lab cache
      sessionStorage.removeItem("skill_lab_profile");
      sessionStorage.removeItem("skill_lab_streak");
      sessionStorage.removeItem("skill_lab_hoursLearned");
      sessionStorage.removeItem("skill_lab_completedCoursesCount");
      sessionStorage.removeItem("skill_lab_earnedCertsCount");
      sessionStorage.removeItem("skill_lab_readinessScore");
      sessionStorage.removeItem("skill_lab_xp");
      sessionStorage.removeItem("skill_lab_level");

      // Clear LMS Explorer cache
      sessionStorage.removeItem("lms_courses");
      sessionStorage.removeItem("lms_enrollments");
    }

    if (newProfile) {
      const newName = newProfile.parsed_name || newProfile.user?.full_name;
      const newEmail = newProfile.parsed_email || newProfile.user?.email;
      if (newName && (newName !== fullName || newEmail !== email)) {
        updateUser(newName, newEmail);
      }
    }

    // Invalidate React Query caches
    queryClient.invalidateQueries();
  };
  const [profile, setProfile] = useState<any>(() => getCachedValue("resume_profile", null));
  const [resumeVersions, setResumeVersions] = useState<ResumeVersion[]>(() => getCachedValue("resume_versions", []));
  const [analysisData, setAnalysisData] = useState<any>(() => getCachedValue("resume_analysis", null));
  const [loading, setLoading] = useState(() => {
    if (typeof window !== "undefined") {
      return !sessionStorage.getItem("resume_profile");
    }
    return true;
  });
  const [uploading, setUploading] = useState(false);
  const [uploadStep, setUploadStep] = useState(0);
  const [uploadProgress, setUploadProgress] = useState(0);
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

  const [fastMode, setFastMode] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load all dashboard data
  const loadDashboardData = async (forceRefresh = false) => {
    const hasCache = typeof window !== "undefined" && 
                     sessionStorage.getItem("resume_profile") && 
                     sessionStorage.getItem("resume_versions") && 
                     sessionStorage.getItem("resume_analysis");

    if (!hasCache || forceRefresh) {
      setLoading(true);
    }

    try {
      const prof = await apiService.getProfile();
      setProfile(prof);
      setCachedValue("resume_profile", prof);
      if (forceRefresh) {
        clearCache(prof);
      } else {
        const newName = prof.parsed_name || prof.user?.full_name;
        const newEmail = prof.parsed_email || prof.user?.email;
        if (newName && (newName !== fullName || newEmail !== email)) {
          updateUser(newName, newEmail);
        }
      }

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
      let formattedResumes: ResumeVersion[] = [];
      try {
        const resumes = await apiService.getResumes();
        if (resumes && Array.isArray(resumes)) {
          formattedResumes = resumes.map((res: any, idx: number) => {
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
          setCachedValue("resume_versions", formattedResumes);
        }
      } catch (err) {
        console.error("Failed to load resume versions:", err);
      }

      // Load AI analysis
      if (!hasCache || forceRefresh) {
        setAnalysisLoading(true);
      }
      try {
        const analysis = await apiService.analyzeResume();
        if (analysis) {
          setAnalysisData(analysis);
          setCachedValue("resume_analysis", analysis);
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

  // Connect WebSocket for real-time progress updates
  const clientId = profile?.id ? `candidate_${profile.id}` : "";
  const { addMessageListener } = useWebSockets(clientId);

  useEffect(() => {
    if (!clientId) return;
    
    const removeListener = addMessageListener((event: any) => {
      console.log("WebSocket event in ResumeBuilder:", event);
      if (event.type === "resume_processing") {
        setUploading(true);
        // Translate state status to our step indicator
        let stepNum = 1;
        if (event.status === "uploading") stepNum = 1;
        else if (event.status === "extracting_text") stepNum = 2;
        else if (event.status === "parsing_resume") stepNum = 3;
        else if (event.status === "building_profile") stepNum = 4;
        else if (event.status === "generating_embeddings") stepNum = 5;
        
        setUploadStep(stepNum);
        setUploadProgress(event.progress || 0);
      } else if (event.type === "resume_processed") {
        setUploadStep(5);
        setUploadProgress(100);
        setSuccessMsg("Resume uploaded and parsed successfully! AI profile is ready.");
        setUploading(false);
        setTimeout(() => setSuccessMsg(""), 5000);
        loadDashboardData(true);
      } else if (event.type === "resume_failed") {
        setErrorMsg(`Failed to parse resume: ${event.error || "Unknown error"}`);
        setUploading(false);
        setTimeout(() => setErrorMsg(""), 5000);
        loadDashboardData(true);
      }
    });
    
    return () => {
      removeListener();
    };
  }, [clientId, addMessageListener]);

  // Adaptive Polling Fallback
  useEffect(() => {
    if (!profile) return;
    
    const isProcessing = ["uploading", "extracting_text", "parsing_resume", "building_profile", "generating_embeddings"].includes(profile.resume_status);
    if (!isProcessing) return;

    setUploading(true);
    let stepNum = 1;
    if (profile.resume_status === "uploading") stepNum = 1;
    else if (profile.resume_status === "extracting_text") stepNum = 2;
    else if (profile.resume_status === "parsing_resume") stepNum = 3;
    else if (profile.resume_status === "building_profile") stepNum = 4;
    else if (profile.resume_status === "generating_embeddings") stepNum = 5;
    setUploadStep(stepNum);
    setUploadProgress(profile.resume_progress || 0);

    let pollInterval = 2000; // start with 2 seconds
    let elapsed = 0;
    let timer: NodeJS.Timeout;

    const poll = async () => {
      try {
        const prof = await apiService.getProfile();
        setProfile(prof);
        setCachedValue("resume_profile", prof);
        
        const nextIsProcessing = ["uploading", "extracting_text", "parsing_resume", "building_profile", "generating_embeddings"].includes(prof.resume_status);
        if (!nextIsProcessing) {
          setUploading(false);
          loadDashboardData(true);
          return;
        }

        let nextStep = 1;
        if (prof.resume_status === "uploading") nextStep = 1;
        else if (prof.resume_status === "extracting_text") nextStep = 2;
        else if (prof.resume_status === "parsing_resume") nextStep = 3;
        else if (prof.resume_status === "building_profile") nextStep = 4;
        else if (prof.resume_status === "generating_embeddings") nextStep = 5;
        setUploadStep(nextStep);
        setUploadProgress(prof.resume_progress || 0);

      } catch (err) {
        console.error("Error in fallback poll:", err);
      }

      elapsed += pollInterval;
      if (elapsed >= 60000) {
        pollInterval = 10000; // throttle to 10 seconds after 1 minute
      }
      timer = setTimeout(poll, pollInterval);
    };

    timer = setTimeout(poll, pollInterval);

    return () => {
      clearTimeout(timer);
    };
  }, [profile?.resume_status]);

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
    setUploadStep(1);
    setUploadProgress(5);
    setErrorMsg("");
    setSuccessMsg("");

    try {
      await apiService.uploadResume(selectedFile, fastMode);
      // Immediately fetch candidate profile to trigger adaptive polling status loop
      const prof = await apiService.getProfile();
      setProfile(prof);
      setCachedValue("resume_profile", prof);
    } catch (err: any) {
      setErrorMsg(err.message || "Resume upload failed.");
      setUploading(false);
      setUploadProgress(0);
      setUploadStep(0);
      setTimeout(() => setErrorMsg(""), 5000);
    }
  };

  const handleDeleteResumeVersion = async (id: number) => {
    if (!confirm("Are you sure you want to delete this resume version?")) return;
    try {
      await apiService.deleteResumeVersion(id);
      setSuccessMsg("Resume version deleted successfully.");
      setTimeout(() => setSuccessMsg(""), 3000);
      
      // Clear cache and reset state ("if delete remove everything")
      clearCache();
      setProfile(null);
      setResumeVersions([]);
      setAnalysisData(null);
      
      await loadDashboardData(true);
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
    const backendUrl = getBackendBaseUrl();
    
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
      await loadDashboardData(true);
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

  // High-demand skills list for comparison
  const highDemandSkills = ["React", "Next.js", "TypeScript", "Node.js", "Python", "FastAPI", "Docker", "AWS", "SQL", "System Design", "Git", "Flutter"];
  const missingSkills = highDemandSkills.filter(s => !skillsList.some((cs: string) => cs.toLowerCase().includes(s.toLowerCase())));

  const courseMappings = [
    { title: "React & Next.js App Router", skills: ["React", "Next.js", "TypeScript"], id: "react-nextjs-app-router" },
    { title: "FastAPI Backend Development", skills: ["FastAPI", "Node.js"], id: "fastapi-backend-development" },
    { title: "Python Complete Bootcamp", skills: ["Python"], id: "python-complete-bootcamp" },
    { title: "SQL Masterclass", skills: ["SQL"], id: "sql-masterclass" },
    { title: "System Design & Scalability", skills: ["System Design"], id: "system-design-scalability" },
    { title: "AWS Cloud Practitioner", skills: ["AWS", "Docker"], id: "aws-cloud-practitioner" },
    { title: "Flutter Development Masterclass", skills: ["Flutter"], id: "flutter-development-masterclass" },
    { title: "Machine Learning Fundamentals", skills: ["Machine Learning", "Data Science"], id: "machine-learning-fundamentals" },
  ];

  const recommendedCourses = courseMappings.filter(course => 
    course.skills.some(skill => missingSkills.includes(skill))
  ).slice(0, 3);

  // Dynamic missing fields based on empty candidate fields
  const missingItems: string[] = [];
  if (!profile?.certifications) missingItems.push("Certifications");
  if (!profile?.achievements || profile?.achievements === "[]") missingItems.push("Achievements");
  if (!profile?.linkedin) missingItems.push("LinkedIn Profile");
  if (!profile?.portfolio) missingItems.push("Portfolio Link");

  // Summaries
  let educationCount = 0;
  try { educationCount = profile?.education ? JSON.parse(profile.education).length : 0; } catch { educationCount = 0; }

  let experienceCount = 0;
  try { experienceCount = profile?.experience ? JSON.parse(profile.experience).length : 0; } catch { experienceCount = 0; }

  let experienceYears = 0;
  if (profile?.experience_years !== undefined && profile?.experience_years !== null) {
    experienceYears = profile.experience_years;
  } else {
    try {
      const expArr = profile?.experience ? JSON.parse(profile.experience) : [];
      experienceYears = expArr.reduce((sum: number, exp: any) => sum + (Number(exp.years) || 0), 0);
    } catch {
      experienceYears = 0;
    }
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
      completed: experienceCount > 0 
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
      <div className="flex-1 min-h-screen bg-background text-foreground p-6 md:p-8 font-sans">
        {/* Skeleton Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <div className="h-8 w-56 bg-muted rounded-xl animate-pulse" />
            <div className="h-4 w-80 bg-muted rounded-lg animate-pulse mt-2" />
          </div>
          <div className="flex items-center gap-3">
            <div className="h-9 w-28 bg-muted rounded-xl animate-pulse" />
            <div className="h-9 w-36 bg-muted rounded-xl animate-pulse" />
          </div>
        </div>
        {/* Skeleton Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          {[1, 2, 3].map(i => (
            <div key={i} className="bg-card border border-border rounded-2xl p-6 animate-pulse">
              <div className="h-4 w-24 bg-muted rounded mb-4" />
              <div className="h-10 w-16 bg-muted rounded-xl mb-2" />
              <div className="h-3 w-32 bg-muted rounded" />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-card border border-border rounded-2xl p-6 h-64 animate-pulse">
            <div className="h-4 w-36 bg-muted rounded mb-4" />
            <div className="space-y-3">
              {[1, 2, 3, 4].map(i => <div key={i} className="h-3 bg-muted rounded" />)}
            </div>
          </div>
          <div className="bg-card border border-border rounded-2xl p-6 h-64 animate-pulse">
            <div className="h-4 w-36 bg-muted rounded mb-4" />
            <div className="space-y-3">
              {[1, 2, 3, 4].map(i => <div key={i} className="h-3 bg-muted rounded" />)}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (resumeVersions.length === 0) {
    return (
      <div className="flex-1 min-h-screen bg-background text-foreground p-6 md:p-8 font-sans flex items-center justify-center">
        <div className="max-w-md w-full space-y-4">
          {successMsg && <Alert variant="success">{successMsg}</Alert>}
          {errorMsg && <Alert variant="error">{errorMsg}</Alert>}

          {/* Hidden file input */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleResumeUpload}
            accept="application/pdf"
            className="hidden"
          />

          <EmptyState
            title="No Resume Uploaded"
            description="Upload your resume to extract profile details, analyze skills, and get personalized course recommendations."
            icon={<FileText size={36} />}
            action={
              <div className="flex flex-col items-center gap-3 w-full">
                <Button 
                  onClick={triggerUpload}
                  disabled={uploading}
                  className="w-full sm:w-auto mt-4 shrink-0"
                >
                  {uploading ? (
                    <>
                      <Loader2 size={16} className="animate-spin mr-2 shrink-0" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload size={16} className="mr-2 shrink-0" />
                      Upload Resume
                    </>
                  )}
                </Button>
                <label className="flex items-center gap-2 text-xs select-none cursor-pointer mt-2 bg-white/5 border border-white/10 rounded-lg py-1.5 px-3 hover:bg-white/10 transition-colors">
                  <input
                    type="checkbox"
                    checked={fastMode}
                    onChange={(e) => setFastMode(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-900 text-violet-600 focus:ring-violet-500"
                  />
                  <span className="font-medium text-slate-300">⚡ Instant Mode (milliseconds)</span>
                </label>
              </div>
            }
          />

          {/* Upload Stepper Modal */}
          {uploading && (
            <Modal
              isOpen={uploading}
              onClose={() => {}}
              title="Processing Resume"
              className="max-w-md"
            >
              <div className="flex flex-col gap-6 py-2">
                <div className="space-y-1.5 text-center">
                  <span className="text-11 font-bold text-muted-foreground uppercase tracking-wider">
                    Ingestion Pipeline
                  </span>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Tush AI is analyzing your CV and extracting structural data.
                  </p>
                </div>

                {/* Stepper Steps */}
                <div className="space-y-4 my-2">
                  {[
                    { step: 1, label: "Uploading Document" },
                    { step: 2, label: "Extracting Bio & Location" },
                    { step: 3, label: "Parsing Skills & Experience" },
                    { step: 4, label: "Analyzing Quality Metrics" },
                    { step: 5, label: "Syncing Profile Data" }
                  ].map((s) => {
                    const isCompleted = uploadStep > s.step;
                    const isActive = uploadStep === s.step;
                    return (
                      <div key={s.step} className="flex items-center gap-3.5">
                        <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 border transition-all ${
                          isCompleted 
                            ? "bg-success border-success text-success-foreground"
                            : isActive
                              ? "bg-primary border-primary text-primary-foreground animate-pulse"
                              : "border-border text-muted-foreground"
                        }`}>
                          {isCompleted ? <Check size={12} strokeWidth={3} /> : s.step}
                        </div>
                        <span className={`text-xs font-semibold ${
                          isActive 
                            ? "text-foreground font-bold" 
                            : isCompleted 
                              ? "text-muted-foreground line-through opacity-75"
                              : "text-muted-foreground"
                        }`}>
                          {s.label}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {/* Progress Bar */}
                <div className="space-y-2 mt-2">
                  <div className="flex justify-between items-center text-xs font-semibold">
                    <span className="text-muted-foreground">Overall progress</span>
                    <span className="text-foreground">{uploadProgress}%</span>
                  </div>
                  <ProgressBar value={uploadProgress} />
                </div>
              </div>
            </Modal>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 min-h-screen bg-background text-foreground p-6 md:p-8 font-sans transition-colors duration-300">
      
      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleResumeUpload}
        accept="application/pdf"
        className="hidden"
      />

      {/* Upload Stepper Modal */}
      {uploading && (
        <Modal
          isOpen={uploading}
          onClose={() => {}}
          title="Processing Resume"
          className="max-w-md"
        >
          <div className="flex flex-col gap-6 py-2">
            <div className="space-y-1.5 text-center">
              <span className="text-11 font-bold text-muted-foreground uppercase tracking-wider">
                Ingestion Pipeline
              </span>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Tush AI is analyzing your CV and extracting structural data.
              </p>
            </div>

            {/* Stepper Steps */}
            <div className="space-y-4 my-2">
              {[
                { step: 1, label: "Uploading Document" },
                { step: 2, label: "Extracting Bio & Location" },
                { step: 3, label: "Parsing Skills & Experience" },
                { step: 4, label: "Analyzing Quality Metrics" },
                { step: 5, label: "Syncing Profile Data" }
              ].map((s) => {
                const isCompleted = uploadStep > s.step;
                const isActive = uploadStep === s.step;
                return (
                  <div key={s.step} className="flex items-center gap-3.5">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 border transition-all ${
                      isCompleted 
                        ? "bg-success border-success text-success-foreground"
                        : isActive
                          ? "bg-primary border-primary text-primary-foreground animate-pulse"
                          : "border-border text-muted-foreground"
                    }`}>
                      {isCompleted ? <Check size={12} strokeWidth={3} /> : s.step}
                    </div>
                    <span className={`text-xs font-semibold ${
                      isActive 
                        ? "text-foreground font-bold" 
                        : isCompleted 
                          ? "text-muted-foreground line-through opacity-75"
                          : "text-muted-foreground"
                    }`}>
                      {s.label}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Progress Bar */}
            <div className="space-y-2 mt-2">
              <div className="flex justify-between items-center text-xs font-semibold">
                <span className="text-muted-foreground">Overall progress</span>
                <span className="text-foreground">{uploadProgress}%</span>
              </div>
              <ProgressBar value={uploadProgress} />
            </div>
          </div>
        </Modal>
      )}

      <div className="max-w-1440 mx-auto space-y-6">
        
        {/* Status Alerts */}
        {successMsg && (
          <Alert variant="success">
            {successMsg}
          </Alert>
        )}

        {errorMsg && (
          <Alert variant="error">
            {errorMsg}
          </Alert>
        )}

        {/* 1. Header Area */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-black tracking-tight text-foreground dark:text-white">My Resume Profile</h1>
            <p className="text-slate-500 dark:text-slate-455 mt-1.5 text-sm leading-relaxed max-w-2xl font-medium">
              Your resume has been parsed and your profile is ready. Keep it updated for better opportunities.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button 
              variant="outline"
              size="sm"
              onClick={handleDownloadLatestResume}
              className="shrink-0"
            >
              <Download size={14} />
              <span>Download Resume</span>
            </Button>
            <Button 
              variant="outline"
              size="sm"
              onClick={() => setIsEditOpen(true)}
              className="shrink-0"
            >
              <Eye size={14} />
              <span>View Profile Details</span>
            </Button>
          </div>
        </div>

        {/* 2. Main content 3-column Grid layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* LEFT 2 COLUMNS */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* MOBILE ONLY VERSION OF THE PROFILE CARD (Shown on screens < md) */}
            <Card className="block md:hidden border border-border bg-card p-4 shadow-sm space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="relative shrink-0">
                    <div className="w-14 h-14 rounded-full overflow-hidden border border-border bg-muted flex items-center justify-center text-foreground text-xl font-black shadow-sm">
                      {avatarLetter}
                    </div>
                    <button 
                      onClick={triggerUpload}
                      disabled={uploading}
                      className="absolute bottom-0 right-0 w-6 h-6 rounded-full bg-background border border-border text-muted-foreground flex items-center justify-center hover:bg-muted transition-all shadow-sm cursor-pointer"
                      title="Upload Resume to Update Profile"
                    >
                      {uploading ? <Loader2 size={10} className="animate-spin" /> : <Upload size={10} />}
                    </button>
                  </div>
                  
                  <div className="min-w-0">
                    <div className="flex flex-col items-start gap-1">
                      <h2 className="text-sm font-black text-foreground truncate max-w-120" title={displayName || undefined}>
                        {displayName}
                      </h2>
                      <Badge variant="success">Verified</Badge>
                    </div>
                  </div>
                </div>

                <ProgressRing 
                  value={completionScore} 
                  size={72} 
                  strokeWidth={5} 
                />
              </div>

              <div className="space-y-1 text-xs font-semibold text-muted-foreground pt-2 border-t border-border">
                <div className="flex items-center gap-2">
                  <User size={12} className="text-muted-foreground shrink-0" />
                  <span className="truncate">{getFirstRole() || "Not specified"}</span>
                </div>
                <div className="flex items-center gap-2">
                  <MapPin size={12} className="text-muted-foreground shrink-0" />
                  <span className="truncate">{profile?.address || "Not specified"}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Mail size={12} className="text-muted-foreground shrink-0" />
                  <span className="truncate" title={displayEmail}>{displayEmail}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Phone size={12} className="text-muted-foreground shrink-0" />
                  <span className="truncate">{profile?.phone || "Not specified"}</span>
                </div>
              </div>

              {/* Horizontal Divider Line */}
              <div className="border-t border-border my-4" />

              {/* Missing Section */}
              <div className="space-y-3">
                <span className="text-xs font-black text-muted-foreground uppercase tracking-wider block">
                  Missing ({100 - completionScore}%)
                </span>
                
                {/* Mobile Missing Cards */}
                <div className="space-y-2">
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
                          className="flex items-center justify-between p-3 rounded-xl border border-border bg-background shadow-xs cursor-pointer hover:bg-muted transition-colors"
                        >
                          <div className="flex items-center gap-2.5">
                            <div className="p-1.5 rounded-lg bg-success/10 text-success border border-success/20 shrink-0">
                              <IconComponent size={14} />
                            </div>
                            <span className="text-xs font-semibold text-foreground">{item}</span>
                          </div>
                          
                          <div className="flex items-center gap-1.5">
                            <Badge variant="destructive">Missing</Badge>
                            <ChevronRight size={14} className="text-muted-foreground" />
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="p-3 rounded-xl border border-border bg-background text-center text-xs text-success font-bold">
                      All sections complete! ✓
                    </div>
                  )}
                </div>

                {/* Complete your profile box */}
                <div className="p-4 rounded-2xl bg-success/5 border border-success/20 flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div className="flex items-center gap-3 text-left w-full sm:w-auto">
                    <div className="w-10 h-10 rounded-xl bg-background border border-success/30 flex items-center justify-center shrink-0 shadow-xs text-success">
                      <FileText size={18} />
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-xs font-black text-foreground">Complete your profile</h4>
                      <p className="text-10 text-muted-foreground mt-0.5 leading-relaxed">
                        Add missing details to get better job matches.
                      </p>
                    </div>
                  </div>
                  
                  <Button 
                    onClick={handleCompleteNow}
                    size="sm"
                    className="w-full sm:w-auto text-xs py-2 h-auto"
                  >
                    Update Profile
                  </Button>
                </div>
                
              </div>
            </Card>

            {/* DESKTOP ONLY VERSION OF THE PROFILE CARD (Shown on screens >= md) */}
            <Card className="hidden md:grid grid-cols-1 md:grid-cols-2 gap-6">
              
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
                    <h2 className="text-xl font-black text-foreground dark:text-white truncate max-w-150" title={displayName || undefined}>
                      {displayName}
                    </h2>
                    <span className="inline-flex px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950/40 text-9 font-bold text-blue-600 dark:text-blue-400 border border-blue-100 dark:border-blue-800/50">
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
                  <span className="text-10 font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">Profile Completion</span>
                  
                  <div className="relative flex items-center justify-center my-1.5">
                    <svg width="86" height="86" className="transform -rotate-90">
                      <circle cx="43" cy="43" r="37" fill="none" strokeWidth="6" className="text-slate-100 dark:text-slate-800" stroke="currentColor" />
                      <circle cx="43" cy="43" r="37" fill="none" strokeWidth="6" strokeDasharray={2 * Math.PI * 37} strokeDashoffset={2 * Math.PI * 37 - (completionScore / 100) * (2 * Math.PI * 37)} strokeLinecap="round" stroke="#0ea5e9" className="transition-all duration-700 ease-out" />
                    </svg>
                    <div className="absolute text-lg font-black text-foreground dark:text-white">{completionScore}%</div>
                  </div>
                  <span className="text-10 font-bold text-emerald-500 dark:text-emerald-400">
                    {completionScore >= 75 ? "Good Progress!" : (completionScore > 0 ? "Started" : (resumeVersions.length > 0 ? "Resume Uploaded" : "No Resume Uploaded"))}
                  </span>
                </div>

                <div className="flex-1 flex flex-col justify-between h-full gap-3 w-full text-center sm:text-left min-w-0">
                  <div>
                    <span className="text-10 font-bold text-slate-450 dark:text-slate-400 uppercase tracking-wider block">Missing ({100 - completionScore}%)</span>
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

            </Card>

            {/* Row 2: Profile Summary Grid (6 widgets) */}
            <Card className="space-y-4">
              <h3 className="text-base font-black text-foreground dark:text-white">Profile Summary</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                
                {/* Skills */}
                <div className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-muted/20 dark:bg-card/40 flex items-center gap-4">
                  <div className="w-11 h-11 rounded-xl bg-blue-50 dark:bg-blue-950/40 text-blue-550 flex items-center justify-center shrink-0 border border-blue-100/50 dark:border-blue-800/30">
                    <Code size={18} />
                  </div>
                  <div className="min-w-0">
                    <span className="text-9 font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">Skills</span>
                    <div className="flex items-baseline gap-1 mt-0.5">
                      <span className="text-lg font-black text-slate-955 dark:text-slate-100">{skillsList.length}</span>
                      <span className="text-9 font-bold text-slate-400">Extracted</span>
                    </div>
                  </div>
                </div>

                {/* Experience */}
                <div className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-muted/20 dark:bg-card/40 flex items-center gap-4">
                  <div className="w-11 h-11 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 text-emerald-555 flex items-center justify-center shrink-0 border border-emerald-100/50 dark:border-emerald-800/30">
                    <Briefcase size={18} />
                  </div>
                  <div className="min-w-0">
                    <span className="text-9 font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">Experience</span>
                    <div className="flex items-baseline gap-1 mt-0.5">
                      <span className="text-lg font-black text-slate-955 dark:text-slate-100">{experienceYears.toFixed(1)}</span>
                      <span className="text-9 font-bold text-slate-400">Years</span>
                    </div>
                  </div>
                </div>

                {/* Education */}
                <div className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-muted/20 dark:bg-card/40 flex items-center gap-4">
                  <div className="w-11 h-11 rounded-xl bg-purple-50 dark:bg-purple-950/40 text-purple-555 flex items-center justify-center shrink-0 border border-purple-100/50 dark:border-purple-800/30">
                    <GraduationCap size={18} />
                  </div>
                  <div className="min-w-0">
                    <span className="text-9 font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">Education</span>
                    <div className="flex items-baseline gap-1 mt-0.5">
                      <span className="text-lg font-black text-slate-955 dark:text-slate-100">{educationCount}</span>
                      <span className="text-9 font-bold text-slate-400">{educationCount === 1 ? "Degree" : "Degrees"}</span>
                    </div>
                  </div>
                </div>

                {/* Projects */}
                <div className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-muted/20 dark:bg-card/40 flex items-center gap-4">
                  <div className="w-11 h-11 rounded-xl bg-amber-50 dark:bg-amber-955/40 text-amber-555 flex items-center justify-center shrink-0 border border-amber-100/50 dark:border-amber-800/30">
                    <Folder size={18} />
                  </div>
                  <div className="min-w-0">
                    <span className="text-9 font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">Projects</span>
                    <div className="flex items-baseline gap-1 mt-0.5">
                      <span className="text-lg font-black text-slate-955 dark:text-slate-100">{projectsCount}</span>
                      <span className="text-9 font-bold text-slate-400">Added</span>
                    </div>
                  </div>
                </div>

                {/* Certifications */}
                <div className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-muted/20 dark:bg-card/40 flex items-center gap-4">
                  <div className="w-11 h-11 rounded-xl bg-rose-50 dark:bg-rose-950/40 text-rose-555 flex items-center justify-center shrink-0 border border-rose-100/50 dark:border-rose-800/30">
                    <Award size={18} />
                  </div>
                  <div className="min-w-0">
                    <span className="text-9 font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">Certifications</span>
                    <div className="flex items-baseline gap-1 mt-0.5">
                      <span className="text-lg font-black text-slate-955 dark:text-slate-100">{certificationsCount}</span>
                      <span className="text-9 font-bold text-slate-400">Added</span>
                    </div>
                  </div>
                </div>

                {/* Achievements */}
                <div className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-muted/20 dark:bg-card/40 flex items-center gap-4">
                  <div className="w-11 h-11 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 text-indigo-555 flex items-center justify-center shrink-0 border border-indigo-100/50 dark:border-indigo-800/30">
                    <Trophy size={18} />
                  </div>
                  <div className="min-w-0">
                    <span className="text-9 font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block">Achievements</span>
                    <div className="flex items-baseline gap-1 mt-0.5">
                      <span className="text-lg font-black text-slate-955 dark:text-slate-100">{achievementsCount}</span>
                      <span className="text-9 font-bold text-slate-400">Added</span>
                    </div>
                  </div>
                </div>

              </div>
            </Card>

            {/* Row 3: Detailed Profile Overview + Top Skills side-by-side */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Detailed Profile Overview */}
              <Card className="flex flex-col">
                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 mb-4 shrink-0">
                  <h3 className="text-base font-black text-foreground dark:text-white">Detailed Profile Overview</h3>
                  <button 
                    onClick={() => setIsEditOpen(true)}
                    className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
                  >
                    View Extracted Details
                  </button>
                </div>
                
                <div className="space-y-2 max-h-300 overflow-y-auto pr-1 flex-1">
                  {profileSections.map((sec, idx) => {
                    const SecIcon = sec.icon;
                    return (
                      <div 
                        key={idx} 
                        onClick={() => handleSectionClick(sec.id)}
                        className="p-2.5 rounded-2xl border border-slate-100 dark:border-slate-800 bg-muted/10 dark:bg-card/40 hover:bg-muted/50 dark:hover:bg-slate-800/60 hover:border-slate-200 dark:hover:border-slate-700 flex items-center justify-between cursor-pointer transition-all"
                      >
                        <div className="flex items-center gap-3">
                          <div className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 shrink-0">
                            <SecIcon size={15} />
                          </div>
                          <div>
                            <span className="text-xs font-bold text-slate-800 dark:text-slate-200 block">{sec.name}</span>
                            <span className="text-10 text-slate-400 dark:text-muted-foreground font-semibold block">{sec.desc}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`text-9 font-bold px-2 py-0.5 rounded-full flex items-center gap-1 ${
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
              </Card>

              {/* Top Skills & Keywords */}
              <Card className="flex flex-col gap-6">
                <div>
                  <h3 className="text-10 font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-3 block">Top Skills</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {skillsList.map((skill: string, idx: number) => (
                      <span key={idx} className="text-11 font-semibold px-2.5 py-1 rounded-xl bg-muted dark:bg-slate-800 border border-border dark:border-border text-foreground dark:text-slate-300">
                        {skill}
                      </span>
                    ))}
                    {skillsList.length === 0 && (
                      <span className="text-xs text-slate-400 italic">No skills extracted.</span>
                    )}
                  </div>
                </div>

                <div className="border-t border-slate-100 dark:border-slate-800 pt-4 flex-1">
                  <h3 className="text-10 font-bold text-slate-400 dark:text-muted-foreground uppercase tracking-wider mb-3 block">Top Keywords Found</h3>
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
              </Card>

              {/* AI Skills Gap & Course Recommendations */}
              <Card className="space-y-4">
                <div className="flex items-center gap-3 border-b border-border pb-3 mb-4 shrink-0">
                  <div className="w-9 h-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0 border border-primary/20">
                    <Sparkles size={18} className="animate-pulse" />
                  </div>
                  <div>
                    <h3 className="text-base font-black text-foreground">AI Skill Gap & Recommendations</h3>
                    <p className="text-xs text-muted-foreground">Personalized upskilling insights based on your resume profile</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Left Column: Missing Skills */}
                  <div className="space-y-3">
                    <span className="text-10 font-bold text-muted-foreground uppercase tracking-wider block">Identified Missing Skills</span>
                    {skillsList.length === 0 ? (
                      <p className="text-xs text-muted-foreground italic">Upload your resume to analyze missing skills.</p>
                    ) : missingSkills.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {missingSkills.map((skill, idx) => (
                          <span key={idx} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-destructive/10 dark:bg-destructive/20 border border-destructive/20 text-destructive text-11 font-bold">
                            <span className="w-1.5 h-1.5 rounded-full bg-destructive animate-pulse" />
                            {skill}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <div className="p-3 rounded-xl bg-success/10 border border-success/20 text-xs text-success font-bold flex items-center gap-2">
                        <CheckCircle2 size={16} />
                        Your skills match the high-demand market trends!
                      </div>
                    )}
                  </div>

                  {/* Right Column: Recommended Courses */}
                  <div className="space-y-3">
                    <span className="text-10 font-bold text-muted-foreground uppercase tracking-wider block">Recommended Upskill Courses</span>
                    <div className="space-y-2.5">
                      {skillsList.length === 0 ? (
                        <p className="text-xs text-muted-foreground italic">No recommendations available.</p>
                      ) : recommendedCourses.length > 0 ? (
                        recommendedCourses.map((course, idx) => (
                          <div key={idx} className="p-3 rounded-2xl border border-border bg-muted/20 dark:bg-muted/10 flex items-center justify-between gap-3 hover:bg-muted/30 transition-all">
                            <div>
                              <span className="text-xs font-bold text-foreground block">{course.title}</span>
                              <span className="text-10 text-muted-foreground mt-0.5 block font-semibold">Upskill in: {course.skills.join(", ")}</span>
                            </div>
                            <Link href="/candidate/skill-lab">
                              <Button size="xs" variant="outline" className="text-10 py-1 h-auto font-bold">
                                Learn
                              </Button>
                            </Link>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-muted-foreground italic">All caught up! Check out Skill Lab for general learning.</p>
                      )}
                    </div>
                  </div>
                </div>
              </Card>

              {/* Row 4: Extracted Resume Analysis & Preview (Summary, Experience, Projects, Education) */}
              {profile?.resume_status === "completed" && (
                <Card className="p-6 space-y-6 border border-border bg-card shadow-sm rounded-3xl">
                  <div className="flex items-center gap-3 border-b border-border pb-4">
                    <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 text-indigo-500 flex items-center justify-center shrink-0 border border-indigo-500/20">
                      <FileText size={20} />
                    </div>
                    <div>
                      <h3 className="text-lg font-black text-foreground">Resume Analysis & Preview</h3>
                      <p className="text-xs text-muted-foreground">Extracted resume details synced dynamically to your profile</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 gap-6">
                    {/* Extracted Summary */}
                    {editForm.summary && (
                      <div className="space-y-2">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                          Professional Summary
                        </h4>
                        <p className="text-xs text-slate-700 dark:text-slate-350 leading-relaxed bg-muted/20 dark:bg-slate-900/20 p-4 rounded-2xl border border-border/55 whitespace-pre-line font-medium">
                          {editForm.summary}
                        </p>
                      </div>
                    )}

                    {/* Skills Grid */}
                    {skillsList.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                          Skills & Competencies
                        </h4>
                        <div className="flex flex-wrap gap-1.5 bg-muted/20 dark:bg-slate-900/20 p-4 rounded-2xl border border-border/55">
                          {skillsList.map((skill: string, idx: number) => (
                            <Badge key={idx} variant="outline" className="text-xs font-bold px-2.5 py-1 bg-background border-border text-foreground">
                              {skill}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Experience Timeline */}
                    {editForm.experienceList.length > 0 && (
                      <div className="space-y-3">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                          Work Experience Timeline
                        </h4>
                        <div className="relative border-l border-border ml-3 pl-6 space-y-6 py-2 bg-muted/10 dark:bg-slate-900/10 p-5 rounded-2xl border border-border/40">
                          {editForm.experienceList.map((exp: any, index: number) => (
                            <div key={index} className="relative">
                              <span className="absolute left-[-29px] top-1 flex h-2.5 w-2.5 items-center justify-center rounded-full bg-indigo-500 border border-indigo-500 shadow-sm shadow-indigo-500/20" />
                              <div className="space-y-1">
                                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-1">
                                  <h5 className="text-xs font-bold text-foreground">{exp.role || "Role not specified"}</h5>
                                  {exp.years && (
                                    <span className="text-10 font-bold px-2 py-0.5 rounded bg-muted text-muted-foreground shrink-0 border border-border/45">
                                      {exp.years} years
                                    </span>
                                  )}
                                </div>
                                <p className="text-11 font-bold text-slate-550 dark:text-slate-400">{exp.company || "Company not specified"}</p>
                                {exp.description && (
                                  <p className="text-xs text-muted-foreground leading-relaxed pt-2 whitespace-pre-wrap">
                                    {exp.description}
                                  </p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Projects Grid */}
                    {editForm.projectList.length > 0 && (
                      <div className="space-y-3">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                          Projects Grid
                        </h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {editForm.projectList.map((proj: any, index: number) => (
                            <div key={index} className="p-4 rounded-2xl border border-border bg-muted/20 dark:bg-slate-900/20 space-y-2 flex flex-col justify-between">
                              <div className="space-y-1.5">
                                <div className="flex justify-between items-start gap-3">
                                  <h5 className="text-xs font-bold text-foreground leading-snug">{proj.name || "Project Name"}</h5>
                                  {proj.link && (
                                    <a href={proj.link} target="_blank" rel="noopener noreferrer" className="text-10 font-bold text-blue-650 dark:text-blue-400 hover:underline flex items-center gap-1 cursor-pointer shrink-0">
                                      <span>Link</span>
                                      <Globe size={10} />
                                    </a>
                                  )}
                                </div>
                                {proj.description && (
                                  <p className="text-11 text-muted-foreground leading-relaxed">
                                    {proj.description}
                                  </p>
                                )}
                              </div>
                              {proj.technologies && (
                                <div className="flex flex-wrap gap-1 mt-2.5">
                                  {(Array.isArray(proj.technologies) ? proj.technologies : String(proj.technologies).split(",")).map((tech: string, tIdx: number) => {
                                    const clean = tech.trim();
                                    if (!clean) return null;
                                    return (
                                      <span key={tIdx} className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-background border border-border text-muted-foreground">
                                        {clean}
                                      </span>
                                    );
                                  })}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Education & Certifications Side-by-side */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* Education */}
                      {editForm.educationList.length > 0 && (
                        <div className="space-y-3">
                          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                            Education History
                          </h4>
                          <div className="relative border-l border-border ml-3 pl-6 space-y-5 py-2 bg-muted/10 dark:bg-slate-900/10 p-5 rounded-2xl border border-border/40">
                            {editForm.educationList.map((edu: any, index: number) => (
                              <div key={index} className="relative">
                                <span className="absolute left-[-29px] top-1 flex h-2.5 w-2.5 items-center justify-center rounded-full bg-purple-500 border border-purple-500 shadow-sm" />
                                <div className="space-y-0.5">
                                  <div className="flex justify-between items-start gap-3">
                                    <h5 className="text-xs font-bold text-foreground">{edu.degree || "Degree not specified"}</h5>
                                    {edu.year && (
                                      <span className="text-10 font-bold px-2 py-0.5 rounded bg-muted text-muted-foreground shrink-0 border border-border/45">
                                        {edu.year}
                                      </span>
                                    )}
                                  </div>
                                  <p className="text-11 text-slate-550 dark:text-slate-400">{edu.school || "School not specified"}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Certifications */}
                      {editForm.certifications && (
                        <div className="space-y-3">
                          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                            Certifications
                          </h4>
                          <div className="flex flex-wrap gap-2 bg-muted/10 dark:bg-slate-900/10 p-5 rounded-2xl border border-border/40 min-h-[90px] content-start">
                            {editForm.certifications.split(",").map((cert: string, idx: number) => {
                              const clean = cert.trim();
                              if (!clean) return null;
                              return (
                                <span key={idx} className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-background border border-border text-slate-705 dark:text-slate-300">
                                  {clean}
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>

                  </div>
                </Card>
              )}

            </div>

          </div>

          {/* RIGHT SIDEBAR (AI Insights, AI Quality Score, Resume Versions) */}
          <div className="space-y-6">
            
            {/* AI Insights Card */}
            <Card>
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
                <h3 className="text-base font-black text-foreground dark:text-white">AI Insights</h3>
                <button className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer">View All</button>
              </div>

              <div className="space-y-4">
                {/* Strongest skill */}
                <div className="flex items-start gap-4">
                  <div className="w-9 h-9 rounded-xl bg-teal-50 dark:bg-teal-950/40 text-teal-600 dark:text-teal-400 flex items-center justify-center shrink-0 border border-teal-100/40 dark:border-teal-850">
                    <Code size={16} />
                  </div>
                  <div>
                    <span className="text-11 font-bold text-slate-400 dark:text-slate-500 block">Your strongest skill</span>
                    <span className="text-xs font-black text-slate-800 dark:text-slate-200 mt-0.5 block">{strongestSkill}</span>
                  </div>
                </div>

                {/* Top improvement area */}
                <div className="flex items-start gap-4">
                  <div className="w-9 h-9 rounded-xl bg-amber-50 dark:bg-amber-955/40 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0 border border-amber-100/40 dark:border-amber-850">
                    <TrendingUp size={16} />
                  </div>
                  <div>
                    <span className="text-11 font-bold text-slate-400 dark:text-slate-500 block">Top improvement area</span>
                    <span className="text-xs font-black text-slate-800 dark:text-slate-200 mt-0.5 block">{improvementArea}</span>
                  </div>
                </div>

                {/* Profile strength */}
                <div className="flex items-start gap-4">
                  <div className="w-9 h-9 rounded-xl bg-purple-50 dark:bg-purple-950/40 text-purple-650 dark:text-purple-400 flex items-center justify-center shrink-0 border border-purple-100/40 dark:border-purple-850">
                    <ShieldCheck size={16} />
                  </div>
                  <div>
                    <span className="text-11 font-bold text-slate-400 dark:text-slate-500 block">Profile strength</span>
                    <span className="text-xs font-black text-slate-800 dark:text-slate-200 mt-0.5 block">{profileStrength}</span>
                  </div>
                </div>

                {/* Recommended next step */}
                <div className="flex items-start gap-4">
                  <div className="w-9 h-9 rounded-xl bg-blue-50 dark:bg-blue-955/40 text-blue-650 dark:text-blue-400 flex items-center justify-center shrink-0 border border-blue-100/40 dark:border-blue-850">
                    <FileText size={16} />
                  </div>
                  <div>
                    <span className="text-11 font-bold text-slate-400 dark:text-slate-500 block">Recommended next step</span>
                    <span className="text-xs font-black text-slate-800 dark:text-slate-200 mt-0.5 block">{recommendedStep}</span>
                  </div>
                </div>
              </div>
            </Card>

            {/* AI Quality Score Card */}
            <Card className="space-y-6">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                <h3 className="text-base font-black text-foreground dark:text-white">AI Quality Score</h3>
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
                      <span className="text-lg font-black text-foreground dark:text-white">{aiQualityScore}</span>
                      <span className="text-8 font-bold text-slate-400 dark:text-slate-500">/10</span>
                    </div>
                  </div>
                  <span className="text-10 font-bold text-indigo-500 mt-1.5 uppercase">
                    {skillsList.length === 0 ? "N/A" : (aiQualityScore >= 8 ? "Excellent" : (aiQualityScore >= 6 ? "Good" : "Needs Work"))}
                  </span>
                </div>

                {/* Score list */}
                <div className="flex-1 space-y-1.5 text-xs font-bold text-slate-655 dark:text-slate-400 min-w-0">
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-slate-450 dark:text-muted-foreground">Grammar</span>
                    <span>{skillsList.length === 0 ? 0 : aiQualityBreakdown.grammar}/10</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-slate-450 dark:text-muted-foreground">Formatting</span>
                    <span>{skillsList.length === 0 ? 0 : aiQualityBreakdown.formatting}/10</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-slate-455 dark:text-muted-foreground">Readability</span>
                    <span>{skillsList.length === 0 ? 0 : aiQualityBreakdown.readability}/10</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-slate-455 dark:text-muted-foreground">Projects</span>
                    <span>{skillsList.length === 0 ? 0 : aiQualityBreakdown.project_quality}/10</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-slate-455 dark:text-muted-foreground">Achievements</span>
                    <span>{skillsList.length === 0 ? 0 : aiQualityBreakdown.achievement_quality}/10</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-slate-455 dark:text-muted-foreground">Structure</span>
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
            </Card>

            {/* Resume Versions Card */}
            <Card className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                <h3 className="text-base font-black text-foreground dark:text-white">Resume Versions</h3>
                <button className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer">View All</button>
              </div>

              <div className="space-y-2.5 max-h-260 overflow-y-auto pr-1">
                {resumeVersions.map((ver, idx) => (
                  <div key={idx} className="p-3 rounded-2xl border border-slate-100 dark:border-slate-800 bg-muted/10 dark:bg-card/40 flex items-center justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-655 dark:text-slate-455 flex items-center justify-center shrink-0">
                        <FileText size={15} />
                      </div>
                      <div className="min-w-0">
                        <span className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1 truncate">
                          {ver.version}
                          {ver.isLatest && (
                            <span className="text-9 font-bold px-1 py-0.2 bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 rounded border border-blue-100 dark:border-blue-800/40 shrink-0">
                              Latest
                            </span>
                          )}
                        </span>
                        <span className="text-9 text-slate-400 dark:text-slate-500 font-semibold block mt-0.5">{ver.date}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      <button 
                        onClick={() => handlePreviewResume(ver.url)}
                        className="p-1 rounded bg-white dark:bg-slate-900 border border-border dark:border-slate-850 text-slate-450 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer hover:bg-muted"
                        title="Preview"
                      >
                        <Eye size={12} />
                      </button>
                      <button 
                        onClick={() => handleDownloadResumeUrl(ver.url, ver.version)}
                        className="p-1 rounded bg-white dark:bg-slate-900 border border-border dark:border-slate-850 text-slate-450 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer hover:bg-muted"
                        title="Download"
                      >
                        <Download size={12} />
                      </button>
                      <button 
                        onClick={() => handleDeleteResumeVersion(ver.id)}
                        className="p-1 rounded bg-white dark:bg-slate-900 border border-slate-155 border-border dark:border-slate-850 text-slate-455 hover:text-red-500 hover:border-red-205 cursor-pointer hover:bg-red-50"
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

              <div className="flex flex-col gap-2 w-full">
                <button 
                  onClick={triggerUpload}
                  disabled={uploading}
                  className="w-full py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-muted dark:hover:bg-slate-800 text-slate-700 dark:text-slate-305 text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-sm disabled:opacity-50"
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
                <label className="flex items-center gap-2 text-[10px] select-none cursor-pointer mt-1 justify-center bg-white/5 border border-white/10 rounded-lg py-1.5 px-3 hover:bg-white/10 transition-colors">
                  <input
                    type="checkbox"
                    checked={fastMode}
                    onChange={(e) => setFastMode(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-900 text-violet-600 focus:ring-violet-500"
                  />
                  <span className="font-semibold text-slate-300">⚡ Instant Ingestion Mode (Milliseconds)</span>
                </label>
              </div>
            </Card>

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
              <div className="w-screen max-w-2xl transform transition-all duration-300 ease-in-out bg-card border-l border-border shadow-2xl flex flex-col h-full">
                
                {/* Header */}
                <div className="px-6 py-5 border-b border-slate-155 dark:border-border flex items-center justify-between shrink-0">
                  <div>
                    <h2 className="text-lg font-black text-foreground dark:text-white" id="slide-over-title">
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
                <div className="bg-muted dark:bg-card/40 px-6 py-3 border-b border-slate-100 dark:border-border text-11 font-semibold text-slate-500 dark:text-slate-400 flex items-start gap-2 shrink-0">
                  <AlertCircle size={14} className="text-slate-400 mt-0.5 shrink-0" />
                  <span>
                    Your profile is synchronized automatically with your latest resume. To make changes or fix inaccuracies, update your resume and upload it again.
                  </span>
                </div>

                {/* Body: Tabs on left/top, Content on right/bottom */}
                <div className="flex-1 overflow-hidden flex flex-col md:flex-row min-h-0">
                  
                  {/* Tabs Selector List */}
                  <div className="w-full md:w-48 bg-muted/50 dark:bg-slate-900/20 border-b md:border-b-0 md:border-r border-slate-100 dark:border-border overflow-x-auto md:overflow-y-auto py-2 md:py-4 flex md:flex-col shrink-0 scrollbar-none">
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
                        <h4 className="text-sm font-black text-foreground dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <MapPin size={16} className="text-slate-400" />
                          <span>Personal Information</span>
                        </h4>
                        <div className="space-y-4">
                          <div>
                            <span className="text-10 font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-1">Full Name</span>
                            <div className="px-3.5 py-2.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-muted/30 dark:bg-slate-900/30 text-xs font-semibold text-slate-800 dark:text-slate-200">
                              {editForm.name || "Not specified"}
                            </div>
                          </div>
                          <div>
                            <span className="text-10 font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-1">Email Address</span>
                            <div className="px-3.5 py-2.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-muted/30 dark:bg-slate-900/30 text-xs font-semibold text-slate-800 dark:text-slate-200">
                              {editForm.email || "Not specified"}
                            </div>
                          </div>
                          <div>
                            <span className="text-10 font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-1">Phone Number</span>
                            <div className="px-3.5 py-2.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-muted/30 dark:bg-slate-900/30 text-xs font-semibold text-slate-800 dark:text-slate-200">
                              {editForm.phone || "Not specified"}
                            </div>
                          </div>
                          <div>
                            <span className="text-10 font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-1">Location / Address</span>
                            <div className="px-3.5 py-2.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-muted/30 dark:bg-slate-900/30 text-xs font-semibold text-slate-800 dark:text-slate-200">
                              {editForm.address || "Not specified"}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* SUMMARY TAB */}
                    {activeTab === "summary" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-foreground dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <FileText size={16} className="text-slate-400" />
                          <span>Professional Summary</span>
                        </h4>
                        <div>
                          <span className="text-10 font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-1.5">Summary</span>
                          <div className="px-4 py-3 rounded-xl border border-slate-100 dark:border-slate-800 bg-muted/30 dark:bg-slate-900/30 text-xs font-semibold text-slate-700 dark:text-slate-350 leading-relaxed whitespace-pre-wrap">
                            {editForm.summary || "No professional summary extracted."}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* SKILLS TAB */}
                    {activeTab === "skills" && (
                      <div className="space-y-6">
                        <h4 className="text-sm font-black text-foreground dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <Code size={16} className="text-slate-400" />
                          <span>Extracted Skills</span>
                        </h4>
                        <div>
                          <span className="text-10 font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-3">Skills List</span>
                          <div className="flex flex-wrap gap-2">
                            {skillsList.map((skill: string, idx: number) => (
                              <span key={idx} className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-muted dark:bg-slate-850 border border-slate-100 dark:border-border text-slate-700 dark:text-slate-300">
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
                        <h4 className="text-sm font-black text-foreground dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <Briefcase size={16} className="text-slate-400" />
                          <span>Work Experience</span>
                        </h4>
                        <div className="space-y-4">
                          {editForm.experienceList.map((exp: any, index: number) => (
                            <div key={index} className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-muted/10 dark:bg-slate-900/20 space-y-2">
                              <div className="flex justify-between items-start">
                                <div>
                                  <h5 className="text-xs font-bold text-foreground dark:text-white">{exp.role || "Role not specified"}</h5>
                                  <p className="text-11 text-slate-550 dark:text-slate-400 font-semibold">{exp.company || "Company not specified"}</p>
                                </div>
                                {exp.years ? (
                                  <span className="text-10 font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
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
                        <h4 className="text-sm font-black text-foreground dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <GraduationCap size={16} className="text-slate-400" />
                          <span>Education</span>
                        </h4>
                        <div className="space-y-4">
                          {editForm.educationList.map((edu: any, index: number) => (
                            <div key={index} className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-muted/10 dark:bg-slate-900/20 flex justify-between items-start">
                              <div className="space-y-1">
                                <h5 className="text-xs font-bold text-foreground dark:text-white">{edu.degree || "Degree not specified"}</h5>
                                <p className="text-11 text-slate-550 dark:text-slate-400 font-semibold">{edu.school || "School/University not specified"}</p>
                              </div>
                              {edu.year && (
                                <span className="text-10 font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
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
                        <h4 className="text-sm font-black text-foreground dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <Folder size={16} className="text-slate-400" />
                          <span>Projects</span>
                        </h4>
                        <div className="space-y-4">
                          {editForm.projectList.map((proj: any, index: number) => (
                            <div key={index} className="p-4 rounded-2xl border border-slate-100 dark:border-slate-800 bg-muted/10 dark:bg-slate-900/20 space-y-2">
                              <div className="flex justify-between items-center">
                                <h5 className="text-xs font-bold text-foreground dark:text-white">{proj.name || "Project name not specified"}</h5>
                                {proj.link && (
                                  <a 
                                    href={proj.link} 
                                    target="_blank" 
                                    rel="noopener noreferrer" 
                                    className="text-10 font-bold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 cursor-pointer"
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
                        <h4 className="text-sm font-black text-foreground dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <Award size={16} className="text-slate-400" />
                          <span>Certifications</span>
                        </h4>
                        <div>
                          <span className="text-10 font-bold uppercase tracking-wider text-slate-400 dark:text-muted-foreground block mb-3">Extracted Certifications</span>
                          <div className="flex flex-wrap gap-2">
                            {editForm.certifications ? (
                              editForm.certifications.split(",").map((cert: string, idx: number) => {
                                const clean = cert.trim();
                                if (!clean) return null;
                                return (
                                  <span key={idx} className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-muted dark:bg-slate-800 border border-slate-100 dark:border-border text-slate-700 dark:text-slate-300">
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
                        <h4 className="text-sm font-black text-foreground dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <Trophy size={16} className="text-slate-400" />
                          <span>Achievements</span>
                        </h4>
                        <div className="space-y-3">
                          {editForm.achievementsList.map((ach: string, index: number) => {
                            if (!ach.trim()) return null;
                            return (
                              <div key={index} className="flex gap-2.5 items-start p-3 rounded-2xl border border-slate-100 dark:border-slate-800 bg-muted/10 dark:bg-slate-900/20 text-xs font-semibold text-slate-700 dark:text-slate-300">
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
                        <h4 className="text-sm font-black text-foreground dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <Languages size={16} className="text-slate-400" />
                          <span>Languages</span>
                        </h4>
                        <div>
                          <span className="text-10 font-bold uppercase tracking-wider text-slate-400 dark:text-muted-foreground block mb-3">Extracted Languages</span>
                          <div className="flex flex-wrap gap-2">
                            {editForm.languages ? (
                              editForm.languages.split(",").map((lang: string, idx: number) => {
                                const clean = lang.trim();
                                if (!clean) return null;
                                return (
                                  <span key={idx} className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-muted dark:bg-slate-800 border border-slate-100 dark:border-border text-slate-700 dark:text-slate-300">
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
                        <h4 className="text-sm font-black text-foreground dark:text-white border-b border-slate-100 dark:border-slate-800 pb-2 flex items-center gap-2">
                          <Globe size={16} className="text-slate-400" />
                          <span>Social Links</span>
                        </h4>
                        <div className="space-y-4">
                          {editForm.linkedin && (
                            <div>
                              <span className="text-10 font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-1">LinkedIn Profile URL</span>
                              <a 
                                href={editForm.linkedin} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                className="px-3.5 py-2.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-muted/30 dark:bg-slate-900/30 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-2"
                              >
                                <Globe size={13} />
                                <span>{editForm.linkedin}</span>
                              </a>
                            </div>
                          )}
                          {editForm.github && (
                            <div>
                              <span className="text-10 font-bold uppercase tracking-wider text-slate-400 dark:text-muted-foreground block mb-1">GitHub Profile URL</span>
                              <a 
                                href={editForm.github} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                className="px-3.5 py-2.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-muted/30 dark:bg-slate-900/30 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-2"
                              >
                                <Code size={13} />
                                <span>{editForm.github}</span>
                              </a>
                            </div>
                          )}
                          {editForm.portfolio && (
                            <div>
                              <span className="text-10 font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block mb-1">Portfolio Website URL</span>
                              <a 
                                href={editForm.portfolio} 
                                target="_blank" 
                                rel="noopener noreferrer" 
                                className="px-3.5 py-2.5 rounded-xl border border-slate-100 dark:border-slate-800 bg-muted/30 dark:bg-slate-900/30 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-2"
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
                <div className="px-6 py-4 border-t border-border dark:border-slate-850 bg-muted/50 dark:bg-slate-900/30 flex items-center justify-between gap-3 shrink-0">
                  <button 
                    onClick={() => {
                      setIsEditOpen(false);
                      triggerUpload();
                    }}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-950 dark:bg-muted hover:bg-slate-900 dark:hover:bg-slate-205 text-white dark:text-slate-955 text-xs font-bold cursor-pointer transition-all shadow-md"
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
      )}
      {/* 4. PDF Preview Modal */}
      {showPreviewModal && previewUrl && (
        <Modal
          isOpen={showPreviewModal}
          onClose={() => setShowPreviewModal(false)}
          title="Resume Preview"
          className="max-w-4xl h-[85vh]"
        >
          <div className="flex flex-col h-full -m-6">
            {/* Action Bar inside Modal */}
            <div className="flex justify-end p-4 border-b border-border shrink-0">
              <a 
                href={`${getBackendBaseUrl()}${previewUrl}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border hover:bg-muted text-xs font-bold text-muted-foreground hover:text-foreground transition-colors"
              >
                <ExternalLink size={12} />
                <span>Open in new tab</span>
              </a>
            </div>
            
            {/* PDF Embed */}
            <div className="flex-1 bg-slate-100 dark:bg-slate-950">
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
