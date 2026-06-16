"use client";

import { useEffect, useState } from "react";
import { apiService } from "@/services/api";
import { 
  BookOpen, Trash, CheckCircle, Sparkles, 
  Wand2, Compass, AlertCircle, RefreshCw, Layers, PlusCircle
} from "lucide-react";

export default function AdminCourses() {
  const [courses, setCourses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Selection tab
  const [activeTab, setActiveTab] = useState<"list" | "generate" | "manual">("list");

  // AI Generator Form States
  const [generateTopic, setGenerateTopic] = useState("");
  const [generateCategory, setGenerateCategory] = useState("Web Development");
  const [generateLevel, setGenerateLevel] = useState("Intermediate");
  const [generateDesc, setGenerateDesc] = useState("");
  const [generating, setGenerating] = useState(false);
  const [genStep, setGenStep] = useState(0);

  // Manual Form States
  const [manualTitle, setManualTitle] = useState("");
  const [manualInstructor, setManualInstructor] = useState("");
  const [manualCategory, setManualCategory] = useState("Web Development");
  const [manualLevel, setManualLevel] = useState("Intermediate");
  const [manualDuration, setManualDuration] = useState("12 Hours");
  const [manualDesc, setManualDesc] = useState("");

  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const CATEGORIES = [
    "Programming",
    "Web Development",
    "AI & Machine Learning",
    "Database Technologies",
    "System Design",
    "Mobile Development",
    "Cloud Computing & DevOps",
    "Cybersecurity"
  ];

  const LEVELS = ["Beginner", "Intermediate", "Advanced"];

  const fetchCourses = async () => {
    try {
      const data = await apiService.getCourses();
      setCourses(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCourses();
  }, []);

  // AI course generation stepper text
  useEffect(() => {
    if (!generating) return;
    const interval = setInterval(() => {
      setGenStep((prev) => (prev < 4 ? prev + 1 : prev));
    }, 4500);
    return () => clearInterval(interval);
  }, [generating]);

  const handleGenerateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!generateTopic.trim()) return;

    setErrorMsg("");
    setSuccessMsg("");
    setGenerating(true);
    setGenStep(0);

    try {
      const res = await apiService.generateCourse(
        generateTopic,
        generateCategory,
        generateLevel,
        generateDesc
      );
      setSuccessMsg(`AI Course "${res.title}" successfully generated with 3 modules, lessons, quizzes, assessments, and AI voice interviews!`);
      setGenerateTopic("");
      setGenerateDesc("");
      setActiveTab("list");
      await fetchCourses();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to generate course with AI.");
    } finally {
      setGenerating(false);
    }
  };

  const handleCreateCourseManual = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualTitle.trim() || !manualInstructor.trim() || !manualDesc.trim()) {
      setErrorMsg("Please fill out all required fields.");
      return;
    }

    setErrorMsg("");
    setSuccessMsg("");

    try {
      const res = await apiService.createCourse(
        manualTitle,
        manualInstructor,
        manualCategory,
        manualLevel,
        manualDesc,
        manualDuration
      );
      setSuccessMsg(`Course "${res.title}" successfully created! You can now add modules to it.`);
      setManualTitle("");
      setManualInstructor("");
      setManualDesc("");
      setActiveTab("list");
      await fetchCourses();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to manually create course.");
    }
  };

  return (
    <div className="p-8 md:p-12 max-w-6xl mx-auto flex flex-col gap-8 text-gray-200">
      
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-gray-800 pb-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <span>Course & Learning Path Management</span>
            <BookOpen className="text-purple-400" size={24} />
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Build production-ready curriculum manually or use generative AI to construct interactive multi-modal courses instantly.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-4 border-b border-gray-800 pb-px">
        {[
          { id: "list", label: "Active Courses", icon: BookOpen },
          { id: "generate", label: "AI Course Generator", icon: Sparkles },
          { id: "manual", label: "Manual Course Builder", icon: Layers }
        ].map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id as any);
                setErrorMsg("");
                setSuccessMsg("");
              }}
              className={`flex items-center gap-2 text-xs font-bold pb-3 border-b-2 transition-all cursor-pointer whitespace-nowrap ${
                active 
                  ? "border-purple-500 text-purple-400" 
                  : "border-transparent text-gray-400 hover:text-white"
              }`}
            >
              <Icon size={14} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Notification Toast Messages */}
      {successMsg && (
        <div className="p-4 bg-emerald-950/30 border border-emerald-900/40 text-emerald-400 rounded-xl flex items-center gap-3 text-sm">
          <CheckCircle size={18} className="shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 bg-red-950/30 border border-red-900/40 text-red-400 rounded-xl flex items-center gap-3 text-sm">
          <AlertCircle size={18} className="shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Main Tab Rendering */}
      {activeTab === "list" && (
        <div className="flex flex-col gap-6">
          {loading ? (
            <div className="text-center py-16 text-gray-500 text-sm flex items-center justify-center gap-2">
              <RefreshCw className="animate-spin" size={16} />
              <span>Loading course catalog...</span>
            </div>
          ) : courses.length === 0 ? (
            <div className="glass-panel p-16 text-center rounded-2xl border border-gray-850 flex flex-col items-center justify-center gap-4 bg-card/20">
              <BookOpen size={40} className="text-gray-600" />
              <p className="text-sm font-medium text-gray-400">No active learning paths or courses found in the system database.</p>
              <button 
                onClick={() => setActiveTab("generate")}
                className="px-5 py-2.5 bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold rounded-xl transition-all cursor-pointer"
              >
                Generate First Course with AI
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {courses.map((course) => (
                <div 
                  key={course.id} 
                  className="glass-panel rounded-2xl border border-gray-850 bg-card/20 p-5 flex flex-col gap-4 hover:border-purple-900/30 transition-all hover:translate-y-[-2px] duration-200"
                >
                  <div className="flex justify-between items-start">
                    <span className="text-[10px] font-bold font-mono px-2 py-0.5 bg-purple-950/40 text-purple-400 border border-purple-900/30 rounded-md">
                      {course.category}
                    </span>
                    <span className="text-xs text-gray-400 font-semibold">{course.level}</span>
                  </div>

                  <div>
                    <h3 className="text-base font-bold text-white leading-snug line-clamp-1">{course.title}</h3>
                    <p className="text-xs text-gray-400 mt-2 line-clamp-2 leading-relaxed">{course.description}</p>
                  </div>

                  <div className="mt-auto border-t border-gray-850 pt-4 flex justify-between items-center text-xs text-gray-400">
                    <div className="flex items-center gap-1">
                      <Layers size={13} className="text-purple-400" />
                      <span>{course.totalModules || 0} Modules</span>
                    </div>
                    <span>{course.duration}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "generate" && (
        <div className="max-w-2xl mx-auto w-full">
          {generating ? (
            <div className="glass-panel p-12 text-center border border-gray-850 rounded-2xl bg-card/30 flex flex-col items-center justify-center gap-6">
              <div className="relative w-16 h-16 flex items-center justify-center">
                <div className="w-16 h-16 rounded-full border-4 border-t-purple-500 border-purple-950 animate-spin absolute" />
                <Wand2 className="text-purple-400" size={24} />
              </div>
              
              <div className="flex flex-col gap-2">
                <h3 className="text-base font-bold text-white">Generating Complete Course via AI...</h3>
                <p className="text-xs text-gray-400 max-w-sm">This can take up to 30-45 seconds as we build out interactive lessons, study guides, and evaluation tools.</p>
              </div>

              {/* Progress Steps Indicators */}
              <div className="w-full max-w-md bg-muted/20 border border-gray-850 rounded-xl p-4 flex flex-col gap-3 text-left">
                {[
                  "Drafting curriculum modules & overview",
                  "Creating video lessons & course resources",
                  "Designing quizzes & conceptual assessments",
                  "Formulating AI voice mock interview questions",
                  "Finalizing database rows & deployment"
                ].map((step, idx) => {
                  const done = genStep > idx;
                  const active = genStep === idx;
                  return (
                    <div key={idx} className="flex items-center gap-3 text-xs">
                      {done ? (
                        <CheckCircle size={14} className="text-emerald-500 shrink-0" />
                      ) : active ? (
                        <div className="w-3.5 h-3.5 rounded-full border-2 border-purple-500 border-t-transparent animate-spin shrink-0" />
                      ) : (
                        <div className="w-3.5 h-3.5 rounded-full border-2 border-gray-800 shrink-0" />
                      )}
                      <span className={done ? "text-gray-400 line-through" : active ? "text-purple-400 font-bold" : "text-gray-600"}>
                        {step}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <form onSubmit={handleGenerateCourse} className="glass-panel p-6 sm:p-8 rounded-2xl border border-gray-850 bg-card/20 flex flex-col gap-5">
              <div className="flex items-center gap-2 border-b border-gray-850 pb-4 mb-2">
                <Wand2 className="text-purple-400" size={20} />
                <div>
                  <h2 className="text-base font-bold text-white">AI Course Generator</h2>
                  <p className="text-xs text-gray-400">Describe the topic, and the system AI will construct a fully functioning multi-module syllabus instantly.</p>
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Course Topic Name</label>
                <input 
                  type="text" 
                  value={generateTopic}
                  onChange={(e) => setGenerateTopic(e.target.value)}
                  placeholder="e.g. Master Docker & Kubernetes Deployment"
                  className="bg-background border border-gray-800 rounded-xl px-4 py-2.5 text-sm focus:outline-hidden focus:border-purple-500 text-white"
                  required
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Category</label>
                  <select 
                    value={generateCategory}
                    onChange={(e) => setGenerateCategory(e.target.value)}
                    className="bg-background border border-gray-800 rounded-xl px-4 py-2.5 text-sm focus:outline-hidden focus:border-purple-500 text-white"
                  >
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Difficulty Level</label>
                  <select 
                    value={generateLevel}
                    onChange={(e) => setGenerateLevel(e.target.value)}
                    className="bg-background border border-gray-800 rounded-xl px-4 py-2.5 text-sm focus:outline-hidden focus:border-purple-500 text-white"
                  >
                    {LEVELS.map((l) => (
                      <option key={l} value={l}>{l}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Additional Prompt / Focus Area (Optional)</label>
                <textarea 
                  value={generateDesc}
                  onChange={(e) => setGenerateDesc(e.target.value)}
                  placeholder="e.g. Focus on docker-compose, multi-stage builds, and deployment on AWS EKS."
                  className="bg-background border border-gray-800 rounded-xl px-4 py-2.5 text-sm focus:outline-hidden focus:border-purple-500 h-24 text-white resize-none"
                />
              </div>

              <button 
                type="submit"
                className="w-full py-3 bg-purple-600 hover:bg-purple-700 text-white font-bold text-sm rounded-xl transition-all cursor-pointer shadow-md flex items-center justify-center gap-2 mt-2"
              >
                <Wand2 size={16} />
                <span>Generate Course with AI</span>
              </button>
            </form>
          )}
        </div>
      )}

      {activeTab === "manual" && (
        <div className="max-w-2xl mx-auto w-full">
          <form onSubmit={handleCreateCourseManual} className="glass-panel p-6 sm:p-8 rounded-2xl border border-gray-850 bg-card/20 flex flex-col gap-5">
            <div className="flex items-center gap-2 border-b border-gray-850 pb-4 mb-2">
              <Layers className="text-purple-400" size={20} />
              <div>
                <h2 className="text-base font-bold text-white">Manual Course Builder</h2>
                <p className="text-xs text-gray-400">Initialize a new learning path manually. Once created, modules and lectures can be attached.</p>
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Course Title</label>
              <input 
                type="text" 
                value={manualTitle}
                onChange={(e) => setManualTitle(e.target.value)}
                placeholder="e.g. Full-Stack JavaScript bootcamp"
                className="bg-background border border-gray-800 rounded-xl px-4 py-2.5 text-sm focus:outline-hidden focus:border-purple-500 text-white"
                required
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Instructor Name</label>
                <input 
                  type="text" 
                  value={manualInstructor}
                  onChange={(e) => setManualInstructor(e.target.value)}
                  placeholder="e.g. Sebastian Ramirez"
                  className="bg-background border border-gray-800 rounded-xl px-4 py-2.5 text-sm focus:outline-hidden focus:border-purple-500 text-white"
                  required
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Duration Estimate</label>
                <input 
                  type="text" 
                  value={manualDuration}
                  onChange={(e) => setManualDuration(e.target.value)}
                  placeholder="e.g. 12 Hours"
                  className="bg-background border border-gray-800 rounded-xl px-4 py-2.5 text-sm focus:outline-hidden focus:border-purple-500 text-white"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Category</label>
                <select 
                  value={manualCategory}
                  onChange={(e) => setManualCategory(e.target.value)}
                  className="bg-background border border-gray-800 rounded-xl px-4 py-2.5 text-sm focus:outline-hidden focus:border-purple-500 text-white"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Difficulty Level</label>
                <select 
                  value={manualLevel}
                  onChange={(e) => setManualLevel(e.target.value)}
                  className="bg-background border border-gray-800 rounded-xl px-4 py-2.5 text-sm focus:outline-hidden focus:border-purple-500 text-white"
                >
                  {LEVELS.map((l) => (
                    <option key={l} value={l}>{l}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-bold text-gray-400 uppercase tracking-wider">Course Description</label>
              <textarea 
                value={manualDesc}
                onChange={(e) => setManualDesc(e.target.value)}
                placeholder="Describe what learners will achieve after completing this path..."
                className="bg-background border border-gray-800 rounded-xl px-4 py-2.5 text-sm focus:outline-hidden focus:border-purple-500 h-24 text-white resize-none"
                required
              />
            </div>

            <button 
              type="submit"
              className="w-full py-3 bg-purple-600 hover:bg-purple-700 text-white font-bold text-sm rounded-xl transition-all cursor-pointer shadow-md flex items-center justify-center gap-2 mt-2"
            >
              <PlusCircle size={16} />
              <span>Create Course Base</span>
            </button>
          </form>
        </div>
      )}

    </div>
  );
}
