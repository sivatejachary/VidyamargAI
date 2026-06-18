"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import { Brain, Clock, BookOpen, X, ArrowRight, CheckCircle, Circle, Sparkles, Award, Flame, TrendingUp } from "lucide-react";
import { HorizontalCarousel } from "@/components/lms/HorizontalCarousel";
import { CourseCard } from "@/components/lms/CourseCard";
import CareerPathCard from "@/components/lms/CareerPathCard";
import LMSSearchBar from "@/components/lms/SearchBar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ProgressBar } from "@/components/ui/Progress";
import type { CareerPath } from "@/types/lms.types";
import { apiService } from "@/services/api";
import { useAuthStore } from "@/store/authStore";
import {
  CAREER_PATHS,
  PATH_BADGES,
  CATEGORY_GRADIENTS,
  DEFAULT_GRADIENT,
} from "@/types/lms.types";

interface ExploreCoursesProps {
  courses: any[];
  enrollments: any[];
  enrolledCourseIds: any[];
  readinessScore: number;
  activeView: string;
  setActiveView: (view: any) => void;
  selectedCourse: any;
  setSelectedCourse: (course: any) => void;
  activeEnrollmentCourse: any;
  activeEnrollmentCurriculum: any;
  handleStartCourse: (course: any) => Promise<void>;
  handleGoToLesson: (course: any, type: string) => Promise<void>;
  completedLessonIds: number[];
  courseSearchQuery: string;
  setCourseSearchQuery: (val: string) => void;
  courseCategoryFilter: string;
  setCourseCategoryFilter: (val: string) => void;
  showAllCourses: boolean;
  setShowAllCourses: (val: boolean) => void;
}

