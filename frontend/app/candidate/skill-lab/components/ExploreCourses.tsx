"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import { Brain, Clock, BookOpen, X, ArrowRight, CheckCircle, Circle } from "lucide-react";
import { HorizontalCarousel } from "@/components/lms/HorizontalCarousel";
import { CourseCard } from "@/components/lms/CourseCard";
import CareerPathCard from "@/components/lms/CareerPathCard";
import LMSSearchBar from "@/components/lms/SearchBar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ProgressBar } from "@/components/ui/Progress";
import type { CareerPath } from "@/types/lms.types";
import {
  CAREER_PATHS,
  PATH_BADGES,
  CATEGORY_GRADIENTS,
  DEFAULT_GRADIENT,
} from "@/types/lms.types";

/* ═══════════════════════════════════════════════════════
   ExploreCourses — Goal-based learning discovery
   ═══════════════════════════════════════════════════════ */

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
  handleStartCourse,
  handleGoToLesson,
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

  /* ─── Continue Learning ─── */
  const continueLearning = useMemo(() => {
    return enrollments
      .filter((e: any) => e.progress > 0 && e.progress < 100)
      .sort((a: any, b: any) => {
        if (a.last_accessed && b.last_accessed)
          return new Date(b.last_accessed).getTime() - new Date(a.last_accessed).getTime();
        return b.progress - a.progress;
      })
      .slice(0, 8)
      .map((enrollment: any) => {
        const course = courses.find((c: any) => c.id === enrollment.course_id) || enrollment.course;
        return { course, enrollment };
      })
      .filter((item: any) => item.course);
  }, [courses, enrollments]);

  /* ─── Section derivations ─── */
  const recommended = useMemo(() => {
    return courses
      .filter((c: any) => !enrolledSet.has(c.id))
      .sort((a: any, b: any) => (b.rating ?? 0) - (a.rating ?? 0))
      .slice(0, 10);
  }, [courses, enrolledSet]);

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
      
      // Smart step keywords matching
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

  /* ─── Get progress status for the career path steps ─── */
  const getStepProgressStatus = useCallback(
    (stepIndex: number, pathSteps: string[], pathCourses: any[]) => {
      // Simple logic: if courses in this step are completed, it's complete.
      // If we are currently learning them, it's active.
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

  /* ─── Render helpers ─── */
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

  const renderContinueLearningCard = useCallback(
    (item: { course: any; enrollment: any }) => {
      const { course, enrollment } = item;
      const progress = Math.round(enrollment.progress || 0);
      const totalModules = course.totalModules || course.modules || 3;
      const remainingLessons = Math.max(1, Math.round(totalModules * ((100 - progress) / 100)));
      const gradientClass = CATEGORY_GRADIENTS[course.category] || DEFAULT_GRADIENT;

      return (
        <Card className="!p-0 !rounded-2xl overflow-hidden w-full h-full flex flex-col" hoverEffect>
          <div className={`h-[100px] w-full bg-gradient-to-br ${gradientClass} flex items-center justify-center relative`}>
            <Brain size={28} className="text-white/30" />
            <div className="absolute bottom-2 left-2">
              <span className="text-white text-[10px] font-bold bg-black/30 backdrop-blur-sm px-2 py-0.5 rounded">
                {progress}% complete
              </span>
            </div>
          </div>
          <div className="p-3.5 flex-1 flex flex-col gap-2">
            <h4 className="text-sm font-semibold text-foreground line-clamp-2 leading-snug">{course.title}</h4>
            <span className="text-xs text-muted-foreground">{remainingLessons} lessons left</span>
            <ProgressBar value={progress} className="mt-auto" />
            <Button variant="outline" size="xs" className="w-full mt-1" onClick={() => handleGoToLesson(course, "video")}>
              Resume
            </Button>
          </div>
        </Card>
      );
    },
    [handleGoToLesson]
  );

  /* ─── Course Detail View ─── */
  if (activeView === "course-details") return null;

  /* ─── Search results mode ─── */
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

  /* ═══════════════════════════════════════════════════════
     Main Explore View
     Search → Continue Learning → Career Paths → Recommended → Trending
     ═══════════════════════════════════════════════════════ */
  return (
    <>
      <div className="flex flex-col gap-8 w-full">
        {/* Search bar */}
        <LMSSearchBar
          value={courseSearchQuery}
          onChange={handleSearchChange}
          onClear={handleSearchClear}
          placeholder="Search courses, skills, topics..."
        />

        {/* ── Section 1: Continue Learning ── */}
        {continueLearning.length > 0 && (
          <HorizontalCarousel
            title="Continue Learning"
            subtitle="Pick up where you left off"
            items={continueLearning}
            renderItem={renderContinueLearningCard}
            variant="course"
          />
        )}

        {/* ── Section 2: Career Growth Paths ── */}
        <section>
          <div className="mb-4">
            <h2 className="text-xl font-bold text-foreground">Career Growth Paths</h2>
            <p className="text-sm text-muted-foreground mt-0.5">
              Choose a career goal and explore related courses
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {CAREER_PATHS.map((path) => (
              <CareerPathCard
                key={path.id}
                path={path}
                onViewPath={(p) => setModalPath(p)}
              />
            ))}
          </div>
        </section>

        {/* ── Section 3: Recommended For You ── */}
        {recommended.length > 0 && (
          <HorizontalCarousel
            title="Recommended For You"
            subtitle="Based on your skill profile and career goals"
            items={recommended}
            renderItem={renderCourseCard}
            variant="course"
            onSeeAll={() => setShowAllCourses(true)}
          />
        )}

        {/* ── Section 4: Trending Now ── */}
        {trending.length > 0 && (
          <HorizontalCarousel
            title="Trending Now"
            subtitle="Most popular courses this month"
            items={trending}
            renderItem={(course: any) => (
              <CourseCard
                course={course}
                enrollment={getEnrollment(course.id)}
                onEnroll={async (id) => { const c = courses.find((co: any) => co.id === id); if (c) await handleStartCourse(c); }}
                onResume={(c) => handleGoToLesson(c, "video")}
                showTrending
              />
            )}
            variant="course"
          />
        )}

        {/* All courses grid */}
        {showAllCourses && (
          <div className="flex flex-col gap-4">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-bold text-foreground">All Courses ({courses.length})</h3>
              <Button variant="ghost" size="xs" onClick={() => setShowAllCourses(false)}>← Back to Explore</Button>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {courses.map((c: any) => (
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
        )}
      </div>

      {/* ═══════════════════════════════════════════════════════
         Career Path Popup Modal
         Shows when user clicks a career path card
         ═══════════════════════════════════════════════════════ */}
      {modalPath && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center animate-in fade-in duration-200"
          onClick={() => setModalPath(null)}
          role="dialog"
          aria-modal="true"
          aria-label={`${modalPath.title} courses`}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/60 backdrop-blur-md" />

          {/* Modal panel */}
          <div
            className="relative z-10 w-full sm:max-w-3xl lg:max-w-4xl max-h-[85vh] bg-card border border-border rounded-t-2xl sm:rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-bottom duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header with gradient */}
            <div className={`relative bg-gradient-to-br ${modalPath.gradient} p-5 sm:p-6 shrink-0`}>
              <div className="absolute inset-0 bg-gradient-to-b from-black/0 to-black/30 pointer-events-none" />
              <div className="relative flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="text-3xl" role="img" aria-hidden="true">{modalPath.icon}</span>
                  <div>
                    <h2 className="text-lg sm:text-xl font-bold text-white">{modalPath.title}</h2>
                    <p className="text-xs text-white/80 mt-0.5">{modalPath.subtitle}</p>
                  </div>
                </div>
                <button
                  onClick={() => setModalPath(null)}
                  className="w-8 h-8 rounded-full bg-white/20 hover:bg-white/30 flex items-center justify-center text-white cursor-pointer transition-colors shrink-0"
                  aria-label="Close"
                >
                  <X size={16} />
                </button>
              </div>

              {/* Stats + Skills */}
              <div className="relative flex flex-wrap items-center gap-3 mt-3.5 text-white/90 text-xs">
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

            {/* Course roadmap steps — scrollable */}
            <div className="flex-1 overflow-y-auto p-5 sm:p-6 bg-slate-50 dark:bg-slate-900/40">
              {(() => {
                const pathCourses = getPathCourses(modalPath);
                return (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-sm font-bold text-foreground">Learning Roadmap</h3>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Follow the steps in this path to gain job-ready skills
                      </p>
                    </div>

                    <div className="relative border-l-2 border-slate-200 dark:border-slate-800 pl-6 ml-3.5 space-y-8">
                      {modalPath.steps.map((step, index) => {
                        const stepCourses = getCoursesForStep(step, pathCourses);
                        const progressStatus = getStepProgressStatus(index, modalPath.steps, pathCourses);

                        // Icon selection based on status
                        let nodeIcon = <Circle size={14} className="text-muted-foreground/50" />;
                        if (progressStatus === "complete") {
                          nodeIcon = <CheckCircle size={14} className="text-emerald-500 fill-emerald-500/10" />;
                        } else if (progressStatus === "current") {
                          nodeIcon = <span className="w-2.5 h-2.5 rounded-full bg-primary" />;
                        }

                        return (
                          <div key={step} className="relative">
                            {/* Roadmap Node Indicator */}
                            <div className={`absolute -left-[35px] top-1 w-[18px] h-[18px] rounded-full border-2 bg-card flex items-center justify-center ${
                              progressStatus === "complete" 
                                ? "border-emerald-500" 
                                : progressStatus === "current"
                                ? "border-primary"
                                : "border-slate-350 dark:border-slate-800"
                            }`}>
                              {nodeIcon}
                            </div>

                            {/* Step Title & Info */}
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

                            {/* Courses for this Step */}
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
