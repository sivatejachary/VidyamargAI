"use client";

import { useState, useEffect } from "react";
import { apiService } from "@/services/api";
import { useAuthStore } from "@/store/authStore";
import { 
  GraduationCap
} from "lucide-react";

import ExploreCourses from "./components/ExploreCourses";
import CoursePlayer from "./components/CoursePlayer";
import MyLearning from "./components/MyLearning";
import Certificates from "./components/Certificates";
import AiMentor from "./components/AiMentor";

function transformNewCurriculumToOld(newCur: any) {
  if (!newCur || !newCur.modules) return newCur;
  
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
  const [courses, setCourses] = useState<any[]>(() => getCachedValue("skill_lab_courses", []));
  const [selectedCourse, setSelectedCourse] = useState<any | null>(null);
  const [activeMediaTab, setActiveMediaTab] = useState<"video" | "pdf">("video");
  
  // Shared Catalog filtering states
  const [courseSearchQuery, setCourseSearchQuery] = useState("");
  const [courseCategoryFilter, setCourseCategoryFilter] = useState("All");
  const [showAllCourses, setShowAllCourses] = useState(false);

  // Dynamic LMS Curriculum States
  const [curriculum, setCurriculum] = useState<any>(() => getCachedValue("skill_lab_curriculum", null));
  const [loadingCurriculum, setLoadingCurriculum] = useState(false);
  const [currentLesson, setCurrentLesson] = useState<any>(null);
  const [completedLessonIds, setCompletedLessonIds] = useState<number[]>([]);
  const [enrollments, setEnrollments] = useState<any[]>(() => getCachedValue("skill_lab_enrollments", []));
  const [certificates, setCertificates] = useState<any[]>(() => getCachedValue("skill_lab_certificates", []));
  const [enrolledCourseIds, setEnrolledCourseIds] = useState<any[]>(() => getCachedValue("skill_lab_enrolledCourseIds", []));

  // Background active enrollment tracking for Continue LearningStepper
  const [activeEnrollmentCurriculum, setActiveEnrollmentCurriculum] = useState<any>(() => getCachedValue("skill_lab_activeEnrollmentCurriculum", null));
  const [activeEnrollmentCourse, setActiveEnrollmentCourse] = useState<any>(() => getCachedValue("skill_lab_activeEnrollmentCourse", null));

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

  // Auth Store details
  const [profile, setProfile] = useState<any>(null);
  const { email, fullName } = useAuthStore();

  const fetchCurriculum = async (courseId: string | number, autoSelectLessonId?: string | number) => {
    setLoadingCurriculum(true);
    try {
      const rawData = await apiService.getCourseCurriculum(courseId);
      const data = transformNewCurriculumToOld(rawData);
      setCurriculum(data);
      setCachedValue("skill_lab_curriculum", data);
      setCompletedLessonIds(data.completed_lesson_ids || []);
      
      const flatLessons: any[] = [];
      data.sections?.forEach((sec: any) => {
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
        } else {
          const incomplete = flatLessons.find(l => !(data.completed_lesson_ids || []).includes(l.id));
          const selected = incomplete || flatLessons[0];
          setCurrentLesson(selected);
          setActiveMediaTab(selected.type === "pdf" ? "pdf" : "video");
        }
      } else {
        setCurrentLesson(null);
      }
    } catch (err) {
      console.error("Failed to fetch curriculum:", err);
    } finally {
      setLoadingCurriculum(false);
    }
  };

  const loadEnrollments = async () => {
    try {
      const data = await apiService.getEnrollments();
      setEnrollments(data || []);
      setCachedValue("skill_lab_enrollments", data || []);
      if (data) {
        const ids = data.map((e: any) => e.course_id);
        setEnrolledCourseIds(ids);
        setCachedValue("skill_lab_enrolledCourseIds", ids);
      }
    } catch (err) {
      console.error("Failed to load enrollments", err);
    }
  };

  const loadCertificates = async () => {
    try {
      const data = await apiService.getCertificates();
      setCertificates(data || []);
      setCachedValue("skill_lab_certificates", data || []);
    } catch (err) {
      console.error("Failed to load certificates", err);
    }
  };

  const loadData = async () => {
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const promises: Promise<any>[] = [];

    // Always fetch course catalog in parallel
    promises.push(
      apiService.getCourses()
        .then((fetchedCourses) => {
          if (fetchedCourses && fetchedCourses.length > 0) {
            setCourses(fetchedCourses);
            setCachedValue("skill_lab_courses", fetchedCourses);
          }
        })
        .catch((courseErr) => {
          console.error("Failed to load courses from DB", courseErr);
        })
    );

    // If authenticated, fetch candidate statistics and states in parallel
    if (token) {
      promises.push(
        apiService.getProfile()
          .then((prof) => {
            setProfile(prof);
            setCachedValue("skill_lab_profile", prof);
          })
          .catch((err) => console.error("Failed to load profile", err))
      );

      promises.push(
        loadEnrollments()
          .catch((err) => console.error("Failed to load enrollments", err))
      );

      promises.push(
        loadCertificates()
          .catch((err) => console.error("Failed to load certificates", err))
      );

      promises.push(
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
          .catch((err) => console.error("Failed to load career readiness", err))
      );
    }

    await Promise.allSettled(promises);
  };

  useEffect(() => {
    loadData();
  }, [email]);

  // Dynamically load active enrollment curriculum for the Continue Learning stepper in background
  useEffect(() => {
    if (enrollments && enrollments.length > 0) {
      const activeEnroll = enrollments[0];
      const courseObj = courses.find(c => c.id === activeEnroll.course_id) || activeEnroll.course;
      if (courseObj) {
        setActiveEnrollmentCourse(courseObj);
        setCachedValue("skill_lab_activeEnrollmentCourse", courseObj);
        apiService.getCourseCurriculum(courseObj.id)
          .then(rawData => {
            const data = transformNewCurriculumToOld(rawData);
            setActiveEnrollmentCurriculum(data);
            setCachedValue("skill_lab_activeEnrollmentCurriculum", data);
          })
          .catch(err => {
            console.error("Error background fetching active curriculum", err);
          });
      }
    } else {
      setActiveEnrollmentCourse(null);
      setActiveEnrollmentCurriculum(null);
    }
  }, [enrollments, courses]);

  const handleEnrollCourse = async (id: string | number) => {
    try {
      await apiService.enrollCourse(id);
      if (!enrolledCourseIds.includes(id)) {
        setEnrolledCourseIds([...enrolledCourseIds, id]);
      }
      setXp(prev => prev + 50);
      await loadEnrollments();
    } catch (err) {
      console.error("Failed to enroll in course:", err);
    }
  };

  const handleStartCourse = async (course: any) => {
    setSelectedCourse(course);
    await handleEnrollCourse(course.id);
    await fetchCurriculum(course.id);
    setActiveView("course-player");
  };

  const handleGoToLesson = async (course: any, lessonType: string) => {
    setSelectedCourse(course);
    setLoadingCurriculum(true);
    setActiveView("course-player");
    try {
      await handleEnrollCourse(course.id);
      const rawData = await apiService.getCourseCurriculum(course.id);
      const data = transformNewCurriculumToOld(rawData);
      setCurriculum(data);
      setCompletedLessonIds(data.completed_lesson_ids || []);
      
      const flatLessons: any[] = [];
      data.sections?.forEach((sec: any) => {
        sec.lessons?.forEach((les: any) => {
          flatLessons.push(les);
        });
      });
      
      const targetLesson = flatLessons.find(l => l.type === lessonType && !l.is_locked) || 
                           flatLessons.find(l => l.type === lessonType) || 
                           flatLessons[0];
      
      if (targetLesson) {
        setCurrentLesson(targetLesson);
        setActiveMediaTab(targetLesson.type === "pdf" ? "pdf" : "video");
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingCurriculum(false);
    }
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
