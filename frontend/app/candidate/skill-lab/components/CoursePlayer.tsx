"use client";

import React, { useState, useEffect, useRef } from "react";
import { apiService } from "@/services/api";
import { useAuthStore } from "@/store/authStore";
import { Play, BookOpen, Brain, Trash2, ArrowRight, Clock, ShieldAlert, RefreshCw, Upload, Code, CheckCircle } from "lucide-react";

interface CoursePlayerProps {
  selectedCourse: any;
  activeView: string;
  setActiveView: (view: any) => void;
  curriculum: any;
  currentLesson: any;
  setCurrentLesson: (lesson: any) => void;
  completedLessonIds: number[];
  setCompletedLessonIds: (ids: number[]) => void;
  loadingCurriculum: boolean;
  fetchCurriculum: (courseId: string | number, autoSelectLessonId?: string | number) => Promise<void>;
  loadEnrollments: () => Promise<void>;
  loadData: () => Promise<void>;
  activeMediaTab: "video" | "pdf";
  setActiveMediaTab: (tab: "video" | "pdf") => void;
  notepadText: string;
  setNotepadText: (text: string) => void;
  savedNotes: string[];
  setSavedNotes: (notes: string[]) => void;
}

export default function CoursePlayer({
  selectedCourse,
  activeView,
  setActiveView,
  curriculum,
  currentLesson,
  setCurrentLesson,
  completedLessonIds,
  setCompletedLessonIds,
  loadingCurriculum,
  fetchCurriculum,
  loadEnrollments,
  loadData,
  activeMediaTab,
  setActiveMediaTab,
  notepadText,
  setNotepadText,
  savedNotes,
  setSavedNotes
}: CoursePlayerProps) {
  const { email, fullName } = useAuthStore();
  const firstName = fullName ? fullName.split(" ")[0] : "Candidate";

  // Player view sub-tabs
  const [playerTab, setPlayerTab] = useState<"overview" | "notes" | "resources" | "discussion" | "qna">("overview");

  // Quiz States
  const [quizAnswers, setQuizAnswers] = useState<Record<number, number>>({});
  const [quizSubmitted, setQuizSubmitted] = useState(false);
  const [quizScore, setQuizScore] = useState<number | null>(null);

  // Written Assessment States
  const [writtenAnswers, setWrittenAnswers] = useState<Record<number, string>>({});

  // AI Interview Room States
  const [interviewStarted, setInterviewStarted] = useState(false);
  const [currentInterviewQuestionIdx, setCurrentInterviewQuestionIdx] = useState(0);
  const [interviewTranscript, setInterviewTranscript] = useState<{ role: "interviewer" | "candidate"; text: string }[]>([]);
  const [candidateInterviewResponse, setCandidateInterviewResponse] = useState("");
  const [submittingInterview, setSubmittingInterview] = useState(false);
  const [interviewResult, setInterviewResult] = useState<any>(null);

  // AI Tara Voice Assessment States
  const [interviewInputMode, setInterviewInputMode] = useState<"voice" | "type">("voice");
  const [isRecording, setIsRecording] = useState(false);
  const [interviewTimeRemaining, setInterviewTimeRemaining] = useState(180);
  const [interviewAnswers, setInterviewAnswers] = useState<Record<string, string>>({});
  const [aiVoiceState, setAiVoiceState] = useState<"idle" | "speaking" | "listening" | "processing">("idle");
  const recognitionRef = useRef<any>(null);

  // Assignment / Project Mock States
  const [assignmentUploaded, setAssignmentUploaded] = useState(false);
  const [submittingAssignment, setSubmittingAssignment] = useState(false);
  const [assignmentFilename, setAssignmentFilename] = useState("");

  const [projectUploaded, setProjectUploaded] = useState(false);
  const [submittingProject, setSubmittingProject] = useState(false);
  const [projectFilename, setProjectFilename] = useState("");

  // Discussions Forum States
  const [forumPosts, setForumPosts] = useState<any[]>([]);
  const [newPostTitle, setNewPostTitle] = useState("");
  const [newPostContent, setNewPostContent] = useState("");
  const [newPostCategory, setNewPostCategory] = useState("Generative AI");

  // Speech helper functions
  const speakQuestion = (text: string) => {
    if (typeof window === "undefined" || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    
    utterance.onstart = () => setAiVoiceState("speaking");
    utterance.onend = () => {
      setAiVoiceState("listening");
      startSpeechRecognition();
    };
    
    window.speechSynthesis.speak(utterance);
  };

  const startSpeechRecognition = () => {
    if (typeof window === "undefined") return;
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
    }

    const rec = new SpeechRecognition();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = "en-US";

    rec.onstart = () => {
      setIsRecording(true);
      setAiVoiceState("listening");
    };

    rec.onresult = (event: any) => {
      let finalTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        }
      }
      if (finalTranscript) {
        setCandidateInterviewResponse(prev => {
          const space = prev.endsWith(" ") || !prev ? "" : " ";
          return prev + space + finalTranscript;
        });
      }
    };

    rec.onerror = (e: any) => {
      console.error("Speech recognition error:", e);
    };

    rec.onend = () => {
      setIsRecording(false);
    };

    recognitionRef.current = rec;
    rec.start();
  };

  const stopSpeechRecognition = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {}
    }
    setIsRecording(false);
    setAiVoiceState("idle");
  };

  const handleAdvanceQuestion = async (isTimeout = false) => {
    if (!currentLesson || !currentLesson.module_interview) return;
    const questions = currentLesson.module_interview.questions || [];
    const currentQuestion = questions[currentInterviewQuestionIdx];
    
    stopSpeechRecognition();

    const updatedAnswers = {
      ...interviewAnswers,
      [currentQuestion]: candidateInterviewResponse || "(No verbal answer provided)"
    };
    setInterviewAnswers(updatedAnswers);

    const newTranscript = [
      ...interviewTranscript,
      { role: "candidate" as const, text: candidateInterviewResponse || "(No verbal answer provided)" }
    ];
    setInterviewTranscript(newTranscript);
    setCandidateInterviewResponse("");

    const nextIdx = currentInterviewQuestionIdx + 1;
    if (nextIdx < questions.length) {
      setCurrentInterviewQuestionIdx(nextIdx);
      const nextQuestion = questions[nextIdx];
      const nextTranscript = [
        ...newTranscript,
        { role: "interviewer" as const, text: nextQuestion }
      ];
      setInterviewTranscript(nextTranscript);
      setInterviewTimeRemaining(180);
      setTimeout(() => {
        speakQuestion(nextQuestion);
      }, 500);
    } else {
      await submitFullInterview(updatedAnswers);
    }
  };

  const submitFullInterview = async (finalAnswers: Record<string, string>) => {
    if (!currentLesson || !currentLesson.module_interview) return;
    setSubmittingInterview(true);
    setAiVoiceState("processing");
    try {
      const res = await apiService.submitModuleInterview(currentLesson.module_interview.id, finalAnswers);
      setInterviewResult(res);
      await fetchCurriculum(selectedCourse.id, currentLesson.id);
      await loadEnrollments();
      await loadData();
    } catch (err) {
      console.error(err);
      alert("Failed to submit assessment interview.");
      setAiVoiceState("idle");
    } finally {
      setSubmittingInterview(false);
    }
  };

  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
    };
  }, []);

  useEffect(() => {
    let interval: any;
    if (interviewStarted && !submittingInterview && !interviewResult && aiVoiceState === "listening") {
      interval = setInterval(() => {
        setInterviewTimeRemaining(prev => {
          if (prev <= 1) {
            clearInterval(interval);
            handleAdvanceQuestion(true);
            return 180;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [interviewStarted, currentInterviewQuestionIdx, submittingInterview, interviewResult, aiVoiceState, candidateInterviewResponse, interviewAnswers]);

  // Forum helper
  const handleCreateForumPost = () => {
    if (!newPostTitle.trim() || !newPostContent.trim()) return;
    const newPost = {
      id: forumPosts.length + 1,
      title: newPostTitle,
      content: newPostContent,
      author: firstName,
      category: newPostCategory,
      repliesCount: 0,
      date: "Just now"
    };
    setForumPosts([newPost, ...forumPosts]);
    setNewPostTitle("");
    setNewPostContent("");
  };

  // Notes helper
  const handleSaveNotes = () => {
    if (!notepadText.trim()) return;
    setSavedNotes([notepadText, ...savedNotes]);
    setNotepadText("");
  };

  const getYoutubeVideoId = (url: string) => {
    if (!url) return null;
    let regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
    let match = url.match(regExp);
    return (match && match[2].length === 11) ? match[2] : null;
  };

  if (!currentLesson) {
    return (
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-12 text-center text-slate-500">
        No modules loaded. Click back to select a course.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex justify-between items-center">
        <button 
          onClick={() => setActiveView("course-details")}
          className="text-10 font-bold text-indigo-600 hover:underline flex items-center gap-1 cursor-pointer"
        >
          <span>← Back to Details</span>
        </button>

        <h3 className="text-xs font-black text-slate-800 dark:text-white truncate max-w-md">
          {selectedCourse.title}
        </h3>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* PLAYER COLUMN: Renders Lesson Content */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm min-h-460 flex flex-col justify-between">
            {loadingCurriculum ? (
              <div className="flex-1 flex flex-col items-center justify-center gap-3">
                <RefreshCw size={24} className="text-indigo-600 animate-spin" />
                <span className="text-xs text-slate-500 font-bold">Updating player curriculum...</span>
              </div>
            ) : currentLesson.type === "video" ? (
              <div className="flex flex-col gap-4 flex-1">
                <div>
                  <span className="px-2 py-0.5 rounded text-8 font-bold font-mono bg-indigo-100 text-indigo-600 dark:bg-indigo-950/30 dark:text-indigo-400 uppercase tracking-wider">
                    Lesson Video
                  </span>
                  <h3 className="text-sm font-black text-slate-800 dark:text-white mt-2 leading-tight">{currentLesson.title}</h3>
                </div>
                
                <div className="aspect-video w-full rounded-2xl overflow-hidden bg-black shadow-inner border border-slate-200 dark:border-slate-800 relative group mt-1">
                  {getYoutubeVideoId(currentLesson.video_url) ? (
                    <iframe
                      width="100%"
                      height="100%"
                      src={`https://www.youtube.com/embed/${getYoutubeVideoId(currentLesson.video_url)}`}
                      title={currentLesson.title}
                      frameBorder="0"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                      allowFullScreen
                      className="w-full h-full"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-slate-500 text-xs font-bold">
                      No video URL configured.
                    </div>
                  )}
                </div>
              </div>
            ) : currentLesson.type === "pdf" ? (
              <div className="flex flex-col gap-4 flex-1">
                <div>
                  <span className="px-2 py-0.5 rounded text-8 font-bold font-mono bg-indigo-100 text-indigo-600 dark:bg-indigo-950/30 dark:text-indigo-400 uppercase tracking-wider">
                    Course Handbook
                  </span>
                  <h3 className="text-sm font-black text-slate-800 dark:text-white mt-2 leading-tight">{currentLesson.title}</h3>
                </div>
                
                <div className="flex-1 min-h-350 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-850 rounded-2xl p-4 flex flex-col justify-between items-center mt-2 relative">
                  <div className="my-auto text-center flex flex-col items-center gap-3">
                    <BookOpen size={48} className="text-indigo-600/35" />
                    <div>
                      <h4 className="text-xs font-bold text-slate-800 dark:text-white">{currentLesson.title}</h4>
                      <p className="text-10 text-slate-450 mt-1 max-w-xs leading-normal">
                        Click the download button or open the link below to view the module study handbook.
                      </p>
                    </div>
                  </div>
                  
                  <a
                    href={currentLesson.pdf_url}
                    target="_blank"
                    rel="noreferrer"
                    className="w-full sm:w-auto px-6 py-2.8 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-all text-center cursor-pointer shadow-md"
                  >
                    Open Handbook PDF
                  </a>
                </div>
              </div>
            ) : currentLesson.type === "quiz" && currentLesson.quiz ? (
              <div className="flex flex-col gap-4 flex-1">
                <div>
                  <span className="px-2 py-0.5 rounded text-8 font-bold font-mono bg-indigo-100 text-indigo-600 dark:bg-indigo-950/30 dark:text-indigo-400 uppercase tracking-wider">
                    Knowledge Quiz
                  </span>
                  <h3 className="text-sm font-black text-slate-800 dark:text-white mt-2 leading-tight">{currentLesson.quiz.title}</h3>
                </div>

                {quizSubmitted ? (
                  <div className="my-auto text-center flex flex-col items-center gap-4 py-8">
                    <div className="w-16 h-16 rounded-full bg-emerald-500/10 text-emerald-500 flex items-center justify-center text-3xl shadow-inner">
                      ✓
                    </div>
                    <div>
                      <h4 className="text-sm font-black text-slate-800 dark:text-white">Quiz Completed!</h4>
                      <p className="text-xs text-slate-450 mt-1">
                        Your Score: <span className="font-extrabold text-emerald-500">{quizScore}%</span>
                      </p>
                    </div>
                    
                    <button
                      onClick={() => {
                        setQuizAnswers({});
                        setQuizSubmitted(false);
                        setQuizScore(null);
                      }}
                      className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl cursor-pointer"
                    >
                      Retry Quiz
                    </button>
                  </div>
                ) : (
                  <div className="space-y-5 mt-2">
                    {currentLesson.quiz.questions.map((q: any, qIdx: number) => (
                      <div key={q.id} className="p-4 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-850 rounded-2xl flex flex-col gap-3">
                        <span className="text-10 font-black text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">Question {qIdx + 1}</span>
                        <p className="text-xs font-bold text-slate-800 dark:text-white">{q.question}</p>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 mt-1">
                          {q.options.map((opt: string, optIdx: number) => (
                            <button
                              key={optIdx}
                              onClick={() => setQuizAnswers(prev => ({ ...prev, [qIdx]: optIdx }))}
                              className={`p-3 rounded-xl border text-left text-xs font-semibold transition-all cursor-pointer ${
                                quizAnswers[qIdx] === optIdx
                                  ? "bg-indigo-600 text-white border-indigo-600 shadow-sm font-bold"
                                  : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-350 hover:border-indigo-500/30"
                              }`}
                            >
                              {opt}
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}

                    <div className="flex justify-end pt-2">
                      <button
                        onClick={async () => {
                          const totalQ = currentLesson.quiz.questions.length;
                          let correct = 0;
                          currentLesson.quiz.questions.forEach((q: any, idx: number) => {
                            if (quizAnswers[idx] === q.correct_option) correct++;
                          });
                          const score = Math.round((correct / totalQ) * 100);
                          
                          try {
                            const res = await apiService.submitQuiz(currentLesson.quiz.id, score >= 70);
                            setQuizScore(score);
                            setQuizSubmitted(true);
                            await fetchCurriculum(selectedCourse.id, currentLesson.id);
                            await loadEnrollments();
                            await loadData();
                          } catch (err) {
                            console.error(err);
                            alert("Failed to submit quiz.");
                          }
                        }}
                        disabled={Object.keys(quizAnswers).length < currentLesson.quiz.questions.length}
                        className="px-6 py-2.8 bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-gray-200 dark:disabled:bg-gray-800 disabled:text-slate-400 text-xs font-bold rounded-xl cursor-pointer disabled:cursor-not-allowed shadow-md"
                      >
                        Submit Answers
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : currentLesson.type === "written_assessment" && currentLesson.written_assessment ? (
              <div className="flex flex-col gap-4 flex-1">
                <div>
                  <span className="px-2 py-0.5 rounded text-8 font-bold font-mono bg-indigo-100 text-indigo-600 dark:bg-indigo-950/30 dark:text-indigo-400 uppercase tracking-wider">
                    Written Assessment
                  </span>
                  <h3 className="text-sm font-black text-slate-800 dark:text-white mt-2 leading-tight">{currentLesson.written_assessment.title}</h3>
                </div>

                {currentLesson.written_assessment.passed ? (
                  <div className="my-auto text-center flex flex-col items-center gap-4 py-8">
                    <div className="w-16 h-16 rounded-full bg-emerald-500/10 text-emerald-500 flex items-center justify-center text-3xl shadow-inner">
                      ✓
                    </div>
                    <div>
                      <h4 className="text-sm font-black text-slate-800 dark:text-white">Assessment Submitted & Evaluated!</h4>
                      <p className="text-xs text-slate-450 mt-1">
                        Best Score: <span className="font-extrabold text-emerald-500">{currentLesson.written_assessment.best_score}%</span>
                      </p>
                      {currentLesson.written_assessment.feedback && (
                        <p className="text-10 text-slate-500 bg-slate-50 dark:bg-slate-950 p-3 rounded-xl border border-slate-200 dark:border-slate-850 mt-3 max-w-md mx-auto leading-relaxed">
                          Feedback: {currentLesson.written_assessment.feedback}
                        </p>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-5 mt-2">
                    {currentLesson.written_assessment.questions.map((q: string, qIdx: number) => (
                      <div key={qIdx} className="p-4 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-850 rounded-2xl flex flex-col gap-3">
                        <span className="text-10 font-black text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">Question {qIdx + 1}</span>
                        <p className="text-xs font-bold text-slate-800 dark:text-white">{q}</p>
                        
                        <textarea
                          placeholder="Type your explanation answer here..."
                          value={writtenAnswers[qIdx] || ""}
                          onChange={(e) => setWrittenAnswers(prev => ({ ...prev, [qIdx]: e.target.value }))}
                          rows={4}
                          className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-3 text-xs text-slate-800 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
                        />
                      </div>
                    ))}

                    <div className="flex justify-end pt-2">
                      <button
                        onClick={async () => {
                          try {
                            const res = await apiService.submitWrittenAssessment(currentLesson.written_assessment.id, writtenAnswers);
                            await fetchCurriculum(selectedCourse.id, currentLesson.id);
                            await loadEnrollments();
                            await loadData();
                          } catch (err) {
                            console.error(err);
                            alert("Failed to submit written assessment.");
                          }
                        }}
                        disabled={Object.keys(writtenAnswers).length < currentLesson.written_assessment.questions.length}
                        className="px-6 py-2.8 bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-gray-200 dark:disabled:bg-gray-800 disabled:text-slate-400 text-xs font-bold rounded-xl cursor-pointer disabled:cursor-not-allowed shadow-md"
                      >
                        Submit Assessment
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : currentLesson.type === "assignment" && currentLesson.assignment ? (
              <div className="flex flex-col gap-4 flex-1">
                <div>
                  <span className="text-10 font-mono font-bold text-indigo-600 uppercase tracking-widest">
                    Practical Homework Project
                  </span>
                  <h3 className="text-xs font-bold text-slate-800 mt-1">{currentLesson.assignment.title}</h3>
                </div>

                <div className="p-4 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-2xl space-y-3 mt-2">
                  <h4 className="text-xs font-bold text-slate-800 dark:text-white">Overview Description:</h4>
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">{currentLesson.assignment.description}</p>
                </div>

                <div className="border border-dashed border-slate-200 dark:border-slate-800 rounded-3xl p-6.5 text-center flex flex-col items-center justify-center gap-3 bg-white dark:bg-slate-900">
                  <Upload className="text-indigo-600/60 shrink-0" size={24} />
                  <div>
                    <span className="text-xs font-bold text-slate-800 dark:text-white block">Submit Code Archive</span>
                    <span className="text-9 text-slate-500 mt-1 block">Drag & drop your files, or click to upload (.py, .zip)</span>
                  </div>

                  <input
                    type="file"
                    id="assignment-file"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        setAssignmentFilename(file.name);
                        setAssignmentUploaded(true);
                      }
                    }}
                    className="hidden"
                  />

                  <label
                    htmlFor="assignment-file"
                    className="px-4 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-10 font-bold rounded-xl cursor-pointer hover:bg-slate-50"
                  >
                    {assignmentFilename ? "Replace File" : "Choose File"}
                  </label>

                  {assignmentFilename && (
                    <span className="text-10 text-emerald-500 font-mono font-bold mt-1">Selected: {assignmentFilename}</span>
                  )}
                </div>

                <div className="flex justify-end pt-4 border-t border-slate-100 dark:border-slate-800/40">
                  <button
                    disabled={!assignmentUploaded || submittingAssignment}
                    onClick={async () => {
                      setSubmittingAssignment(true);
                      setTimeout(async () => {
                        try {
                          await apiService.completeLesson(currentLesson.id);
                          alert("Assignment submitted successfully! +50 XP");
                          await fetchCurriculum(selectedCourse.id, currentLesson.id);
                          await loadEnrollments();
                          await loadData();
                        } catch (err) {
                          console.error(err);
                        } finally {
                          setSubmittingAssignment(false);
                        }
                      }, 1500);
                    }}
                    className="px-4.5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-gray-250 disabled:text-slate-400 text-xs font-bold rounded-xl cursor-pointer"
                  >
                    {submittingAssignment ? "Submitting Code..." : "Submit Assignment Code"}
                  </button>
                </div>
              </div>
            ) : currentLesson.type === "project" && currentLesson.project ? (
              <div className="flex flex-col gap-4 flex-1">
                <div>
                  <span className="text-10 font-mono font-bold text-emerald-500 uppercase tracking-widest">
                    Capstone Coding Project
                  </span>
                  <h3 className="text-xs font-bold text-slate-800 dark:text-white mt-1">{currentLesson.project.title}</h3>
                </div>

                <div className="p-4 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-2xl space-y-3 mt-2">
                  <h4 className="text-xs font-bold text-slate-800 dark:text-white">Task Objectives:</h4>
                  <p className="text-xs text-slate-650 dark:text-slate-400 leading-relaxed">{currentLesson.project.description}</p>
                </div>

                <div className="border border-dashed border-slate-200 dark:border-slate-800 rounded-3xl p-6.5 text-center flex flex-col items-center justify-center gap-3 bg-white dark:bg-slate-900">
                  <Upload className="text-indigo-650/60 shrink-0" size={24} />
                  <div>
                    <span className="text-xs font-bold text-slate-800 dark:text-white block">Submit Finished Project</span>
                    <span className="text-9 text-slate-500 mt-1 block">Drag & drop your files, or click to upload (.zip)</span>
                  </div>

                  <input
                    type="file"
                    id="project-file"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        setProjectFilename(file.name);
                        setProjectUploaded(true);
                      }
                    }}
                    className="hidden"
                  />

                  <label
                    htmlFor="project-file"
                    className="px-4 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-10 font-bold rounded-xl cursor-pointer hover:bg-slate-50"
                  >
                    {projectFilename ? "Replace File" : "Choose File"}
                  </label>

                  {projectFilename && (
                    <span className="text-10 text-emerald-500 font-mono font-bold mt-1">Selected: {projectFilename}</span>
                  )}
                </div>

                <div className="flex justify-end pt-4 border-t border-slate-100 dark:border-slate-800/40">
                  <button
                    disabled={!projectUploaded || submittingProject}
                    onClick={async () => {
                      setSubmittingProject(true);
                      setTimeout(async () => {
                        try {
                          await apiService.completeLesson(currentLesson.id);
                          alert("Capstone Project submitted successfully! +100 XP");
                          await fetchCurriculum(selectedCourse.id, currentLesson.id);
                          await loadEnrollments();
                          await loadData();
                        } catch (err) {
                          console.error(err);
                        } finally {
                          setSubmittingProject(false);
                        }
                      }, 1500);
                    }}
                    className="px-4.5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-gray-250 disabled:text-slate-400 text-xs font-bold rounded-xl cursor-pointer"
                  >
                    {submittingProject ? "Submitting Code..." : "Submit Capstone Project"}
                  </button>
                </div>
              </div>
            ) : currentLesson.type === "ai_interview" && currentLesson.module_interview ? (
              <div className="flex flex-col gap-4 flex-1">
                <div>
                  <span className="px-2 py-0.5 rounded text-8 font-bold font-mono bg-indigo-100 text-indigo-600 dark:bg-indigo-950/30 dark:text-indigo-400 uppercase tracking-wider">
                    AI Interview Room
                  </span>
                  <h3 className="text-sm font-black text-slate-800 dark:text-white mt-2 leading-tight">{currentLesson.module_interview.title}</h3>
                </div>

                {interviewResult ? (
                  <div className="my-auto text-center flex flex-col items-center gap-4 py-8">
                    <div className="w-16 h-16 rounded-full bg-emerald-500/10 text-emerald-500 flex items-center justify-center text-3xl shadow-inner">
                      ✓
                    </div>
                    <div>
                      <h4 className="text-sm font-black text-slate-800 dark:text-white">AI Evaluation Completed!</h4>
                      <p className="text-xs text-slate-450 mt-1">
                        Interview Score: <span className="font-extrabold text-emerald-500">{interviewResult.interview_score}%</span>
                      </p>
                      <div className="text-left text-10 text-slate-500 bg-slate-50 dark:bg-slate-950 p-4 rounded-xl border border-slate-200 dark:border-slate-850 mt-3 max-w-md mx-auto space-y-1 leading-normal">
                        <span className="font-bold text-slate-700 dark:text-slate-350 uppercase tracking-wider block text-8">Mentor feedback report:</span>
                        <p>{interviewResult.feedback}</p>
                      </div>
                    </div>
                  </div>
                ) : !interviewStarted ? (
                  <div className="my-auto text-center flex flex-col items-center gap-4 py-8">
                    <div className="w-16 h-16 rounded-2xl bg-indigo-50 dark:bg-indigo-950/30 text-indigo-600 flex items-center justify-center">
                      <Brain size={28} />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-800 dark:text-white">Ready for your AI interview simulation?</h4>
                      <p className="text-10 text-slate-450 mt-1 max-w-xs mx-auto leading-relaxed">
                        TARA will evaluate your verbal explanations. This requires micro-phone permissions for speech-to-text.
                      </p>
                    </div>

                    <button
                      onClick={() => {
                        setInterviewStarted(true);
                        const firstQ = currentLesson.module_interview.questions[0];
                        setInterviewTranscript([
                          { role: "interviewer", text: firstQ }
                        ]);
                        speakQuestion(firstQ);
                      }}
                      className="px-6 py-2.8 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-all shadow-md"
                    >
                      Start Interview
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col gap-4 flex-1">
                    {/* Transcript Pane */}
                    <div className="flex-1 min-h-200 max-h-250 overflow-y-auto bg-slate-50 dark:bg-slate-950 border border-slate-250 dark:border-slate-850 p-4 rounded-2xl flex flex-col gap-3.5 scrollbar-thin">
                      {interviewTranscript.map((msg, idx) => (
                        <div
                          key={idx}
                          className={`max-w-80-pct rounded-2xl p-3 text-xs leading-relaxed ${
                            msg.role === "candidate"
                              ? "bg-indigo-600 text-white self-end rounded-tr-none"
                              : "bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-100 self-start rounded-tl-none"
                          }`}
                        >
                          <span className="text-8 font-black uppercase opacity-75 block mb-0.5">
                            {msg.role === "candidate" ? "You" : "TARA AI Assessor"}
                          </span>
                          <p className="font-semibold">{msg.text}</p>
                        </div>
                      ))}
                    </div>

                    {/* Microphone status and controls */}
                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-4 rounded-2xl flex flex-col gap-3">
                      <div className="flex justify-between items-center">
                        <span className="text-9 font-black text-slate-450 uppercase tracking-wider">
                          Question {currentInterviewQuestionIdx + 1} of {currentLesson.module_interview.questions.length}
                        </span>

                        <div className="flex items-center gap-1.5 text-10 font-bold text-slate-500">
                          <Clock size={12} />
                          <span>{Math.floor(interviewTimeRemaining / 60)}:{(interviewTimeRemaining % 60).toString().padStart(2, '0')}</span>
                        </div>
                      </div>

                      {/* Speaking indicator / typing options */}
                      {interviewInputMode === "voice" ? (
                        <div className="flex flex-col items-center gap-3 py-2">
                          <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                              aiVoiceState === "listening"
                                ? "bg-red-500 text-white animate-pulse"
                                : aiVoiceState === "speaking"
                                  ? "bg-indigo-500 text-white"
                                  : "bg-slate-100 dark:bg-slate-800 text-slate-400"
                            }`}>
                              <Brain size={16} />
                            </div>
                            <span className="text-xs font-bold text-slate-800 dark:text-white capitalize">
                              {aiVoiceState === "listening" ? "Listening to response..." : aiVoiceState === "speaking" ? "TARA is speaking..." : "Assessor Ready"}
                            </span>
                          </div>

                          <textarea
                            placeholder="Voice transcript text will stream here as you speak..."
                            value={candidateInterviewResponse}
                            onChange={(e) => setCandidateInterviewResponse(e.target.value)}
                            rows={2}
                            className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-3 text-xs text-slate-800 dark:text-slate-100 focus:outline-none"
                          />
                        </div>
                      ) : (
                        <textarea
                          placeholder="Type your structured explanation answer here..."
                          value={candidateInterviewResponse}
                          onChange={(e) => setCandidateInterviewResponse(e.target.value)}
                          rows={3}
                          className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-3 text-xs text-slate-800 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
                        />
                      )}

                      {/* Action buttons */}
                      <div className="flex justify-between items-center border-t border-slate-100 dark:border-slate-800/40 pt-3">
                        <button
                          onClick={() => setInterviewInputMode(interviewInputMode === "voice" ? "type" : "voice")}
                          className="text-10 text-indigo-600 dark:text-indigo-400 font-bold hover:underline cursor-pointer"
                        >
                          Switch to {interviewInputMode === "voice" ? "Keyboard Typing" : "Voice Assessment"}
                        </button>

                        <button
                          onClick={() => handleAdvanceQuestion(false)}
                          className="px-4.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-extrabold rounded-xl transition-all shadow-md flex items-center gap-1 cursor-pointer"
                        >
                          <span>{currentInterviewQuestionIdx + 1 === currentLesson.module_interview.questions.length ? "Submit Interview" : "Next Question"}</span>
                          <ArrowRight size={12} />
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : null}

            {/* Bottom Controls Row: Mark Done, Navigation */}
            <div className="flex justify-between items-center border-t border-slate-100 dark:border-slate-800/40 pt-4 mt-6">
              <div className="flex gap-2">
                <button
                  onClick={async () => {
                    const flat: any[] = [];
                    curriculum.sections?.forEach((s: any) => s.lessons?.forEach((l: any) => flat.push(l)));
                    const idx = flat.findIndex(l => l.id === currentLesson.id);
                    if (idx > 0) {
                      setCurrentLesson(flat[idx - 1]);
                      setQuizSubmitted(false);
                      setQuizAnswers({});
                    }
                  }}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 text-slate-700 text-xs font-bold rounded-xl cursor-pointer"
                >
                  Previous
                </button>
                <button
                  onClick={async () => {
                    const flat: any[] = [];
                    curriculum.sections?.forEach((s: any) => s.lessons?.forEach((l: any) => flat.push(l)));
                    const idx = flat.findIndex(l => l.id === currentLesson.id);
                    if (idx < flat.length - 1) {
                      setCurrentLesson(flat[idx + 1]);
                      setQuizSubmitted(false);
                      setQuizAnswers({});
                    }
                  }}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 text-slate-700 text-xs font-bold rounded-xl cursor-pointer"
                >
                  Next
                </button>
              </div>

              <div className="flex items-center gap-3">
                {(currentLesson.type === "video" || currentLesson.type === "pdf") && (
                  <>
                    <button
                      onClick={async () => {
                        try {
                          if (currentLesson.type === "pdf") {
                            await apiService.completePdf(currentLesson.id);
                          } else {
                            await apiService.completeLesson(currentLesson.id);
                          }
                          await fetchCurriculum(selectedCourse.id, currentLesson.id);
                          await loadEnrollments();
                          await loadData();
                        } catch (err) {
                          console.error(err);
                        }
                      }}
                      disabled={completedLessonIds.includes(currentLesson.id)}
                      className={`px-4.5 py-2.5 rounded-xl text-xs font-extrabold flex items-center gap-1.5 transition-all shadow-sm ${
                        completedLessonIds.includes(currentLesson.id)
                          ? "bg-emerald-500 text-white cursor-not-allowed"
                          : "bg-indigo-600 hover:bg-indigo-700 text-white cursor-pointer"
                      }`}
                    >
                      <CheckCircle size={13} />
                      <span>{completedLessonIds.includes(currentLesson.id) ? "Completed" : "Mark Done (+25 XP)"}</span>
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Player Tabbed Menu Pane (Overview, Notepad, discussions etc.) */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm flex flex-col gap-5">
            <div className="flex gap-5 border-b border-slate-100 dark:border-slate-800/40 pb-2.5">
              {[
                { id: "overview", label: "Overview" },
                { id: "notes", label: "Notepad" },
                { id: "discussion", label: "Discussions" }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setPlayerTab(tab.id as any)}
                  className={`text-xs font-bold pb-2 transition-all border-b-2 cursor-pointer ${
                    playerTab === tab.id
                      ? "border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400 font-extrabold"
                      : "border-transparent text-slate-500 hover:text-slate-800"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {playerTab === "overview" && (
              <div className="text-xs text-slate-650 dark:text-slate-400 space-y-3 leading-relaxed font-semibold">
                <h4 className="text-slate-800 dark:text-white font-bold text-xs">About this Module</h4>
                <p>
                  This session forms part of the training for {selectedCourse.title}. Completion of videos, handbooks, and assessments is required to qualify for the official credential.
                </p>
                <div className="flex gap-4.5 text-10 text-slate-450 border-t border-slate-100 dark:border-slate-800/40 pt-3.5 mt-3 w-full">
                  <span>Rating: {selectedCourse.rating} ★</span>
                  <span>Duration: {selectedCourse.duration}</span>
                  <span>Category: {selectedCourse.category}</span>
                </div>
              </div>
            )}

            {playerTab === "notes" && (
              <div className="flex flex-col gap-4">
                <textarea
                  placeholder="Jot down notes as you learn..."
                  value={notepadText}
                  onChange={(e) => setNotepadText(e.target.value)}
                  rows={4}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 text-xs text-slate-800 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
                />
                
                <div className="flex justify-between items-center">
                  <span className="text-10 text-slate-450 font-bold">Saved Notes: {savedNotes.length}</span>
                  <button
                    onClick={handleSaveNotes}
                    className="px-4.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl cursor-pointer shadow-sm"
                  >
                    Save Note (+10 XP)
                  </button>
                </div>

                <div className="space-y-2 mt-2">
                  {savedNotes.map((note, i) => (
                    <div key={i} className="p-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-850 rounded-xl text-xs text-slate-600 dark:text-slate-400 relative">
                      <button
                        onClick={() => setSavedNotes(savedNotes.filter((_, idx) => idx !== i))}
                        className="absolute right-2 top-2 text-slate-400 hover:text-red-500"
                      >
                        <Trash2 size={13} />
                      </button>
                      <p className="pr-5 leading-normal">{note}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {playerTab === "discussion" && (
              <div className="flex flex-col gap-4">
                <h4 className="text-xs font-bold text-slate-800 dark:text-white">Community Discussions ({forumPosts.length})</h4>
                
                <div className="space-y-3">
                  {forumPosts.length === 0 ? (
                    <div className="p-6 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-850 rounded-2xl text-center text-xs text-slate-500 font-bold">
                      No discussion threads started yet. Be the first to start a thread!
                    </div>
                  ) : (
                    forumPosts.map((post) => (
                      <div key={post.id} className="p-3.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-850 rounded-2xl text-xs">
                        <h5 className="font-extrabold text-slate-800 dark:text-white leading-tight">{post.title}</h5>
                        <p className="text-slate-600 dark:text-slate-400 mt-1 text-11 font-semibold leading-relaxed">{post.content}</p>
                        
                        <div className="flex justify-between items-center text-10 text-slate-450 mt-3 border-t border-slate-100 dark:border-slate-800/40 pt-2 font-bold">
                          <span>By {post.author} • {post.date}</span>
                          <span>{post.repliesCount} replies</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                <div className="border-t border-slate-100 dark:border-slate-800/40 pt-4 flex flex-col gap-3">
                  <span className="text-xs font-bold text-slate-800 dark:text-white">Start a new thread</span>
                  <input
                    type="text"
                    placeholder="Thread title..."
                    value={newPostTitle}
                    onChange={(e) => setNewPostTitle(e.target.value)}
                    className="bg-slate-50 dark:bg-slate-955 border border-slate-200 dark:border-slate-800 rounded-xl p-2.5 text-xs text-slate-850 dark:text-slate-100 focus:outline-none"
                  />
                  <textarea
                    placeholder="Type details..."
                    value={newPostContent}
                    onChange={(e) => setNewPostContent(e.target.value)}
                    rows={2}
                    className="bg-slate-50 dark:bg-slate-955 border border-slate-200 dark:border-slate-800 rounded-xl p-2.5 text-xs text-slate-850 dark:text-slate-100 focus:outline-none"
                  />
                  
                  <button
                    onClick={handleCreateForumPost}
                    className="self-end px-4.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl cursor-pointer"
                  >
                    Post Thread (+15 XP)
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* SIDEBAR: Curriculum Navigation checklist */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm flex flex-col gap-4">
            <div>
              <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-400">Class Roadmap</h4>
              <h3 className="text-sm font-black text-slate-800 dark:text-white mt-1 leading-snug">Modules Syllabus</h3>
            </div>

            <div className="flex flex-col gap-3.5 mt-2">
              {curriculum?.sections?.map((section: any, secIdx: number) => (
                <div key={section.id} className="space-y-2.5">
                  <span className="text-10 font-black text-indigo-600 dark:text-indigo-400 block border-b border-slate-100 dark:border-slate-800/40 pb-1.5 uppercase tracking-wide">
                    {section.title}
                  </span>

                  <div className="flex flex-col gap-2.5">
                    {section.lessons?.map((less: any) => {
                      const completed = completedLessonIds.includes(less.id);
                      const isLocked = less.is_locked;
                      const active = currentLesson.id === less.id;

                      return (
                        <button
                          key={less.id}
                          disabled={isLocked && !completed}
                          onClick={() => {
                            setCurrentLesson(less);
                            setQuizSubmitted(false);
                            setQuizAnswers({});
                          }}
                          className={`flex items-center justify-between p-3 rounded-2xl border text-left text-xs transition-all w-full cursor-pointer ${
                            active
                              ? "bg-indigo-50 border-indigo-200 dark:bg-indigo-950/20 dark:border-indigo-800 text-indigo-600 dark:text-indigo-400 font-extrabold"
                              : isLocked && !completed
                                ? "bg-slate-50 dark:bg-slate-950 border-slate-100 dark:border-slate-900 text-slate-400 opacity-60 cursor-not-allowed"
                                : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-350 hover:border-indigo-500/20"
                          }`}
                        >
                          <div className="flex items-center gap-2.5 min-w-0 pr-2">
                            {completed ? (
                              <CheckCircle size={15} className="text-emerald-500 shrink-0" />
                            ) : isLocked ? (
                              <ShieldAlert size={14} className="text-slate-400 shrink-0" />
                            ) : (
                              <Play size={14} className="text-indigo-600 shrink-0" />
                            )}
                            <span className="truncate font-semibold">{less.title}</span>
                          </div>

                          <span className="text-9 font-mono text-slate-450 shrink-0 uppercase tracking-wider font-bold">
                            {less.type === "video" ? "Video" : less.type === "pdf" ? "PDF" : less.type === "quiz" ? "Quiz" : less.type === "written_assessment" ? "Test" : less.type === "ai_interview" ? "AI Room" : less.type}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