export default function ExploreCourses({
  courses,
  enrollments,
  enrolledCourseIds,
  activeView,
  setActiveView,
  setSelectedCourse,
  activeEnrollmentCourse,
  activeEnrollmentCurriculum,
  handleStartCourse,
  handleGoToLesson,
  completedLessonIds,
  courseSearchQuery,
  setCourseSearchQuery,
  courseCategoryFilter,
  setCourseCategoryFilter,
  showAllCourses,
  setShowAllCourses,
}: ExploreCoursesProps) {
  const [searchDebounced, setSearchDebounced] = useState(courseSearchQuery);
  const [debounceTimer, setDebounceTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
  const [modalPath, setModalPath] = useState<CareerPath | null>(null);
  
  // Real-time backend stats states
  const [stats, setStats] = useState<any>(null);
  const [careerPaths, setCareerPaths] = useState<any[]>([]);
  const [loadingStats, setLoadingStats] = useState(true);
  const { fullName } = useAuthStore();
  const userName = fullName ? fullName.split(" ")[0] : "Learner";

  const timeOfDay = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return "Morning";
    if (hour < 18) return "Afternoon";
    return "Evening";
  }, []);

  const loadStatsAndPaths = useCallback(() => {
    setLoadingStats(true);
    apiService.getAIMentorProfile()
      .then((res) => setStats(res))
      .catch((err) => console.error("Failed to fetch AI stats:", err));

    apiService.getCareerPaths()
      .then((res) => {
        setCareerPaths(res);
        setLoadingStats(false);
      })
      .catch((err) => {
        console.error("Failed to fetch career paths:", err);
        setLoadingStats(false);
      });
  }, []);

  useEffect(() => {
    loadStatsAndPaths();
  }, [loadStatsAndPaths, enrollments]);

  const handleSelectGoal = async (goal: string) => {
    try {
      await apiService.updateCareerGoal(goal);
      loadStatsAndPaths();
    } catch (err) {
      console.error("Failed to update goal:", err);
    }
  };

  /* ─── Enrolled IDs set ─── */
  const enrolledSet = useMemo(
    () => new Set(enrolledCourseIds.map((id: any) => id)),
    [enrolledCourseIds]
  );

  /* ─── Lock body scroll when modal open ─── */
  useEffect(() => {
    if (modalPath) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [modalPath]);

  /* ─── Search with debounce ─── */
  const handleSearchChange = useCallback(
    (value: string) => {
      setCourseSearchQuery(value);
      if (debounceTimer) clearTimeout(debounceTimer);
      const timer = setTimeout(() => setSearchDebounced(value), 300);
      setDebounceTimer(timer);
    },
    [setCourseSearchQuery, debounceTimer]
  );

  const handleSearchClear = useCallback(() => {
    setCourseSearchQuery("");
    setSearchDebounced("");
  }, [setCourseSearchQuery]);

  /* ─── Filter courses by search ─── */
  const filteredCourses = useMemo(() => {
    const query = searchDebounced.toLowerCase();
    if (!query) return courses;
    return courses.filter((c: any) =>
      c.title?.toLowerCase().includes(query) ||
      c.instructor?.toLowerCase().includes(query) ||
      c.category?.toLowerCase().includes(query) ||
      (c.skills || []).some((s: string) => s.toLowerCase().includes(query))
    );
  }, [courses, searchDebounced]);

  const isSearchActive = searchDebounced.trim().length > 0;

  /* ─── Recommended For You ─── */
  const recommended = useMemo(() => {
    return courses
      .filter((c: any) => !enrolledSet.has(c.id))
      .sort((a: any, b: any) => (b.rating ?? 0) - (a.rating ?? 0))
      .slice(0, 10);
  }, [courses, enrolledSet]);

  /* ─── Trending Now ─── */
  const trending = useMemo(() => {
    return [...courses]
      .sort((a: any, b: any) => (b.enrollment_count ?? 0) - (a.enrollment_count ?? 0))
      .slice(0, 8);
  }, [courses]);

  /* ─── Get courses matching a career path ─── */
  const getPathCourses = useCallback(
    (path: CareerPath) => {
      const pathSkillsLower = path.skills.map((s) => s.toLowerCase());
      const matched = courses.filter((c: any) => {
        const courseSkills = (c.skills || []).map((s: string) => s.toLowerCase());
        const courseCategory = (c.category || "").toLowerCase();
        const courseTag = (c.tag || "").toLowerCase();
        return pathSkillsLower.some(
          (ps) =>
            courseSkills.some((cs: string) => cs.includes(ps) || ps.includes(cs)) ||
            courseCategory.includes(ps) ||
            courseTag.includes(ps)
        );
      });
      return matched.length > 0 ? matched : courses;
    },
    [courses]
  );

  /* ─── Get courses matching a specific roadmap step ─── */
  const getCoursesForStep = useCallback(
    (step: string, pathCourses: any[]) => {
      const stepLower = step.toLowerCase();
      let keywords: string[] = [stepLower];
      if (stepLower.includes("html") || stepLower.includes("css")) {
        keywords = ["html", "css", "web development", "frontend"];
      } else if (stepLower.includes("javascript") || stepLower.includes("js")) {
        keywords = ["javascript", "js", "web development", "react", "next.js"];
      } else if (stepLower.includes("typescript")) {
        keywords = ["typescript", "ts", "next.js", "react"];
      } else if (stepLower.includes("react")) {
        keywords = ["react", "next.js"];
      } else if (stepLower.includes("next.js")) {
        keywords = ["next.js", "react"];
      } else if (stepLower.includes("python")) {
        keywords = ["python"];
      } else if (stepLower.includes("databases") || stepLower.includes("sql")) {
        keywords = ["sql", "database", "postgres"];
      } else if (stepLower.includes("apis") || stepLower.includes("node.js")) {
        keywords = ["api", "node.js", "fastapi", "backend"];
      } else if (stepLower.includes("ml fundamentals") || stepLower.includes("deep learning") || stepLower.includes("llms") || stepLower.includes("math")) {
        keywords = ["machine learning", "ml", "python", "ai"];
      } else if (stepLower.includes("aws core") || stepLower.includes("cloud") || stepLower.includes("networking")) {
        keywords = ["aws", "cloud", "devops"];
      } else if (stepLower.includes("architecture") || stepLower.includes("system design")) {
        keywords = ["system design", "scalability"];
      } else if (stepLower.includes("docker") || stepLower.includes("ci/cd") || stepLower.includes("kubernetes")) {
        keywords = ["docker", "aws", "kubernetes", "devops"];
      } else if (stepLower.includes("cryptography") || stepLower.includes("ethical hacking") || stepLower.includes("siem")) {
        keywords = ["security", "cybersecurity", "networking"];
      }

      return pathCourses.filter((c: any) => {
        const titleLower = (c.title || "").toLowerCase();
        const categoryLower = (c.category || "").toLowerCase();
        const descLower = (c.description || "").toLowerCase();
        const skillsLower = (c.skills || []).map((s: string) => s.toLowerCase());

        return keywords.some(kw => 
          titleLower.includes(kw) || 
          categoryLower.includes(kw) || 
          descLower.includes(kw) ||
          skillsLower.some((s: string) => s.includes(kw) || kw.includes(s))
        );
      });
    },
    []
  );

  const getStepProgressStatus = useCallback(
    (stepIndex: number, pathSteps: string[], pathCourses: any[]) => {
      const stepCourses = getCoursesForStep(pathSteps[stepIndex], pathCourses);
      if (stepCourses.length === 0) return "upcoming";

      const stepEnrollments = stepCourses.map(c => enrollments.find(e => e.course_id === c.id)).filter(Boolean);
      if (stepEnrollments.length === 0) return "upcoming";

      const allCompleted = stepEnrollments.every(e => e.progress >= 100);
      if (allCompleted) return "complete";

      const someProgress = stepEnrollments.some(e => e.progress > 0);
      if (someProgress) return "current";

      return "upcoming";
    },
    [enrollments, getCoursesForStep]
  );

  const getEnrollment = useCallback(
    (courseId: string | number) => enrollments.find((e: any) => e.course_id === courseId),
    [enrollments]
  );

  const renderCourseCard = useCallback(
    (course: any) => (
      <CourseCard
        key={course.id}
        course={course}
        enrollment={getEnrollment(course.id)}
        onEnroll={async (id) => {
          const c = courses.find((co: any) => co.id === id);
          if (c) await handleStartCourse(c);
        }}
        onResume={(c) => handleGoToLesson(c, "video")}
      />
    ),
    [getEnrollment, courses, handleStartCourse, handleGoToLesson]
  );

  if (isSearchActive) {
    return (
      <div className="flex flex-col gap-6 w-full">
        <LMSSearchBar value={courseSearchQuery} onChange={handleSearchChange} onClear={handleSearchClear} />
        {filteredCourses.length > 0 ? (
          <div>
            <h3 className="text-base font-bold text-foreground mb-1">Results for &ldquo;{searchDebounced}&rdquo;</h3>
            <p className="text-xs text-muted-foreground mb-4">{filteredCourses.length} course{filteredCourses.length !== 1 ? "s" : ""} found</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {filteredCourses.map((c: any) => (
                <CourseCard
                  key={c.id}
                  course={c}
                  enrollment={getEnrollment(c.id)}
                  onEnroll={async (id) => { const course = courses.find((co: any) => co.id === id); if (course) await handleStartCourse(course); }}
                  onResume={(course) => handleGoToLesson(course, "video")}
                />
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-16 gap-4">
            <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center">
              <BookOpen size={28} className="text-muted-foreground" />
            </div>
            <p className="text-sm font-semibold text-muted-foreground">No courses found for &ldquo;{searchDebounced}&rdquo;</p>
            <Button variant="outline" size="sm" onClick={handleSearchClear}>Browse all courses</Button>
          </div>
        )}
      </div>
    );
  }

  // Active user details
  const healthScore = stats?.health_score ? Math.round(stats.health_score) : 84;
  const levelNum = stats?.level || 8;
  const xpPoints = stats?.xp || 1250;
  const streakDays = stats?.streak || 12;
  const careerGoal = stats?.career_goal || "Frontend Engineer";
  const onTrackPercent = Math.round(healthScore * 0.85);

  return (
    <>
      <div className="flex flex-col gap-8 w-full pb-20">
        
        {/* Search bar */}
        <LMSSearchBar
          value={courseSearchQuery}
          onChange={handleSearchChange}
          onClear={handleSearchClear}
          placeholder="Search courses, skills, topics..."
        />

        {/* ── Section 1: Hero Section (AI Learning OS Welcome) ── */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-indigo-950/80 to-slate-900 border border-indigo-500/20 p-4 sm:p-5 shadow-xl flex flex-col md:flex-row justify-between gap-4">
          <div className="absolute top-0 right-0 w-60 h-60 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />
          
          <div className="relative z-10 flex-1 space-y-3">
            <div className="space-y-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 font-mono bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-full">
                VidyamargAI Skill Lab 3.0
              </span>
              <h2 className="text-lg sm:text-xl font-black text-white leading-tight mt-1">
                Good {timeOfDay}, {userName} 👋
              </h2>
            </div>

            <div className="flex flex-wrap gap-2 text-[11px] font-semibold text-slate-350">
              <div className="flex items-center gap-1.5 bg-black/30 backdrop-blur-md px-2.5 py-1 rounded-lg border border-white/5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-lg shadow-emerald-500/50 animate-pulse" />
                <span>Learning Health: <strong>{healthScore}%</strong></span>
              </div>
              <div className="flex items-center gap-1.5 bg-black/30 backdrop-blur-md px-2.5 py-1 rounded-lg border border-white/5">
                <Award size={12} className="text-amber-400" />
                <span>Level {levelNum}</span>
              </div>
              <div className="flex items-center gap-1.5 bg-black/30 backdrop-blur-md px-2.5 py-1 rounded-lg border border-white/5">
                <Sparkles size={12} className="text-violet-400" />
                <span>{xpPoints} XP</span>
              </div>
              <div className="flex items-center gap-1.5 bg-black/30 backdrop-blur-md px-2.5 py-1 rounded-lg border border-white/5">
                <Flame size={12} className="text-orange-500 fill-orange-500/10" />
                <span>{streakDays} Day Streak</span>
              </div>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl p-3 max-w-lg">
              <p className="text-[9px] uppercase font-bold text-slate-400 tracking-wider">Current Goal</p>
              <h4 className="text-xs font-bold text-white mb-0.5">{careerGoal}</h4>
              <p className="text-[11px] text-indigo-200/90">
                🤖 AI Insight: &ldquo;You're {onTrackPercent}% on track to your goal.&rdquo;
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2 pt-1">
              {activeEnrollmentCourse && (
                <button
                  className="px-3.5 py-1.8 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-[11px] font-bold shadow-md shadow-indigo-600/30 flex items-center gap-1.5 cursor-pointer transition-all hover:-translate-y-0.5"
                  onClick={() => handleGoToLesson(activeEnrollmentCourse, "video")}
                >
                  Resume Learning →
                </button>
              )}
              <button
                className="px-3.5 py-1.8 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-[11px] font-bold border border-slate-700/50 flex items-center gap-1.5 cursor-pointer transition-all"
                onClick={() => setActiveView("ai-mentor")}
              >
                Ask AI Mentor
              </button>
              <button
                className="px-3.5 py-1.8 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 rounded-lg text-[11px] font-bold border border-indigo-500/20 flex items-center gap-1.5 cursor-pointer transition-all"
                onClick={() => setActiveView("ai-mentor")}
              >
                Generate Study Plan
              </button>
            </div>
          </div>
        </div>

        {/* ── Section 2: Learning Health Dashboard Grid ── */}
        <section className="space-y-3">
          <div>
            <h3 className="text-base font-bold text-foreground">Learning Health Dashboard</h3>
            <p className="text-[11px] text-muted-foreground">Real-time stats from your autonomous learning logs</p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: "Courses Enrolled", val: enrollments.length, change: "+1 this week", type: "info" },
              { label: "Courses Completed", val: stats?.completed_courses || 0, change: "100% finished", type: "success" },
              { label: "Hours Learned", val: `${stats?.hours_learned || 0}h`, change: "Active this week", type: "info" },
              { label: "Certificates Earned", val: stats?.completed_certs || 0, change: "Verified PDF", type: "success" },
              { label: "Current Streak", val: `${streakDays} days`, change: "Daily habit active", type: "success" },
              { label: "XP Earned", val: `${xpPoints} XP`, change: "+150 XP today", type: "success" },
              { label: "Weekly Progress", val: `${Math.round(stats?.weekly_progress || 0)}%`, change: "Goal: 100%", type: "info" },
              { label: "Learning Health Score", val: `${healthScore}%`, change: "Good Progress", type: "success" },
            ].map((stat, idx) => (
              <Card
                key={idx}
                className="relative overflow-hidden border border-border/80 p-3 rounded-xl flex flex-col justify-between hover:scale-[1.02] hover:shadow-sm transition-all duration-350 cursor-default"
              >
                <div className="space-y-0.5">
                  <p className="text-[9px] uppercase font-bold text-muted-foreground tracking-wider">{stat.label}</p>
                  <h3 className="text-base sm:text-lg font-black text-foreground">{stat.val}</h3>
                </div>
                <div className="flex items-center gap-1 mt-2 text-[9px] text-muted-foreground font-semibold">
                  <TrendingUp size={11} className={stat.type === "success" ? "text-emerald-500" : "text-indigo-500"} />
                  <span>{stat.change}</span>
                </div>
              </Card>
            ))}
          </div>
        </section>

        {/* ── Section 3: Continue Learning (Netflix-Style Carousel) ── */}
        {enrollments.filter(e => e.progress > 0 && e.progress < 100).length > 0 && (
          <section className="space-y-4">
            <div>
              <h3 className="text-lg font-bold text-foreground">Continue Learning</h3>
              <p className="text-xs text-muted-foreground">Pick up right where you left off</p>
            </div>

            <div className="flex gap-4 overflow-x-auto pb-3 pt-1 scrollbar-hide -mx-4 px-4 sm:-mx-6 sm:px-6">
              {enrollments
                .filter(e => e.progress > 0 && e.progress < 100)
                .map((enrollment: any) => {
                  const course = courses.find((c: any) => c.id === enrollment.course_id) || enrollment.course;
                  if (!course) return null;
                  
                  const progress = Math.round(enrollment.progress || 0);
                  const remainingHours = Math.round((100 - progress) * 0.08 + 1);
                  const gradient = CATEGORY_GRADIENTS[course.category] || DEFAULT_GRADIENT;

                  return (
                    <div
                      key={enrollment.id}
                      className="min-w-[240px] sm:min-w-[280px] max-w-[280px] bg-card border border-border/75 rounded-2xl overflow-hidden shadow-sm hover:scale-[1.03] hover:shadow-md transition-all flex flex-col"
                    >
                      <div className={`h-24 w-full bg-gradient-to-br ${gradient} flex items-center justify-center relative`}>
                        <Brain size={30} className="text-white/20" />
                        <span className="absolute bottom-2 left-2 text-[9px] font-bold text-white bg-black/40 backdrop-blur-md px-2 py-0.5 rounded-full">
                          {progress}% complete
                        </span>
                      </div>
                      
                      <div className="p-4 flex-1 flex flex-col justify-between gap-3">
                        <div className="space-y-1">
                          <h4 className="text-xs font-bold text-foreground line-clamp-1 leading-snug">
                            {course.title}
                          </h4>
                          <p className="text-[10px] text-muted-foreground">
                            Estimated {remainingHours} hrs remaining
                          </p>
                        </div>
                        
                        <div className="space-y-2">
                          <ProgressBar value={progress} className="h-1.5" />
                          <Button
                            variant="primary"
                            size="xs"
                            className="w-full font-bold"
                            onClick={() => handleGoToLesson(course, "video")}
                          >
                            Resume
                          </Button>
                        </div>
                      </div>
                    </div>
                  );
                })}
            </div>
          </section>
        )}

        {/* ── Section 4: Career Growth Paths ── */}
        <section className="space-y-3">
          <div>
            <h3 className="text-base font-bold text-foreground">Career Growth Paths</h3>
            <p className="text-[11px] text-muted-foreground">Choose your goal path and let the AI system direct your learning</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {careerPaths.map((path) => {
              const isActive = careerGoal.toLowerCase() === path.name.toLowerCase();
              return (
                <div
                  key={path.id}
                  className={`relative overflow-hidden rounded-xl border p-3.5 flex flex-col justify-between gap-3 transition-all duration-300 hover:shadow-sm cursor-pointer ${
                    isActive 
                      ? "border-indigo-500 bg-indigo-500/5 shadow-sm"
                      : "border-border hover:border-indigo-500/40 bg-card"
                  }`}
                  onClick={() => handleSelectGoal(path.name)}
                >
                  <div className="space-y-2">
                    <div className="flex justify-between items-start">
                      <h4 className="text-xs font-bold text-foreground">{path.name}</h4>
                      <span className={`text-[9px] font-bold px-2 py-0.5 rounded-md ${
                        path.match_percentage >= 80 
                          ? "bg-emerald-500/10 text-emerald-500" 
                          : "bg-indigo-500/10 text-indigo-400"
                      }`}>
                        {path.match_percentage}% Match
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-1">
                      {path.skills.slice(0, 4).map((skill: string) => (
                        <span
                          key={skill}
                          className="text-[8px] font-semibold bg-muted px-1.5 py-0.5 rounded text-muted-foreground border border-border/20"
                        >
                          {skill}
                        </span>
                      ))}
                      {path.skills.length > 4 && (
                        <span className="text-[8px] font-semibold text-muted-foreground px-0.5">+{path.skills.length - 4} more</span>
                      )}
                    </div>
                  </div>

                  <div className="space-y-1.5 pt-2 border-t border-border/40">
                    <div className="flex justify-between text-[9px] text-muted-foreground">
                      <span>Est. Time: {path.duration_estimate}</span>
                      <span>Progress: {path.progress}%</span>
                    </div>
                    <ProgressBar value={path.progress} className="h-1" />
                    <Button
                      variant={isActive ? "primary" : "outline"}
                      size="xs"
                      className="w-full mt-1 font-bold text-[9px]"
                    >
                      {isActive ? "Selected Path ✓" : "Activate Path"}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ── Section 5: All Available Courses ── */}
        <section className="space-y-3">
          <div>
            <h3 className="text-base font-bold text-foreground">All Available Courses</h3>
            <p className="text-[11px] text-muted-foreground">Browse all courses and enroll in the ones that interest you</p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {courses.map((course: any) => renderCourseCard(course))}
          </div>
        </section>

      </div>

      {/* ── Section 5: AI Mentor Floating Card (Persistent Actions) ── */}
      {stats?.next_best_actions?.length > 0 && (
        <div className="fixed bottom-6 right-6 z-50 max-w-sm bg-slate-900/90 backdrop-blur-xl border border-indigo-500/30 rounded-2xl p-4.5 shadow-2xl text-white flex items-start gap-3 animate-bounce-subtle">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center shrink-0 shadow-lg shadow-indigo-600/30">
            <span>🤖</span>
          </div>
          <div className="flex-1 space-y-1">
            <h5 className="text-[10px] uppercase font-bold text-indigo-400 tracking-wider">AI Mentor Recommendation</h5>
            <p className="text-xs font-bold text-white line-clamp-2">
              {stats.next_best_actions[0]}
            </p>
            <p className="text-[10px] text-indigo-200">
              Estimated duration: {stats.estimated_time || "35 Minutes"}
            </p>
            <button
              onClick={() => setActiveView("ai-mentor")}
              className="mt-2 text-[10px] font-black text-indigo-400 hover:text-indigo-300 flex items-center gap-1 cursor-pointer transition-colors"
            >
              <span>Ask Mentor →</span>
            </button>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              e.currentTarget.parentElement?.remove();
            }}
            className="text-white/40 hover:text-white transition-colors cursor-pointer"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Career Path Roadmap modal from existing code */}
      {modalPath && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-background border border-border w-full max-w-3xl h-[85vh] rounded-2xl overflow-hidden flex flex-col shadow-2xl">
            {/* Header info */}
            <div className={`p-5 sm:p-6 bg-gradient-to-r ${modalPath.gradient || DEFAULT_GRADIENT} text-white flex justify-between items-start`}>
              <div className="space-y-1">
                <h2 className="text-xl font-bold">{modalPath.title}</h2>
                <p className="text-xs text-white/80">{modalPath.subtitle}</p>
                <div className="flex flex-wrap items-center gap-3 mt-4 text-[10px]">
                  <span className="flex items-center gap-1.5"><BookOpen size={13} />{modalPath.courseCount} courses</span>
                  <span className="w-px h-3 bg-white/30" />
                  <span className="flex items-center gap-1.5"><Clock size={13} />{modalPath.totalHours}h total</span>
                  {modalPath.badge && PATH_BADGES[modalPath.badge] && (
                    <>
                      <span className="w-px h-3 bg-white/30" />
                      <span className="bg-white/20 px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider">{PATH_BADGES[modalPath.badge].label}</span>
                    </>
                  )}
                </div>
              </div>
              <button onClick={() => setModalPath(null)} className="text-white/60 hover:text-white transition-colors cursor-pointer">
                <X size={20} />
              </button>
            </div>

            {/* Steps timeline list */}
            <div className="flex-1 overflow-y-auto p-5 sm:p-6 bg-slate-50 dark:bg-slate-900/40">
              {(() => {
                const pathCourses = getPathCourses(modalPath);
                return (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-sm font-bold text-foreground">Learning Roadmap</h3>
                      <p className="text-xs text-muted-foreground mt-0.5">Follow the steps in this path to gain job-ready skills</p>
                    </div>

                    <div className="relative border-l-2 border-slate-200 dark:border-slate-800 pl-6 ml-3.5 space-y-8">
                      {modalPath.steps.map((step, index) => {
                        const stepCourses = getCoursesForStep(step, pathCourses);
                        const progressStatus = getStepProgressStatus(index, modalPath.steps, pathCourses);

                        let nodeIcon = <Circle size={14} className="text-muted-foreground/50" />;
                        if (progressStatus === "complete") {
                          nodeIcon = <CheckCircle size={14} className="text-emerald-500 fill-emerald-500/10" />;
                        } else if (progressStatus === "current") {
                          nodeIcon = <span className="w-2.5 h-2.5 rounded-full bg-primary" />;
                        }

                        return (
                          <div key={step} className="relative">
                            <div className={`absolute -left-[35px] top-1 w-[18px] h-[18px] rounded-full border-2 bg-card flex items-center justify-center ${
                              progressStatus === "complete" 
                                ? "border-emerald-500" 
                                : progressStatus === "current"
                                ? "border-primary"
                                : "border-slate-350 dark:border-slate-800"
                            }`}>
                              {nodeIcon}
                            </div>

                            <div className="mb-3">
                              <span className={`text-[10px] font-bold uppercase tracking-wider ${
                                progressStatus === "complete"
                                  ? "text-emerald-600 dark:text-emerald-400"
                                  : progressStatus === "current"
                                  ? "text-primary"
                                  : "text-muted-foreground"
                              }`}>
                                Step {index + 1}
                              </span>
                              <div className="flex items-center gap-2">
                                <h4 className="text-sm font-bold text-foreground">{step}</h4>
                                {progressStatus === "current" && (
                                  <span className="text-[10px] font-semibold text-primary bg-primary/10 px-1.5 py-0.5 rounded-md">
                                    Current Step
                                  </span>
                                )}
                              </div>
                            </div>

                            {stepCourses.length > 0 ? (
                              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                                {stepCourses.map((c: any) => (
                                  <CourseCard
                                    key={c.id}
                                    course={c}
                                    enrollment={getEnrollment(c.id)}
                                    onEnroll={async (id) => {
                                      const course = courses.find((co: any) => co.id === id);
                                      if (course) await handleStartCourse(course);
                                    }}
                                    onResume={(course) => {
                                      setModalPath(null);
                                      handleGoToLesson(course, "video");
                                    }}
                                  />
                                ))}
                              </div>
                            ) : (
                              <div className="bg-card/50 border border-dashed border-border rounded-xl p-3 flex items-center justify-between text-xs text-muted-foreground">
                                <span>No active courses matched this step. Self-paced study recommended.</span>
                                <span className="text-[10px] font-medium bg-muted px-2 py-0.5 rounded">Core Concepts</span>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })()}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
