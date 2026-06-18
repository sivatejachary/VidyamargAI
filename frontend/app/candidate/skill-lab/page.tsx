"use client";

import { useState, useEffect, useMemo } from "react";
import { apiService } from "@/services/api";
import { useAuthStore } from "@/store/authStore";
import { useQuery, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { 
  GraduationCap
} from "lucide-react";

import ExploreCourses from "./components/ExploreCourses";
import CoursePlayer from "./components/CoursePlayer";
import MyLearning from "./components/MyLearning";
import Certificates from "./components/Certificates";
import AiMentor from "./components/AiMentor";


function transformNewCurriculumToOld(newCur: any) {
  if (!newCur || !newCur.modules || !Array.isArray(newCur.modules)) return newCur;
  
  const sections: any[] = [];
  const completedLessonIds: string[] = [];
  
  newCur.modules.forEach((mod: any) => {
    const sectionLessons: any[] = [];
    
    // Process topics list under each module
    if (mod.topics && Array.isArray(mod.topics)) {
      mod.topics.forEach((topic: any) => {
        // 1. Video
        if (topic.video) {
          const vidId = topic.video.id;
          sectionLessons.push({
            id: vidId,
            title: topic.video.title,
            type: "video",
            duration: topic.video.duration || "15 min",
            is_locked: !mod.unlocked, // will compute sequentially later
            video_url: topic.video.youtubeUrl,
          });
          if (topic.video.completed) {
            completedLessonIds.push(vidId);
          }
        }
        
        // 2. PDF
        if (topic.pdf) {
          const pdfId = topic.pdf.id;
          sectionLessons.push({
            id: pdfId,
            title: topic.pdf.title,
            type: "pdf",
            duration: "5 pages",
            is_locked: !mod.unlocked, // will compute sequentially later
            pdf_url: topic.pdf.pdfUrl,
          });
          if (topic.pdf.completed) {
            completedLessonIds.push(pdfId);
          }
        }
      });
    }
    
    // 3. Quiz
    if (mod.quiz) {
      const quizId = mod.quiz.id;
      sectionLessons.push({
        id: quizId,
        title: mod.quiz.title,
        type: "quiz",
        duration: "5 questions",
        is_locked: mod.quiz.locked, // will compute sequentially later
        quiz: {
          id: quizId,
          title: mod.quiz.title,
          questions: (mod.quiz.questions || []).map((q: any, idx: number) => ({
            id: q.id || idx.toString(),
            question: q.question,
            options: q.options,
            correct_option: q.correct_option
          }))
        }
      });
      if (mod.quiz.completed) {
        completedLessonIds.push(quizId);
      }
    }
    
    // 4. Written Assessment
    if (mod.writtenAssessment) {
      const writtenId = mod.writtenAssessment.id;
      sectionLessons.push({
        id: writtenId,
        title: mod.writtenAssessment.title,
        type: "written_assessment",
        duration: "3 questions",
        is_locked: mod.writtenAssessment.locked, // will compute sequentially later
        written_assessment: {
          id: writtenId,
          title: mod.writtenAssessment.title,
          questions: mod.writtenAssessment.questions || [],
          best_score: mod.writtenAssessment.bestScore,
          passed: mod.writtenAssessment.passed,
          feedback: mod.writtenAssessment.feedback
        }
      });
      if (mod.writtenAssessment.completed) {
        completedLessonIds.push(writtenId);
      }
    }
    
    // 5. AI Interview
    if (mod.aiInterview) {
      const interviewId = mod.aiInterview.id;
      sectionLessons.push({
        id: interviewId,
        title: mod.aiInterview.title,
        type: "ai_interview",
        duration: "10 min",
        is_locked: mod.aiInterview.locked, // will compute sequentially later
        module_interview: {
          id: interviewId,
          title: mod.aiInterview.title,
          questions: mod.aiInterview.questions || [],
          best_score: mod.aiInterview.bestScore,
          passed: mod.aiInterview.passed,
          feedback: mod.aiInterview.feedback
        }
      });
      if (mod.aiInterview.completed) {
        completedLessonIds.push(interviewId);
      }
    }
    
    // Perform sequential linear lock computation for the lessons in this section
    let prevCompleted = true; // The first item is unlocked if the module itself is unlocked
    sectionLessons.forEach((les: any) => {
      les.is_locked = !mod.unlocked || !prevCompleted;
      prevCompleted = completedLessonIds.includes(les.id);
    });
    
    sections.push({
      id: mod.moduleId,
      title: `Module ${mod.moduleNo}: ${mod.moduleName}`,
      lessons: sectionLessons
    });
  });
  
  return {
    courseId: newCur.courseId,
    courseName: newCur.courseName,
    description: newCur.description,
    enrolled: newCur.enrolled,
    progress: newCur.progress,
    sections: sections,
    completed_lesson_ids: completedLessonIds
  };
}

export default function SkillLab() {
  // Session storage caching helpers for instant (0ms) loads
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

  const [activeView, setActiveView] = useState<"explore" | "course-details" | "course-player" | "my-learning" | "certificates" | "ai-mentor">("explore");
  const [selectedCourse, setSelectedCourse] = useState<any | null>(null);
  const [activeMediaTab, setActiveMediaTab] = useState<"video" | "pdf">("video");
  
  // Shared Catalog filtering states
  const [courseSearchQuery, setCourseSearchQuery] = useState("");
  const [courseCategoryFilter, setCourseCategoryFilter] = useState("All");
  const [showAllCourses, setShowAllCourses] = useState(false);

  // Auth Store details
  const [profile, setProfile] = useState<any>(null);
  const { email, fullName } = useAuthStore();

  // React Query cached fetches
  const queryClient = useQueryClient();

  const { data: courses = [] } = useQuery({
    queryKey: ["courses"],
    queryFn: () => apiService.getCourses(),
    placeholderData: keepPreviousData,
  });

  const { data: enrollments = [] } = useQuery({
    queryKey: ["enrollments", email],
    queryFn: () => apiService.getEnrollments(),
    enabled: !!email,
    placeholderData: keepPreviousData,
  });

  const { data: certificates = [] } = useQuery({
    queryKey: ["certificates", email],
    queryFn: () => apiService.getCertificates(),
    enabled: !!email,
    placeholderData: keepPreviousData,
  });

  const { data: rawCurriculum = null, isLoading: loadingCurriculum } = useQuery({
    queryKey: ["curriculum", selectedCourse?.id],
    queryFn: () => {
      if (!selectedCourse?.id) return null;
      return apiService.getCourseCurriculum(selectedCourse.id);
    },
    enabled: !!selectedCourse?.id,
    placeholderData: keepPreviousData,
  });

  const curriculum = useMemo(() => {
    return transformNewCurriculumToOld(rawCurriculum);
  }, [rawCurriculum]);

  const enrolledCourseIds = useMemo(() => {
    if (!Array.isArray(enrollments)) return [];
    return enrollments.map((e: any) => e.course_id);
  }, [enrollments]);

  // Background active enrollment tracking for Continue LearningStepper
  const activeEnrollmentCourse = useMemo(() => {
    if (Array.isArray(enrollments) && enrollments.length > 0) {
      const activeEnroll = enrollments[0];
      const coursesArray = Array.isArray(courses) ? courses : [];
      return coursesArray.find((c: any) => c.id === activeEnroll.course_id) || activeEnroll.course;
    }
    return null;
  }, [enrollments, courses]);

  const { data: rawActiveEnrollmentCurriculum = null } = useQuery({
    queryKey: ["curriculum", activeEnrollmentCourse?.id],
    queryFn: () => {
      if (!activeEnrollmentCourse?.id) return null;
      return apiService.getCourseCurriculum(activeEnrollmentCourse.id);
    },
    enabled: !!activeEnrollmentCourse?.id,
    placeholderData: keepPreviousData,
  });

  const activeEnrollmentCurriculum = useMemo(() => {
    return transformNewCurriculumToOld(rawActiveEnrollmentCurriculum);
  }, [rawActiveEnrollmentCurriculum]);

  // Local state for current selections
  const [currentLesson, setCurrentLesson] = useState<any>(null);
  const [completedLessonIds, setCompletedLessonIds] = useState<number[]>([]);
  const [autoSelectLessonId, setAutoSelectLessonId] = useState<string | number | null>(null);
  const [autoSelectType, setAutoSelectType] = useState<string | null>(null);

  // Sync current lesson selection when curriculum changes
  useEffect(() => {
    if (!curriculum) return;
    setCompletedLessonIds(curriculum.completed_lesson_ids || []);
    
    const flatLessons: any[] = [];
    curriculum.sections?.forEach((sec: any) => {
      sec.lessons?.forEach((les: any) => {
        flatLessons.push(les);
      });
    });

    if (flatLessons.length > 0) {
      if (autoSelectLessonId) {
        const match = flatLessons.find(l => l.id === autoSelectLessonId);
        if (match) {
          setCurrentLesson(match);
          setActiveMediaTab(match.type === "pdf" ? "pdf" : "video");
        }
        setAutoSelectLessonId(null);
      } else if (autoSelectType) {
        const match = flatLessons.find(l => l.type === autoSelectType && !l.is_locked) ||
                      flatLessons.find(l => l.type === autoSelectType);
        if (match) {
          setCurrentLesson(match);
          setActiveMediaTab(match.type === "pdf" ? "pdf" : "video");
        } else {
          setCurrentLesson(flatLessons[0]);
          setActiveMediaTab(flatLessons[0].type === "pdf" ? "pdf" : "video");
        }
        setAutoSelectType(null);
      } else {
        const currentLessonIsFromThisCourse = flatLessons.some(l => l.id === currentLesson?.id);
        if (!currentLesson || !currentLessonIsFromThisCourse) {
          const incomplete = flatLessons.find(l => !(curriculum.completed_lesson_ids || []).includes(l.id));
          const selected = incomplete || flatLessons[0];
          setCurrentLesson(selected);
          setActiveMediaTab(selected.type === "pdf" ? "pdf" : "video");
        }
      }
    } else {
      setCurrentLesson(null);
    }
  }, [curriculum, autoSelectLessonId, autoSelectType]);

  // Gamification & Streak States
  const [xp, setXp] = useState<number>(() => getCachedValue("skill_lab_xp", 80));
  const [level, setLevel] = useState<number>(() => getCachedValue("skill_lab_level", 12));
  const [streak, setStreak] = useState<number>(() => getCachedValue("skill_lab_streak", 25));
  const [hoursLearned, setHoursLearned] = useState<number>(() => getCachedValue("skill_lab_hoursLearned", 0));
  const [completedCoursesCount, setCompletedCoursesCount] = useState<number>(() => getCachedValue("skill_lab_completedCoursesCount", 0));
  const [earnedCertsCount, setEarnedCertsCount] = useState<number>(() => getCachedValue("skill_lab_earnedCertsCount", 0));
  const [readinessScore, setReadinessScore] = useState<number>(() => getCachedValue("skill_lab_readinessScore", 64));

  // Notepad States
  const [notepadText, setNotepadText] = useState("");
  const [savedNotes, setSavedNotes] = useState<string[]>([]);

  const fetchCurriculum = async (courseId: string | number, autoSelectLesId?: string | number) => {
    if (autoSelectLesId) {
      setAutoSelectLessonId(autoSelectLesId);
    }
    queryClient.invalidateQueries({ queryKey: ["curriculum", courseId] });
  };

  const loadEnrollments = async () => {
    queryClient.invalidateQueries({ queryKey: ["enrollments", email] });
  };

  const loadCertificates = async () => {
    queryClient.invalidateQueries({ queryKey: ["certificates", email] });
  };

  const loadData = async () => {
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    if (token) {
      apiService.getProfile()
        .then((prof) => {
          setProfile(prof);
          setCachedValue("skill_lab_profile", prof);
        })
        .catch((err) => console.error("Failed to load profile", err));

      apiService.getCareerReadiness()
        .then((cr) => {
          if (cr) {
            setStreak(cr.learning_streak);
            setCachedValue("skill_lab_streak", cr.learning_streak);
            setHoursLearned(cr.hours_learned);
            setCachedValue("skill_lab_hoursLearned", cr.hours_learned);
            setCompletedCoursesCount(cr.courses_completed);
            setCachedValue("skill_lab_completedCoursesCount", cr.courses_completed);
            setEarnedCertsCount(cr.certificates_earned);
            setCachedValue("skill_lab_earnedCertsCount", cr.certificates_earned);
            setReadinessScore(Math.round(cr.career_readiness_score));
            setCachedValue("skill_lab_readinessScore", Math.round(cr.career_readiness_score));
            if (cr.xp !== undefined) {
              setXp(cr.xp);
              setCachedValue("skill_lab_xp", cr.xp);
            }
            if (cr.level !== undefined) {
              setLevel(cr.level);
              setCachedValue("skill_lab_level", cr.level);
            }
          }
        })
        .catch((err) => console.error("Failed to load career readiness", err));
    }
  };

  useEffect(() => {
    loadData();
  }, [email]);

  const handleEnrollCourse = async (id: string | number) => {
    try {
      await apiService.enrollCourse(id);
      setXp(prev => prev + 50);
      queryClient.invalidateQueries({ queryKey: ["enrollments", email] });
    } catch (err) {
      console.error("Failed to enroll in course:", err);
    }
  };

  const handleStartCourse = async (course: any) => {
    setSelectedCourse(course);
    await handleEnrollCourse(course.id);
    setActiveView("course-player");
  };

  const handleGoToLesson = async (course: any, lessonType: string) => {
    setSelectedCourse(course);
    setAutoSelectType(lessonType);
    setActiveView("course-player");
    await handleEnrollCourse(course.id);
  };

  const isAiMentor = activeView === "ai-mentor";

  return (
    <div className={`w-full bg-background text-foreground p-4 sm:p-6 font-sans transition-colors duration-300 relative overflow-hidden flex flex-col ${
      isAiMentor ? "h-screen pb-4 gap-4" : "min-h-screen gap-5"
    }`}>

      {/* Header */}
      <div className="relative z-10 w-full flex items-center gap-3 shrink-0">
        <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shrink-0">
          <GraduationCap size={22} />
        </div>
        <div>
          <h1 className="text-xl font-bold text-foreground">Skill Lab</h1>
          <p className="text-xs text-muted-foreground font-medium">Learn · Test · AI Interview · Get Certified</p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="relative z-10 flex items-center gap-6 border-b border-border w-full shrink-0 overflow-x-auto scrollbar-hide">
        {[
          { id: "explore", label: "Explore Courses" },
          { id: "my-learning", label: "My Learning" },
          { id: "certificates", label: "Certificates" },
          { id: "ai-mentor", label: "AI Mentor" }
        ].map((tab) => {
          const active = (activeView as string) === tab.id || 
            (tab.id === "explore" && (activeView as string) === "course-details") ||
            (tab.id === "my-learning" && (activeView as string) === "course-player");

          return (
            <button
              key={tab.id}
              onClick={() => {
                setActiveView(tab.id as any);
                if (tab.id === "explore") {
                  setSelectedCourse(null);
                  setShowAllCourses(false);
                }
              }}
              className={`text-xs font-bold pb-2.5 border-b-2 transition-all cursor-pointer whitespace-nowrap ${
                active 
                  ? "border-primary text-primary" 
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
              aria-label={tab.label}
              aria-selected={active}
              role="tab"
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      <div className={`relative z-10 flex flex-col w-full ${isAiMentor ? "flex-1 min-h-0 gap-4" : "gap-5"}`}>

        {/* Tab View components rendering */}
        {(activeView === "explore" || activeView === "course-details") && (
          <ExploreCourses
            courses={courses}
            enrollments={enrollments}
            enrolledCourseIds={enrolledCourseIds}
            readinessScore={readinessScore}
            activeView={activeView}
            setActiveView={setActiveView}
            selectedCourse={selectedCourse}
            setSelectedCourse={setSelectedCourse}
            activeEnrollmentCourse={activeEnrollmentCourse}
            activeEnrollmentCurriculum={activeEnrollmentCurriculum}
            handleStartCourse={handleStartCourse}
            handleGoToLesson={handleGoToLesson}
            completedLessonIds={completedLessonIds}
            courseSearchQuery={courseSearchQuery}
            setCourseSearchQuery={setCourseSearchQuery}
            courseCategoryFilter={courseCategoryFilter}
            setCourseCategoryFilter={setCourseCategoryFilter}
            showAllCourses={showAllCourses}
            setShowAllCourses={setShowAllCourses}
          />
        )}

        {activeView === "course-player" && selectedCourse && (
          <CoursePlayer
            selectedCourse={selectedCourse}
            activeView={activeView}
            setActiveView={setActiveView}
            curriculum={curriculum}
            currentLesson={currentLesson}
            setCurrentLesson={setCurrentLesson}
            completedLessonIds={completedLessonIds}
            setCompletedLessonIds={setCompletedLessonIds}
            loadingCurriculum={loadingCurriculum}
            fetchCurriculum={fetchCurriculum}
            loadEnrollments={loadEnrollments}
            loadData={loadData}
            activeMediaTab={activeMediaTab}
            setActiveMediaTab={setActiveMediaTab}
            notepadText={notepadText}
            setNotepadText={setNotepadText}
            savedNotes={savedNotes}
            setSavedNotes={setSavedNotes}
          />
        )}

        {activeView === "my-learning" && (
          <MyLearning
            enrollments={enrollments}
            courses={courses}
            handleStartCourse={handleStartCourse}
            setActiveView={setActiveView}
          />
        )}

        {activeView === "certificates" && (
          <Certificates certificates={certificates} />
        )}

        {activeView === "ai-mentor" && (
          <AiMentor
            email={email}
            fullName={fullName}
            profile={profile}
            loadData={loadData}
            setXp={setXp}
            enrollments={enrollments}
            courses={courses}
          />
        )}

      </div>
    </div>
  );
}
