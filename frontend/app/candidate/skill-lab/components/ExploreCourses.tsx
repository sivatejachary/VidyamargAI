"use client";

import { useState, useCallback, useMemo } from "react";
import { CheckCircle, Brain, Clock, BookOpen, Award, Star } from "lucide-react";
import { HorizontalCarousel } from "@/components/lms/HorizontalCarousel";
import { CourseCard } from "@/components/lms/CourseCard";
import CareerPathCard from "@/components/lms/CareerPathCard";
import RoadmapCard from "@/components/lms/RoadmapCard";
import LMSSearchBar from "@/components/lms/SearchBar";
import SkillFilterChips from "@/components/lms/SkillFilterChips";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ProgressBar } from "@/components/ui/Progress";
import { Skeleton } from "@/components/ui/Skeleton";
import type { LMSCourse, LMSEnrollment, CareerPath, LearningRoadmap } from "@/types/lms.types";
import {
  SKILL_CHIPS,
  CAREER_PATHS,
  LEARNING_ROADMAPS,
  CATEGORY_GRADIENTS,
  DEFAULT_GRADIENT,
} from "@/types/lms.types";

/* ═══════════════════════════════════════════════════════
   ExploreCourses — World-class learning discovery page
   Udemy/Netflix/Coursera-style horizontal carousels
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
    setCourseCategoryFilter("All");
  }, [setCourseSearchQuery, setCourseCategoryFilter]);

  /* ─── Skill filter handler ─── */
  const handleChipSelect = useCallback(
    (chip: string) => {
      setCourseCategoryFilter(chip);
    },
    [setCourseCategoryFilter]
  );

  /* ─── Filter courses by search + chip ─── */
  const filteredCourses = useMemo(() => {
    return courses.filter((c: any) => {
      const query = searchDebounced.toLowerCase();
      const matchesSearch =
        !query ||
        c.title?.toLowerCase().includes(query) ||
        c.instructor?.toLowerCase().includes(query) ||
        c.category?.toLowerCase().includes(query) ||
        (c.skills || []).some((s: string) => s.toLowerCase().includes(query));

      const matchesChip =
        courseCategoryFilter === "All" ||
        c.category?.toLowerCase().includes(courseCategoryFilter.toLowerCase()) ||
        c.tag?.toLowerCase().includes(courseCategoryFilter.toLowerCase()) ||
        (c.skills || []).some((s: string) =>
          s.toLowerCase().includes(courseCategoryFilter.toLowerCase())
        );

      return matchesSearch && matchesChip;
    });
  }, [courses, searchDebounced, courseCategoryFilter]);

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

  /* ─── Section derivations from filtered courses ─── */
  const recommended = useMemo(() => {
    return filteredCourses
      .filter((c: any) => !enrolledSet.has(c.id))
      .sort((a: any, b: any) => (b.rating ?? 0) - (a.rating ?? 0))
      .slice(0, 10);
  }, [filteredCourses, enrolledSet]);

  const trending = useMemo(() => {
    return [...filteredCourses]
      .sort((a: any, b: any) => (b.enrollment_count ?? 0) - (a.enrollment_count ?? 0))
      .slice(0, 8);
  }, [filteredCourses]);

  const topRated = useMemo(() => {
    return [...filteredCourses]
      .filter((c: any) => (c.rating ?? 0) >= 4.0)
      .sort((a: any, b: any) => (b.rating ?? 0) - (a.rating ?? 0))
      .slice(0, 8);
  }, [filteredCourses]);

  const newReleases = useMemo(() => {
    const sixtyDaysAgo = Date.now() - 60 * 24 * 60 * 60 * 1000;
    return filteredCourses
      .filter((c: any) => c.published_at && new Date(c.published_at).getTime() > sixtyDaysAgo)
      .sort((a: any, b: any) => new Date(b.published_at).getTime() - new Date(a.published_at).getTime())
      .slice(0, 6);
  }, [filteredCourses]);

  /* ─── Render helpers ─── */
  const getEnrollment = useCallback(
    (courseId: string | number) => {
      return enrollments.find((e: any) => e.course_id === courseId);
    },
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
          {/* Thumbnail with gradient */}
          <div
            className={`h-[100px] w-full bg-gradient-to-br ${gradientClass} flex items-center justify-center relative`}
          >
            <Brain size={28} className="text-white/30" />
            <div className="absolute bottom-2 left-2">
              <span className="text-white text-10 font-bold bg-black/30 backdrop-blur-sm px-2 py-0.5 rounded">
                {progress}% complete
              </span>
            </div>
          </div>

          {/* Content */}
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

  /* ─── Course Detail View ─── */
  if (activeView === "course-details") {
    return null; // Handled by parent — this component focuses on explore view
  }

  /* ─── Search results mode ─── */
  if (isSearchActive) {
    return (
      <div className="flex flex-col gap-6 w-full">
        {/* Search + Chips */}
        <div className="flex flex-col gap-3">
          <LMSSearchBar
            value={courseSearchQuery}
            onChange={handleSearchChange}
            onClear={handleSearchClear}
          />
          <SkillFilterChips
            chips={SKILL_CHIPS}
            activeChip={courseCategoryFilter}
            onSelect={handleChipSelect}
          />
        </div>

        {filteredCourses.length > 0 ? (
          <HorizontalCarousel
            title={`Results for "${searchDebounced}"`}
            subtitle={`${filteredCourses.length} course${filteredCourses.length !== 1 ? "s" : ""} found`}
            items={filteredCourses}
            renderItem={renderCourseCard}
            variant="course"
          />
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

  /* ─── Main Explore View — Vertical sections with horizontal carousels ─── */
  return (
    <div className="flex flex-col gap-8 w-full">
      {/* Search + Chips */}
      <div className="flex flex-col gap-3">
        <LMSSearchBar
          value={courseSearchQuery}
          onChange={handleSearchChange}
          onClear={handleSearchClear}
        />
        <SkillFilterChips
          chips={SKILL_CHIPS}
          activeChip={courseCategoryFilter}
          onSelect={handleChipSelect}
        />
      </div>

      {/* Section: Continue Learning */}
      {continueLearning.length > 0 && (
        <HorizontalCarousel
          title="Continue Learning"
          subtitle="Pick up where you left off"
          items={continueLearning}
          renderItem={renderContinueLearningCard}
          variant="course"
        />
      )}

      {/* Section: Recommended For You */}
      {recommended.length > 0 && (
        <HorizontalCarousel
          title="Recommended For You"
          subtitle="Based on your skill profile and career goals"
          items={recommended}
          renderItem={renderCourseCard}
          variant="course"
          onSeeAll={() => setShowAllCourses(true)}
          emptyState={
            <p className="text-sm text-muted-foreground">
              Complete your profile to unlock personalized recommendations.
            </p>
          }
        />
      )}

      {/* Section: Trending Now */}
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

      {/* Section: Top Rated */}
      {topRated.length > 0 && (
        <HorizontalCarousel
          title="Top Rated"
          subtitle="Highest rated by our learners"
          items={topRated}
          renderItem={renderCourseCard}
          variant="course"
        />
      )}

      {/* Section: New Releases */}
      {newReleases.length > 0 && (
        <HorizontalCarousel
          title="New Releases"
          subtitle="Fresh courses added recently"
          items={newReleases}
          renderItem={(course: any) => (
            <CourseCard
              course={course}
              enrollment={getEnrollment(course.id)}
              onEnroll={async (id) => {
                const c = courses.find((co: any) => co.id === id);
                if (c) await handleStartCourse(c);
              }}
              onResume={(c) => handleGoToLesson(c, "video")}
              showNew
            />
          )}
          variant="course"
        />
      )}

      {/* Section: Career Growth Paths */}
      <HorizontalCarousel
        title="Career Growth Paths"
        subtitle="Structured tracks to level up your career"
        items={CAREER_PATHS}
        renderItem={(path: CareerPath) => (
          <CareerPathCard
            path={path}
            onViewPath={() => {
              setCourseCategoryFilter(path.skills[0] || "All");
              setShowAllCourses(true);
            }}
          />
        )}
        variant="career"
      />

      {/* Section: Learning Paths (Roadmaps) */}
      <HorizontalCarousel
        title="Learning Paths"
        subtitle="Step-by-step roadmaps from beginner to expert"
        items={LEARNING_ROADMAPS}
        renderItem={(roadmap: LearningRoadmap) => (
          <RoadmapCard
            roadmap={roadmap}
            onStart={() => {
              setCourseCategoryFilter(roadmap.steps[0] || "All");
              setShowAllCourses(true);
            }}
          />
        )}
        variant="roadmap"
      />

      {/* All courses grid view (when "See All" clicked) */}
      {showAllCourses && (
        <div className="flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-bold text-foreground">
              All Courses ({filteredCourses.length})
            </h3>
            <Button
              variant="ghost"
              size="xs"
              onClick={() => {
                setShowAllCourses(false);
                setCourseCategoryFilter("All");
                setCourseSearchQuery("");
              }}
            >
              ← Back to Explore
            </Button>
          </div>
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
      )}
    </div>
  );
}
