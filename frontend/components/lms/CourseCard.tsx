"use client";

import * as React from "react";
import { Star, Clock, BookOpen, Brain, Play } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ProgressBar } from "@/components/ui/Progress";
import {
  LMSCourse,
  LMSEnrollment,
  CATEGORY_GRADIENTS,
  DEFAULT_GRADIENT,
} from "@/types/lms.types";

/* ─── Props ──────────────────────────────────────────────── */

export interface CourseCardProps {
  course: LMSCourse;
  enrollment?: LMSEnrollment;
  onEnroll?: (courseId: string | number) => void;
  onResume?: (course: LMSCourse) => void;
  showTrending?: boolean;
  showNew?: boolean;
}

/* ─── Component ──────────────────────────────────────────── */

export function CourseCard({
  course,
  enrollment,
  onEnroll,
  onResume,
  showTrending = false,
  showNew = false,
}: CourseCardProps) {
  const isEnrolled = !!enrollment;
  const gradient =
    CATEGORY_GRADIENTS[course.category ?? ""] ?? DEFAULT_GRADIENT;
  const moduleCount = course.totalModules ?? course.modules ?? 0;

  return (
    <Card
      className={
        "w-full h-full !rounded-2xl !p-0 overflow-hidden flex flex-col " +
        "transition-transform transition-shadow duration-200 " +
        "hover:-translate-y-1 hover:shadow-lg " +
        "motion-reduce:transition-none motion-reduce:hover:transform-none"
      }
      hoverEffect={false}
    >
      {/* ── 1. Thumbnail ──────────────────────────────────── */}
      <div className="relative h-[120px] w-full shrink-0 overflow-hidden">
        {course.thumbnailUrl ? (
          <img
            src={course.thumbnailUrl}
            alt={course.title}
            loading="lazy"
            className="h-full w-full object-cover"
          />
        ) : (
          <div
            className={`h-full w-full bg-gradient-to-br ${gradient} flex items-center justify-center`}
          >
            <Brain size={32} className="text-white/40" aria-hidden="true" />
          </div>
        )}

        {/* Category badge — top-left */}
        {course.category && (
          <div className="absolute top-2 left-2">
            <Badge variant="secondary" className="backdrop-blur-sm bg-card/70">
              {course.category}
            </Badge>
          </div>
        )}

        {/* Trending / New badge — top-right */}
        {showTrending && (
          <div className="absolute top-2 right-2">
            <Badge variant="secondary" className="backdrop-blur-sm bg-card/70">
              🔥 Trending
            </Badge>
          </div>
        )}
        {!showTrending && showNew && (
          <div className="absolute top-2 right-2">
            <Badge variant="primary">New</Badge>
          </div>
        )}
      </div>

      {/* ── 2. Content Area ───────────────────────────────── */}
      <div className="flex flex-1 flex-col gap-2 p-3.5">
        {/* Title */}
        <h3 className="text-sm font-semibold text-foreground line-clamp-2 leading-snug">
          {course.title}
        </h3>

        {/* Instructor */}
        {course.instructor && (
          <p className="text-xs text-muted-foreground truncate">
            {course.instructor}
          </p>
        )}

        {/* Star rating */}
        {course.rating != null && (
          <div className="flex items-center gap-1">
            <Star
              size={13}
              className="fill-yellow-400 text-yellow-400 shrink-0"
              aria-hidden="true"
            />
            <span className="text-xs font-medium text-foreground">
              {course.rating.toFixed(1)}
            </span>
            {course.enrollment_count != null && (
              <span className="text-xs text-muted-foreground">
                ({course.enrollment_count.toLocaleString()})
              </span>
            )}
          </div>
        )}

        {/* Meta row: duration · modules */}
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {course.duration && (
            <span className="inline-flex items-center gap-1">
              <Clock size={12} aria-hidden="true" />
              {course.duration}
            </span>
          )}
          {moduleCount > 0 && (
            <span className="inline-flex items-center gap-1">
              <BookOpen size={12} aria-hidden="true" />
              {moduleCount} modules
            </span>
          )}
        </div>

        {/* Spacer pushes CTA to bottom */}
        <div className="mt-auto flex flex-col gap-2 pt-1">
          {/* Progress bar (enrolled only) */}
          {isEnrolled && (
            <div className="flex flex-col gap-1">
              <ProgressBar
                value={enrollment.progress}
                label={`${course.title} progress`}
                className="h-1.5"
              />
              <span className="text-[10px] font-medium text-muted-foreground">
                {enrollment.progress}% complete
              </span>
            </div>
          )}

          {/* CTA Button */}
          {isEnrolled ? (
            <Button
              variant="outline"
              size="xs"
              className="w-full"
              onClick={() => onResume?.(course)}
              aria-label={`Resume ${course.title}`}
            >
              <Play size={13} aria-hidden="true" />
              Resume
            </Button>
          ) : (
            <Button
              variant="primary"
              size="xs"
              className="w-full"
              onClick={() => onEnroll?.(course.id)}
              aria-label={`Enroll in ${course.title}`}
            >
              Enroll
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}

CourseCard.displayName = "CourseCard";
