"use client";

import { useMemo, useCallback } from "react";
import { ArrowLeft, Clock, BookOpen, CheckCircle, Circle, ChevronRight } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ProgressBar } from "@/components/ui/Progress";
import { CourseCard } from "@/components/lms/CourseCard";
import type { CareerPath, LMSCourse } from "@/types/lms.types";
import { PATH_BADGES, CATEGORY_GRADIENTS, DEFAULT_GRADIENT } from "@/types/lms.types";

/* ═══════════════════════════════════════════════════════
   CareerPathDetail — Dedicated roadmap page shown when
   a user clicks a career path card. Shows learning order,
   estimated completion, skill progress, and all courses.
   ═══════════════════════════════════════════════════════ */

interface CareerPathDetailProps {
  path: CareerPath;
  courses: any[];
  enrollments: any[];
  onBack: () => void;
  onStartCourse: (course: any) => Promise<void>;
  onResumeCourse: (course: any) => void;
}

export default function CareerPathDetail({
  path,
  courses,
  enrollments,
  onBack,
  onStartCourse,
  onResumeCourse,
}: CareerPathDetailProps) {
  const badgeConfig = path.badge ? PATH_BADGES[path.badge] : null;

  /* Match courses to this career path by skills overlap */
  const pathCourses = useMemo(() => {
    const pathSkillsLower = path.skills.map((s) => s.toLowerCase());
    return courses.filter((c: any) => {
      const courseSkills = (c.skills || []).map((s: string) => s.toLowerCase());
      const courseCategory = (c.category || "").toLowerCase();
      const courseTag = (c.tag || "").toLowerCase();
      return (
        pathSkillsLower.some(
          (ps) =>
            courseSkills.some((cs: string) => cs.includes(ps) || ps.includes(cs)) ||
            courseCategory.includes(ps) ||
            courseTag.includes(ps)
        )
      );
    });
  }, [courses, path.skills]);

  /* If no skill-matched courses, show all courses as fallback */
  const displayCourses = pathCourses.length > 0 ? pathCourses : courses;

  const getEnrollment = useCallback(
    (courseId: string | number) => enrollments.find((e: any) => e.course_id === courseId),
    [enrollments]
  );

  /* Calculate overall path progress */
  const pathProgress = useMemo(() => {
    if (displayCourses.length === 0) return 0;
    const enrolled = displayCourses.filter((c: any) =>
      enrollments.some((e: any) => e.course_id === c.id)
    );
    if (enrolled.length === 0) return 0;
    const totalProgress = enrolled.reduce((sum: number, c: any) => {
      const e = enrollments.find((en: any) => en.course_id === c.id);
      return sum + (e?.progress || 0);
    }, 0);
    return Math.round(totalProgress / displayCourses.length);
  }, [displayCourses, enrollments]);

  /* Step completion status */
  const stepStatus = useMemo(() => {
    return path.steps.map((step, index) => {
      // Mark steps as complete based on path progress percentage
      const stepPercentage = ((index + 1) / path.steps.length) * 100;
      if (pathProgress >= stepPercentage) return "complete";
      if (pathProgress > 0 && index === Math.floor((pathProgress / 100) * path.steps.length))
        return "current";
      return "upcoming";
    });
  }, [path.steps, pathProgress]);

  const completedSteps = stepStatus.filter((s) => s === "complete").length;
  const estimatedHoursLeft = Math.round(path.totalHours * ((100 - pathProgress) / 100));

  return (
    <div className="flex flex-col gap-6 w-full">
      {/* Back button */}
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer w-fit"
        aria-label="Back to explore"
      >
        <ArrowLeft size={16} />
        Back to Explore
      </button>

      {/* Hero header */}
      <div className={`relative bg-gradient-to-br ${path.gradient} rounded-2xl overflow-hidden`}>
        <div className="absolute inset-0 bg-gradient-to-b from-black/0 via-black/5 to-black/25 pointer-events-none" />
        <div className="relative p-6 sm:p-8 flex flex-col gap-4">
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <span className="text-4xl" role="img" aria-hidden="true">
                {path.icon}
              </span>
              <div>
                <h2 className="text-xl sm:text-2xl font-bold text-white">{path.title}</h2>
                <p className="text-sm text-white/70 mt-0.5">{path.subtitle}</p>
              </div>
            </div>
            {badgeConfig && (
              <span className="text-xs font-bold bg-white/25 backdrop-blur-sm text-white px-3 py-1.5 rounded-lg">
                {badgeConfig.label}
              </span>
            )}
          </div>

          {/* Stats */}
          <div className="flex flex-wrap items-center gap-4 text-white/80 text-sm">
            <span className="flex items-center gap-1.5">
              <BookOpen size={14} />
              {path.courseCount} courses
            </span>
            <span className="flex items-center gap-1.5">
              <Clock size={14} />
              {path.totalHours} hours total
            </span>
            {pathProgress > 0 && (
              <span className="flex items-center gap-1.5">
                <CheckCircle size={14} />
                {pathProgress}% complete · ~{estimatedHoursLeft}h remaining
              </span>
            )}
          </div>

          {/* Skills */}
          <div className="flex flex-wrap gap-2">
            {path.skills.map((skill) => (
              <span key={skill} className="bg-white/15 text-white text-xs font-medium px-2.5 py-1 rounded-lg">
                {skill}
              </span>
            ))}
          </div>

          {/* Overall progress bar */}
          {pathProgress > 0 && (
            <div className="mt-1">
              <div className="h-2 w-full bg-white/20 rounded-full overflow-hidden">
                <div
                  className="h-full bg-white rounded-full transition-all duration-500"
                  style={{ width: `${pathProgress}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Learning Roadmap steps */}
      <div>
        <h3 className="text-base font-bold text-foreground mb-3">Learning Roadmap</h3>
        <div className="flex flex-col gap-0">
          {path.steps.map((step, index) => {
            const status = stepStatus[index];
            return (
              <div key={step} className="flex items-stretch gap-3">
                {/* Vertical connector line + status icon */}
                <div className="flex flex-col items-center w-6 shrink-0">
                  {status === "complete" ? (
                    <CheckCircle size={20} className="text-emerald-500 shrink-0" />
                  ) : status === "current" ? (
                    <div className="w-5 h-5 rounded-full border-[3px] border-primary bg-background shrink-0" />
                  ) : (
                    <Circle size={20} className="text-muted-foreground/40 shrink-0" />
                  )}
                  {index < path.steps.length - 1 && (
                    <div
                      className={`w-0.5 flex-1 min-h-[24px] ${
                        status === "complete" ? "bg-emerald-500/40" : "bg-border"
                      }`}
                    />
                  )}
                </div>

                {/* Step content */}
                <div className="pb-4 flex-1">
                  <span
                    className={`text-sm font-semibold ${
                      status === "complete"
                        ? "text-emerald-600 dark:text-emerald-400"
                        : status === "current"
                        ? "text-foreground"
                        : "text-muted-foreground"
                    }`}
                  >
                    {step}
                  </span>
                  {status === "current" && (
                    <span className="ml-2 text-xs text-primary font-medium">← You are here</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Courses grid */}
      <div>
        <h3 className="text-base font-bold text-foreground mb-1">
          Courses in this path
          <span className="text-muted-foreground font-normal text-sm ml-2">
            ({displayCourses.length})
          </span>
        </h3>
        <p className="text-xs text-muted-foreground mb-4">
          Complete these courses in order for the best learning experience
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {displayCourses.map((course: any) => (
            <CourseCard
              key={course.id}
              course={course}
              enrollment={getEnrollment(course.id)}
              onEnroll={async (id) => {
                const c = courses.find((co: any) => co.id === id);
                if (c) await onStartCourse(c);
              }}
              onResume={onResumeCourse}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
