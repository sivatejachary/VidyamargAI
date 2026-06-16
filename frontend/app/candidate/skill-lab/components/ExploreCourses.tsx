"use client";

import { useState, useCallback, useMemo } from "react";
import { Brain, Clock, BookOpen } from "lucide-react";
import { HorizontalCarousel } from "@/components/lms/HorizontalCarousel";
import { CourseCard } from "@/components/lms/CourseCard";
import CareerPathCard from "@/components/lms/CareerPathCard";
import CareerPathDetail from "@/components/lms/CareerPathDetail";
import LMSSearchBar from "@/components/lms/SearchBar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ProgressBar } from "@/components/ui/Progress";
import type { CareerPath } from "@/types/lms.types";
import {
  CAREER_PATHS,
  CATEGORY_GRADIENTS,
  DEFAULT_GRADIENT,
} from "@/types/lms.types";

/* ═══════════════════════════════════════════════════════
   ExploreCourses — Goal-based learning discovery
   Career paths are the primary entry point.
   Technology-first navigation removed in favor of
   Coursera / Google Career Certificate UX patterns.
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
  const [selectedPath, setSelectedPath] = useState<CareerPath | null>(null);

  /* ─── Enrolled IDs set for quick lookup ─── */
  const enrolledSet = useMemo(
    () => new Set(enrolledCourseIds.map((id: any) => id)),
    [enrolledCourseIds]
  );

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

  /* ─── Filter courses by search only (no skill chips) ─── */
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

  /* ─── Continue Learning: enrolled with 0 < progress < 100 ─── */
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
          <div
            className={`h-[100px] w-full bg-gradient-to-br ${gradientClass} flex items-center justify-center relative`}
          >
            <Brain size={28} className="text-white/30" />
            <div className="absolute bottom-2 left-2">
              <span className="text-white text-[10px] font-bold bg-black/30 backdrop-blur-sm px-2 py-0.5 rounded">
                {progress}% complete
              </span>
            </div>
          </div>
          <div className="p-3.5 flex-1 flex flex-col gap-2">
            <h4 className="text-sm font-semibold text-foreground line-clamp-2 leading-snug">
              {course.title}
            </h4>
            <span className="text-xs text-muted-foreground">{remainingLessons} lessons left</span>
            <ProgressBar value={progress} className="mt-auto" />
            <Button
              variant="outline"
              size="xs"
              className="w-full mt-1"
              onClick={() => handleGoToLesson(course, "video")}
            >
              Resume
            </Button>
          </div>
        </Card>
      );
    },
    [handleGoToLesson]
  );

  /* ─── Career Path Detail View ─── */
  if (selectedPath) {
    return (
      <CareerPathDetail
        path={selectedPath}
        courses={courses}
        enrollments={enrollments}
        onBack={() => setSelectedPath(null)}
        onStartCourse={handleStartCourse}
        onResumeCourse={(c) => handleGoToLesson(c, "video")}
      />
    );
  }

  /* ─── Course Detail View ─── */
  if (activeView === "course-details") {
    return null;
  }

  /* ─── Search results mode ─── */
  if (isSearchActive) {
    return (
      <div className="flex flex-col gap-6 w-full">
        <LMSSearchBar
          value={courseSearchQuery}
          onChange={handleSearchChange}
          onClear={handleSearchClear}
        />

        {filteredCourses.length > 0 ? (
          <div>
            <h3 className="text-base font-bold text-foreground mb-1">
              Results for &ldquo;{searchDebounced}&rdquo;
            </h3>
            <p className="text-xs text-muted-foreground mb-4">
              {filteredCourses.length} course{filteredCourses.length !== 1 ? "s" : ""} found
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
              {filteredCourses.map((c: any) => (
                <CourseCard
                  key={c.id}
                  course={c}
                  enrollment={getEnrollment(c.id)}
                  onEnroll={async (id) => {
                    const course = courses.find((co: any) => co.id === id);
                    if (course) await handleStartCourse(course);
                  }}
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
            <p className="text-sm font-semibold text-muted-foreground">
              No courses found for &ldquo;{searchDebounced}&rdquo;
            </p>
            <Button variant="outline" size="sm" onClick={handleSearchClear}>
              Browse all courses
            </Button>
          </div>
        )}
      </div>
    );
  }

  /* ═══════════════════════════════════════════════════════
     Main Explore View — Goal-based discovery
     Career Paths → Continue Learning → Recommended → Trending
     ═══════════════════════════════════════════════════════ */
  return (
    <div className="flex flex-col gap-8 w-full">
      {/* Search bar */}
      <LMSSearchBar
        value={courseSearchQuery}
        onChange={handleSearchChange}
        onClear={handleSearchClear}
        placeholder="Search courses, skills, topics..."
      />

      {/* ── Section 1: Choose Your Career Path (Primary Hero) ── */}
      <section>
        <div className="mb-4">
          <h2 className="text-xl font-bold text-foreground">Choose Your Career Path</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Goal-based learning tracks designed by industry experts
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {CAREER_PATHS.map((path) => (
            <CareerPathCard
              key={path.id}
              path={path}
              onViewPath={setSelectedPath}
            />
          ))}
        </div>
      </section>

      {/* ── Section 2: Continue Learning ── */}
      {continueLearning.length > 0 && (
        <HorizontalCarousel
          title="Continue Learning"
          subtitle="Pick up where you left off"
          items={continueLearning}
          renderItem={renderContinueLearningCard}
          variant="course"
        />
      )}

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
              onEnroll={async (id) => {
                const c = courses.find((co: any) => co.id === id);
                if (c) await handleStartCourse(c);
              }}
              onResume={(c) => handleGoToLesson(c, "video")}
              showTrending
            />
          )}
          variant="course"
        />
      )}

      {/* All courses grid view */}
      {showAllCourses && (
        <div className="flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold text-foreground">
              All Courses ({courses.length})
            </h3>
            <Button
              variant="ghost"
              size="xs"
              onClick={() => setShowAllCourses(false)}
            >
              ← Back to Explore
            </Button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {courses.map((c: any) => (
              <CourseCard
                key={c.id}
                course={c}
                enrollment={getEnrollment(c.id)}
                onEnroll={async (id) => {
                  const course = courses.find((co: any) => co.id === id);
                  if (course) await handleStartCourse(course);
                }}
                onResume={(course) => handleGoToLesson(course, "video")}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
