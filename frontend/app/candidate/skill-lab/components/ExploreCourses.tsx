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
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center"
          onClick={() => setModalPath(null)}
          role="dialog"
          aria-modal="true"
          aria-label={`${modalPath.title} courses`}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />

          {/* Modal panel */}
          <div
            className="relative z-10 w-full sm:max-w-3xl lg:max-w-4xl max-h-[85vh] bg-card border border-border rounded-t-2xl sm:rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-bottom duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header with gradient */}
            <div className={`relative bg-gradient-to-br ${modalPath.gradient} p-5 sm:p-6 shrink-0`}>
              <div className="absolute inset-0 bg-gradient-to-b from-black/0 to-black/20 pointer-events-none" />
              <div className="relative flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="text-3xl" role="img" aria-hidden="true">{modalPath.icon}</span>
                  <div>
                    <h2 className="text-lg sm:text-xl font-bold text-white">{modalPath.title}</h2>
                    <p className="text-xs text-white/70 mt-0.5">{modalPath.subtitle}</p>
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
              <div className="relative flex flex-wrap items-center gap-3 mt-3 text-white/80 text-xs">
                <span className="flex items-center gap-1"><BookOpen size={12} />{modalPath.courseCount} courses</span>
                <span className="w-px h-3 bg-white/30" />
                <span className="flex items-center gap-1"><Clock size={12} />{modalPath.totalHours}h total</span>
                {modalPath.badge && PATH_BADGES[modalPath.badge] && (
                  <>
                    <span className="w-px h-3 bg-white/30" />
                    <span className="bg-white/20 px-2 py-0.5 rounded text-[11px] font-semibold">{PATH_BADGES[modalPath.badge].label}</span>
                  </>
                )}
              </div>

              {/* Learning roadmap steps */}
              <div className="relative flex flex-wrap items-center gap-1.5 mt-3">
                {modalPath.steps.map((step, i) => (
                  <span key={step} className="flex items-center gap-1.5">
                    <span className="bg-white/20 text-white text-[10px] font-medium px-2 py-0.5 rounded-md">{step}</span>
                    {i < modalPath.steps.length - 1 && <ArrowRight size={10} className="text-white/40" />}
                  </span>
                ))}
              </div>
            </div>

            {/* Course grid — scrollable */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6">
              {(() => {
                const pathCourses = getPathCourses(modalPath);
                return (
                  <>
                    <p className="text-xs text-muted-foreground mb-4">
                      {pathCourses.length} course{pathCourses.length !== 1 ? "s" : ""} in this path
                    </p>
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                      {pathCourses.map((c: any) => (
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
                  </>
                );
              })()}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
