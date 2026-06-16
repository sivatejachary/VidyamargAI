"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { apiService } from "@/services/api";
import type { LMSCourse, LMSEnrollment } from "@/types/lms.types";

/* ═══════════════════════════════════════════════════════
   useLMSExploreData — Data hook for the LMS Explore page.
   Fetches courses, enrollments, and derives all
   section data (trending, top rated, etc.) client-side.
   ═══════════════════════════════════════════════════════ */

interface LMSExploreData {
  /* Raw data */
  courses: LMSCourse[];
  enrollments: LMSEnrollment[];

  /* Derived sections */
  continueLearning: { course: LMSCourse; enrollment: LMSEnrollment }[];
  recommended: LMSCourse[];
  trending: LMSCourse[];
  topRated: LMSCourse[];
  newReleases: LMSCourse[];

  /* State */
  isLoading: boolean;
  error: string | null;

  /* Enrolled course IDs for quick lookup */
  enrolledCourseIds: Set<string | number>;

  /* Actions */
  enrollInCourse: (courseId: string | number) => Promise<void>;
  refetch: () => Promise<void>;
}

/** Session storage cache helpers for instant loads */
function getCached<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function setCache(key: string, value: unknown): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch { /* quota exceeded — silently ignore */ }
}

export function useLMSExploreData(): LMSExploreData {
  const [courses, setCourses] = useState<LMSCourse[]>(() =>
    getCached("lms_courses", [])
  );
  const [enrollments, setEnrollments] = useState<LMSEnrollment[]>(() =>
    getCached("lms_enrollments", [])
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* ─── Fetch all data in parallel ─── */
  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const token =
        typeof window !== "undefined" ? localStorage.getItem("token") : null;

      const [coursesRes, enrollmentsRes] = await Promise.allSettled([
        apiService.getCourses(),
        token ? apiService.getEnrollments() : Promise.resolve([]),
      ]);

      if (coursesRes.status === "fulfilled" && coursesRes.value) {
        setCourses(coursesRes.value);
        setCache("lms_courses", coursesRes.value);
      }

      if (enrollmentsRes.status === "fulfilled" && enrollmentsRes.value) {
        setEnrollments(enrollmentsRes.value);
        setCache("lms_enrollments", enrollmentsRes.value);
      }

      if (
        coursesRes.status === "rejected" &&
        enrollmentsRes.status === "rejected"
      ) {
        setError("Failed to load course data. Please try again.");
      }
    } catch (err) {
      setError("Failed to load course data. Please try again.");
      console.error("LMS explore data fetch error:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /* ─── Enrolled course IDs set ─── */
  const enrolledCourseIds = useMemo(
    () => new Set(enrollments.map((e) => e.course_id)),
    [enrollments]
  );

  /* ─── Continue Learning: enrolled with 0 < progress < 100 ─── */
  const continueLearning = useMemo(() => {
    return enrollments
      .filter((e) => e.progress > 0 && e.progress < 100)
      .sort((a, b) => {
        // Sort by last_accessed DESC if available
        if (a.last_accessed && b.last_accessed) {
          return new Date(b.last_accessed).getTime() - new Date(a.last_accessed).getTime();
        }
        return b.progress - a.progress;
      })
      .slice(0, 8)
      .map((enrollment) => {
        const course =
          courses.find((c) => c.id === enrollment.course_id) ||
          (enrollment.course as LMSCourse) ||
          ({
            id: enrollment.course_id,
            title: "Course",
          } as LMSCourse);
        return { course, enrollment };
      });
  }, [courses, enrollments]);

  /* ─── Recommended: courses not yet enrolled, sorted by rating ─── */
  const recommended = useMemo(() => {
    return courses
      .filter((c) => !enrolledCourseIds.has(c.id))
      .sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0))
      .slice(0, 10);
  }, [courses, enrolledCourseIds]);

  /* ─── Trending: sorted by enrollment_count DESC ─── */
  const trending = useMemo(() => {
    return [...courses]
      .sort((a, b) => (b.enrollment_count ?? 0) - (a.enrollment_count ?? 0))
      .slice(0, 8);
  }, [courses]);

  /* ─── Top Rated: rating DESC, minimum threshold ─── */
  const topRated = useMemo(() => {
    return [...courses]
      .filter((c) => (c.rating ?? 0) >= 4.0)
      .sort((a, b) => (b.rating ?? 0) - (a.rating ?? 0))
      .slice(0, 8);
  }, [courses]);

  /* ─── New Releases: published in last 60 days ─── */
  const newReleases = useMemo(() => {
    const sixtyDaysAgo = Date.now() - 60 * 24 * 60 * 60 * 1000;
    return courses
      .filter((c) => {
        if (!c.published_at) return false;
        return new Date(c.published_at).getTime() > sixtyDaysAgo;
      })
      .sort(
        (a, b) =>
          new Date(b.published_at!).getTime() -
          new Date(a.published_at!).getTime()
      )
      .slice(0, 6);
  }, [courses]);

  /* ─── Enroll action ─── */
  const enrollInCourse = useCallback(
    async (courseId: string | number) => {
      try {
        await apiService.enrollCourse(courseId);
        // Refresh enrollments after enrollment
        const updated = await apiService.getEnrollments();
        if (updated) {
          setEnrollments(updated);
          setCache("lms_enrollments", updated);
        }
      } catch (err) {
        console.error("Failed to enroll:", err);
      }
    },
    []
  );

  return {
    courses,
    enrollments,
    continueLearning,
    recommended,
    trending,
    topRated,
    newReleases,
    isLoading,
    error,
    enrolledCourseIds,
    enrollInCourse,
    refetch: fetchData,
  };
}
