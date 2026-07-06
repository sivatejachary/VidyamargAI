"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import Script from "next/script";
import { apiService } from "@/services/api";
import { useAuthStore } from "@/store/authStore";
import { 
  Play, Pause, BookOpen, Brain, Trash2, ArrowRight, Clock, ShieldAlert, 
  RefreshCw, Upload, Code, CheckCircle, Volume2, VolumeX, Maximize2, 
  Minimize2, Lock, Sparkles, Award, FileText, CheckCircle2, ChevronRight,
  MessageSquare, Loader2, Flame, HelpCircle
} from "lucide-react";
// Removed framer-motion

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

  // Player state sub-tabs
  const [playerTab, setPlayerTab] = useState<"overview" | "notes" | "resources" | "transcript" | "discussion">("overview");

  // Custom Video Player States
  const videoRef = useRef<HTMLVideoElement>(null);
  const playerContainerRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.8);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasStarted, setHasStarted] = useState(false);
  const [isPlayerReady, setIsPlayerReady] = useState(false);

  // YouTube player state refs and helper
  const isYouTube = useMemo(() => {
    return !!(currentLesson?.video_url && (currentLesson.video_url.includes("youtube.com") || currentLesson.video_url.includes("youtu.be")));
  }, [currentLesson?.video_url]);
  const ytPlayerRef = useRef<any>(null);
  const ytIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const ytStartedTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pendingSeekTimeRef = useRef<number | null>(null);

  const pauseActiveVideo = () => {
    if (ytPlayerRef.current && typeof ytPlayerRef.current.pauseVideo === "function") {
      try {
        ytPlayerRef.current.pauseVideo();
      } catch (e) {
        console.error("Error pausing video:", e);
      }
    }
  };

  // Anti-Cheat & Resume Watching states
  const [watchedSegments, setWatchedSegments] = useState<number[]>([]);
  const [hasReportedLoad, setHasReportedLoad] = useState(false);
  const [loadStartTime] = useState(Date.now());
  const [bufferCount, setBufferCount] = useState(0);
  const [bufferStartTime, setBufferStartTime] = useState<number | null>(null);
  const [bufferDuration, setBufferDuration] = useState(0);
  const [failures, setFailures] = useState(0);

  // Auto-save feedback indicators
  const [isSavingNotes, setIsSavingNotes] = useState(false);
  const [notesStatus, setNotesStatus] = useState<"Saved" | "Saving..." | "">("Saved");

  // Countdown Next Lesson states
  const [autoNextCount, setAutoNextCount] = useState<number | null>(null);
  const autoNextTimerRef = useRef<NodeJS.Timeout | null>(null);
  const [isNextUnlocked, setIsNextUnlocked] = useState(false);

  // Gamification stats
  const [userStats, setUserStats] = useState({ xp: 0, badges: [] as string[], streak: 0 });
  const [showSuccessOverlay, setShowSuccessOverlay] = useState(false);
  const [xpEarnedAlert, setXpEarnedAlert] = useState<number | null>(null);
  const [badgeAlert, setBadgeAlert] = useState<string | null>(null);

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

  // Capstone Assignments
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
  const [newPostCategory, setNewPostCategory] = useState("General");

  // Redesign Layout and state variables
  const [expandedModules, setExpandedModules] = useState<string[]>([]);

  // AI Mentor Sidebar Chat Widget States
  const [mentorSessionId, setMentorSessionId] = useState<string | null>(null);
  const [mentorMessages, setMentorMessages] = useState<any[]>([]);
  const [mentorInput, setMentorInput] = useState("");
  const [loadingMentor, setLoadingMentor] = useState(false);

  // Collapse/Expand Module helper
  const toggleModule = (modId: string) => {
    setExpandedModules((prev: string[]) => 
      prev.includes(modId) ? prev.filter(id => id !== modId) : [...prev, modId]
    );
  };

  // Auto-expand current active lesson's module
  useEffect(() => {
    if (currentLesson && curriculum?.sections) {
      const activeSection = curriculum.sections.find((sec: any) => 
        sec.lessons?.some((less: any) => less.id === currentLesson.id)
      );
      if (activeSection && !expandedModules.includes(activeSection.id)) {
        setExpandedModules((prev: string[]) => [...prev, activeSection.id]);
      }
    }
  }, [currentLesson, curriculum]);

  // Load AI Mentor Session and initial messages
  useEffect(() => {
    const initMentorSession = async () => {
      try {
        const sessions = await apiService.getAIMentorSessions();
        if (sessions && sessions.length > 0) {
          // Use the most recent session
          setMentorSessionId(sessions[0].id);
          const msgs = await apiService.getAIMentorMessages(sessions[0].id);
          setMentorMessages(msgs || []);
        } else {
          const newSession = await apiService.createAIMentorSession("Skill Lab Quick Chat");
          setMentorSessionId(newSession.id);
        }
      } catch (err) {
        console.error("Failed to init AI Mentor sidebar:", err);
      }
    };
    initMentorSession();
  }, []);

  const handleSendMentorMessage = async (textToSend: string) => {
    if (!textToSend.trim() || !mentorSessionId || loadingMentor) return;
    
    // Add user message locally
    const userMsg = {
      id: Math.random().toString(),
      sender: "user",
      message: textToSend,
      created_at: new Date().toISOString()
    };
    setMentorMessages(prev => [...prev, userMsg]);
    setMentorInput("");
    setLoadingMentor(true);

    try {
      const res = await apiService.sendAIMentorChat(mentorSessionId, textToSend, "tutor");
      if (res) {
        const msgs = await apiService.getAIMentorMessages(mentorSessionId);
        setMentorMessages(msgs || []);
      }
    } catch (err) {
      console.error("Failed to send AI Mentor message:", err);
      setMentorMessages(prev => [...prev, {
        id: Math.random().toString(),
        sender: "assistant",
        message: "I am having trouble connecting to the network. Please check your connection and try again.",
        created_at: new Date().toISOString()
      }]);
    } finally {
      setLoadingMentor(false);
    }
  };

  const handleAIClick = (toolName: string) => {
    let prompt = "";
    if (toolName === "Explain Like I'm 10") {
      prompt = `Explain the concept of "${currentLesson.title}" like I am 10 years old. Keep it simple and use analogies.`;
    } else if (toolName === "AI Summary") {
      prompt = `Provide a clear, structured summary of the key takeaways from "${currentLesson.title}".`;
    } else if (toolName === "Generate Quiz") {
      prompt = `Generate a short 3-question multiple-choice quiz about "${currentLesson.title}" to test my understanding.`;
    } else if (toolName === "Code Playground") {
      prompt = `Show me a practical, copy-pasteable code example illustrating "${currentLesson.title}".`;
    } else if (toolName === "Flashcards") {
      prompt = `Create 3 flashcards (questions and answers) that cover the core terms/definitions in "${currentLesson.title}".`;
    } else if (toolName === "Interview Q&A") {
      prompt = `What are 3 typical technical interview questions and answers related to "${currentLesson.title}"?`;
    } else if (toolName === "Career Tips") {
      prompt = `How is the knowledge of "${currentLesson.title}" applied in real-world jobs/projects?`;
    }

    if (prompt) {
      handleSendMentorMessage(prompt);
    }
  };

  const togglePlaybackRate = () => {
    const nextSpeed = playbackRate === 1.0 ? 1.25 : playbackRate === 1.25 ? 1.5 : playbackRate === 1.5 ? 2.0 : 1.0;
    setPlaybackRate(nextSpeed);
    if (isYouTube && ytPlayerRef.current && typeof ytPlayerRef.current.setPlaybackRate === "function") {
      ytPlayerRef.current.setPlaybackRate(nextSpeed);
    } else if (videoRef.current) {
      videoRef.current.playbackRate = nextSpeed;
    }
  };

  // Fetch flat lessons syllabus list
  const flatLessons = useMemo(() => {
    const flat: any[] = [];
    curriculum?.sections?.forEach((sec: any) => {
      sec.lessons?.forEach((les: any) => {
        flat.push(les);
      });
    });
    return flat;
  }, [curriculum]);

  // Find next lesson object
  const nextLesson = useMemo(() => {
    if (!currentLesson || flatLessons.length === 0) return null;
    const idx = flatLessons.findIndex(l => l.id === currentLesson.id);
    if (idx !== -1 && idx < flatLessons.length - 1) {
      return flatLessons[idx + 1];
    }
    return null;
  }, [currentLesson, flatLessons]);

  // Load User Stats & Resume playback position
  useEffect(() => {
    if (!currentLesson) return;
    const loadPlayerStats = async () => {
      try {
        const stats = await apiService.getUserStats();
        setUserStats(stats);
      } catch (err) {
        console.error("Failed to load user stats", err);
      }
    };
    loadPlayerStats();
  }, [currentLesson]);

  // Handle switching active lesson & prefetching/resuming
  useEffect(() => {
    if (!currentLesson) return;
    setVideoError(null);
    setIsLoading(true);
    setIsPlaying(false);
    setHasStarted(false);
    setCurrentTime(0);
    setIsNextUnlocked(false);
    setWatchedSegments([]);
    setHasReportedLoad(false);
    setBufferCount(0);
    setBufferDuration(0);
    setQuizSubmitted(false);
    setQuizAnswers({});
    setInterviewStarted(false);
    setInterviewResult(null);
    setCurrentInterviewQuestionIdx(0);
    setInterviewTranscript([]);

    if (autoNextTimerRef.current) {
      clearInterval(autoNextTimerRef.current);
      autoNextTimerRef.current = null;
    }
    setAutoNextCount(null);

    if (ytStartedTimeoutRef.current) {
      clearTimeout(ytStartedTimeoutRef.current);
      ytStartedTimeoutRef.current = null;
    }

    // Smart Prefetch: Preload metadata for the next lesson
    if (nextLesson) {
      console.log(`Smart Prefetching next lesson: ${nextLesson.title}`);
      if (nextLesson.type === "video" && nextLesson.video_url) {
        const link = document.createElement("link");
        link.rel = "prefetch";
        link.href = nextLesson.video_url;
        document.head.appendChild(link);
      }
    }

    // Load Note drafts
    const cachedNotes = localStorage.getItem(`notes:lesson:${currentLesson.id}`);
    setNotepadText(cachedNotes || "");

    // Track event: LESSON OPENED
    apiService.saveLearningEvent({
      eventType: currentLesson.type === "pdf" ? "PDF_OPENED" : currentLesson.type === "quiz" ? "QUIZ_STARTED" : "VIDEO_STARTED",
      lessonId: currentLesson.id
    }).catch(err => console.error("Event error:", err));

    // For PDFs: Automatically complete PDF on open
    if (currentLesson.type === "pdf") {
      const triggerPdfComplete = async () => {
        try {
          if (!completedLessonIds.includes(currentLesson.id)) {
            const res = await apiService.completePdf(currentLesson.id);
            setCompletedLessonIds([...completedLessonIds, currentLesson.id]);
            await fetchCurriculum(selectedCourse.id, currentLesson.id);
            await loadEnrollments();
            await loadData();
            
            // Event Tracking & Gamification
            apiService.saveLearningEvent({ eventType: "PDF_COMPLETED", lessonId: currentLesson.id });
            setXpEarnedAlert(25);
            setShowSuccessOverlay(true);
            setTimeout(() => setShowSuccessOverlay(false), 3000);
          }
        } catch (e) {
          console.error("PDF Auto-Complete error:", e);
        }
      };
      triggerPdfComplete();
    }

    // Resume video playback position
    if (currentLesson.type === "video") {
      const loadResumeState = async () => {
        try {
          const res = await apiService.getResumeLearning(selectedCourse.id);
          let targetTime = 0;
          if (res && res.lessonId === currentLesson.id && res.playbackPosition > 0) {
            targetTime = res.playbackPosition;
          } else {
            const cached = localStorage.getItem(`resume:lesson:${currentLesson.id}`);
            if (cached) targetTime = parseFloat(cached);
          }
          
          if (targetTime > 0) {
            if (isYouTube) {
              if (ytPlayerRef.current && typeof ytPlayerRef.current.seekTo === "function" && isPlayerReady) {
                ytPlayerRef.current.seekTo(targetTime, true);
              } else {
                pendingSeekTimeRef.current = targetTime;
              }
            } else if (videoRef.current) {
              videoRef.current.currentTime = targetTime;
            }
          }
        } catch (e) {
          console.error("Resume playback error:", e);
        }
      };
      // Short timeout to ensure video element is bound
      setTimeout(loadResumeState, 300);
    }
  }, [currentLesson?.id]);

  // Manage YouTube Player API and segment tracking
  useEffect(() => {
    if (!isYouTube) {
      setIsPlayerReady(false);
      if (ytIntervalRef.current) {
        clearInterval(ytIntervalRef.current);
        ytIntervalRef.current = null;
      }
      if (ytPlayerRef.current) {
        try {
          if (typeof ytPlayerRef.current.destroy === "function") {
            ytPlayerRef.current.destroy();
          }
        } catch (e) {
          console.error("Error destroying YT player:", e);
        }
        ytPlayerRef.current = null;
      }
      return;
    }

    setIsLoading(true);
    setIsPlaying(false);
    setVideoError(null);

    let checkInterval: NodeJS.Timeout | null = null;
    let initialized = false;

    const initializeYTPlayer = () => {
      if (initialized) return;
      if ((window as any).YT && (window as any).YT.Player) {
        initialized = true;
        if (checkInterval) clearInterval(checkInterval);
        
        const videoId = extractYouTubeId(currentLesson?.video_url || "", selectedCourse?.id, currentLesson?.id);
        if (!videoId) {
          setVideoError("Invalid YouTube URL");
          setIsLoading(false);
          return;
        }

        try {
          ytPlayerRef.current = new (window as any).YT.Player('youtube-player', {
            videoId: videoId,
            playerVars: {
              autoplay: 0,
              controls: 0,
              disablekb: 1,
              fs: 0,
              iv_load_policy: 3,
              modestbranding: 1,
              rel: 0,
              showinfo: 0,
              origin: typeof window !== "undefined" ? window.location.origin : "",
            },
            events: {
              onReady: (event: any) => {
                setDuration(event.target.getDuration());
                setIsLoading(false);
                setIsPlayerReady(true);
                if (pendingSeekTimeRef.current !== null) {
                  event.target.seekTo(pendingSeekTimeRef.current, true);
                  pendingSeekTimeRef.current = null;
                }
              },
              onStateChange: (event: any) => {
                const state = event.data;
                // state 5 = CUED, state 1 = PLAYING, state 2 = PAUSED, state 0 = ENDED
                if (state === 5) {
                  setDuration(event.target.getDuration());
                  setIsLoading(false);
                }
                
                if (state === 1) {
                  setIsPlaying(true);
                  setIsLoading(false);
                  if (ytStartedTimeoutRef.current) {
                    clearTimeout(ytStartedTimeoutRef.current);
                  }
                  ytStartedTimeoutRef.current = setTimeout(() => {
                    setHasStarted(true);
                    ytStartedTimeoutRef.current = null;
                  }, 600);
                  if (!ytIntervalRef.current) {
                    ytIntervalRef.current = setInterval(() => {
                      if (ytPlayerRef.current && ytPlayerRef.current.getCurrentTime) {
                        const currTime = ytPlayerRef.current.getCurrentTime();
                        setCurrentTime(currTime);
                        updateWatchedSegments(currTime);

                        const dur = ytPlayerRef.current.getDuration();
                        if (dur > 0) {
                          // Save position dynamically every 5 seconds
                          const roundedTime = Math.round(currTime);
                          if (roundedTime > 0 && roundedTime % 5 === 0) {
                            localStorage.setItem(`resume:lesson:${currentLesson.id}`, currTime.toString());
                            const totalSegs = Math.ceil(dur / 5);
                            const uniquePct = totalSegs > 0 ? (watchedSegments.length / totalSegs) * 100 : 0;
                            apiService.saveResumeLearning({
                              courseId: selectedCourse.id,
                              lessonId: currentLesson.id,
                              playbackPosition: currTime,
                              watchedSegments: watchedSegments,
                              completion: Math.round(uniquePct)
                            }).catch(err => console.error("Auto-save position error:", err));
                          }

                          if (dur > 15) {
                            if (currTime >= dur - 15) {
                              setIsNextUnlocked(true);
                            }
                          } else {
                            if (currTime / dur >= 0.95) {
                              setIsNextUnlocked(true);
                            }
                          }
                        }
                      }
                    }, 1000);
                  }
                } else if (state === 0) {
                  // Ended
                  setIsPlaying(false);
                  if (ytStartedTimeoutRef.current) {
                    clearTimeout(ytStartedTimeoutRef.current);
                    ytStartedTimeoutRef.current = null;
                  }
                  if (ytIntervalRef.current) {
                    clearInterval(ytIntervalRef.current);
                    ytIntervalRef.current = null;
                  }
                  triggerLessonCompletion();
                } else if (state === 2) {
                  // Paused
                  setIsPlaying(false);
                  if (ytStartedTimeoutRef.current) {
                    clearTimeout(ytStartedTimeoutRef.current);
                    ytStartedTimeoutRef.current = null;
                  }
                  if (ytIntervalRef.current) {
                    clearInterval(ytIntervalRef.current);
                    ytIntervalRef.current = null;
                  }
                }
              },
              onError: (event: any) => {
                console.error("YouTube Player error:", event.data);
                setVideoError(`Unable to load YouTube video (Error: ${event.data})`);
                setIsLoading(false);
              }
            }
          });
        } catch (e) {
          console.error("Error creating YT.Player:", e);
          setVideoError("Unable to initialize video player");
          setIsLoading(false);
        }
      }
    };

    // Load YouTube iframe API statically in the JSX return using next/script.
    const previousCallback = (window as any).onYouTubeIframeAPIReady;
    (window as any).onYouTubeIframeAPIReady = () => {
      if (previousCallback) previousCallback();
      initializeYTPlayer();
    };

    checkInterval = setInterval(initializeYTPlayer, 200);

    return () => {
      setIsPlayerReady(false);
      if (checkInterval) clearInterval(checkInterval);
      if (ytIntervalRef.current) clearInterval(ytIntervalRef.current);
      if (ytStartedTimeoutRef.current) clearTimeout(ytStartedTimeoutRef.current);
      if (ytPlayerRef.current) {
        try {
          if (typeof ytPlayerRef.current.destroy === "function") {
            ytPlayerRef.current.destroy();
          }
        } catch (e) {}
        ytPlayerRef.current = null;
      }
    };
  }, [isYouTube]);

  // Load new video when lesson changes
  useEffect(() => {
    if (!isYouTube || !isPlayerReady || !ytPlayerRef.current) return;

    const videoId = extractYouTubeId(currentLesson?.video_url || "", selectedCourse?.id, currentLesson?.id);
    if (!videoId) {
      setVideoError("Invalid YouTube URL");
      return;
    }

    setIsLoading(true);
    setIsPlaying(false);
    setVideoError(null);
    setHasStarted(false);
    setCurrentTime(0);

    try {
      if (typeof ytPlayerRef.current.cueVideoById === "function") {
        ytPlayerRef.current.cueVideoById({ videoId: videoId });
      } else {
        setIsPlayerReady(false);
      }
    } catch (e) {
      console.error("Error loading video in existing player:", e);
      setVideoError("Unable to load YouTube video");
      setIsLoading(false);
    }
  }, [currentLesson?.id, isPlayerReady, isYouTube]);

  // Auto-Save notes every 3 seconds if modified
  useEffect(() => {
    if (!currentLesson || !notepadText) return;
    setNotesStatus("Saving...");
    const timer = setTimeout(async () => {
      localStorage.setItem(`notes:lesson:${currentLesson.id}`, notepadText);
      setNotesStatus("Saved");
    }, 3000);
    return () => clearTimeout(timer);
  }, [notepadText, currentLesson?.id]);

  // Track unique video segments for Anti-Cheat
  const updateWatchedSegments = (time: number) => {
    if (!duration) return;
    const segmentIndex = Math.floor(time / 5); // 5-second unique buckets
    if (!watchedSegments.includes(segmentIndex)) {
      setWatchedSegments(prev => {
        const next = [...prev, segmentIndex];
        const totalSegs = Math.ceil(duration / 5);
        const uniquePct = totalSegs > 0 ? (next.length / totalSegs) * 100 : 0;

        // Save progress details locally
        localStorage.setItem(`progress:lesson:${currentLesson.id}`, JSON.stringify({
          lessonId: currentLesson.id,
          watchedSegments: next,
          completion: Math.round(uniquePct)
        }));

        return next;
      });
    }
  };

  // Video Events
  const handleCanPlay = () => {
    setIsLoading(false);
    if (!hasReportedLoad) {
      setHasReportedLoad(true);
      const loadTime = Date.now() - loadStartTime;
      apiService.saveVideoAnalytics({
        lessonId: currentLesson.id,
        loadTime: loadTime,
        bufferCount: bufferCount,
        bufferDuration: bufferDuration,
        playbackFailures: failures,
        device: typeof window !== "undefined" && window.innerWidth < 768 ? "Mobile" : "Desktop",
        browser: typeof navigator !== "undefined" ? navigator.userAgent.split(" ").slice(-1)[0] : "Chrome"
      }).catch(err => console.error(err));
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      const time = videoRef.current.currentTime;
      setCurrentTime(time);
      updateWatchedSegments(time);

      // Save playback position locally and in Redis every 5 seconds
      if (Math.round(time) % 5 === 0 && isPlaying) {
        localStorage.setItem(`resume:lesson:${currentLesson.id}`, time.toString());
        const totalSegs = Math.ceil(duration / 5);
        const uniquePct = totalSegs > 0 ? (watchedSegments.length / totalSegs) * 100 : 0;
        
        apiService.saveResumeLearning({
          courseId: selectedCourse.id,
          lessonId: currentLesson.id,
          playbackPosition: time,
          watchedSegments: watchedSegments,
          completion: Math.round(uniquePct)
        }).catch(err => console.error("Auto-save position error:", err));
      }

      // Check for Next button unlock (15 seconds before the end of the video)
      if (duration > 0) {
        if (duration > 15) {
          if (time >= duration - 15) {
            setIsNextUnlocked(true);
          }
        } else {
          if (time / duration >= 0.95) {
            setIsNextUnlocked(true);
          }
        }
      }
    }
  };

  const triggerLessonCompletion = async () => {
    try {
      setIsPlaying(false);
      if (videoRef.current) videoRef.current.pause();

      await apiService.completeLesson(currentLesson.id);
      setCompletedLessonIds([...completedLessonIds, currentLesson.id]);
      await fetchCurriculum(selectedCourse.id, currentLesson.id);
      await loadEnrollments();
      await loadData();

      // Track Event
      apiService.saveLearningEvent({ eventType: "VIDEO_COMPLETED", lessonId: currentLesson.id });

      // Trigger XP & success rewards animation
      setXpEarnedAlert(25);
      setShowSuccessOverlay(true);
      setTimeout(() => {
        setShowSuccessOverlay(false);
        // Start Auto-Next Lesson Countdown
        if (nextLesson) {
          startAutoNextCountdown();
        }
      }, 3000);
    } catch (e) {
      console.error(e);
    }
  };

  const startAutoNextCountdown = () => {
    setAutoNextCount(5);
    autoNextTimerRef.current = setInterval(() => {
      setAutoNextCount(prev => {
        if (prev === null) return null;
        if (prev <= 1) {
          clearInterval(autoNextTimerRef.current!);
          autoNextTimerRef.current = null;
          setCurrentLesson(nextLesson);
          return null;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const cancelAutoNext = () => {
    if (autoNextTimerRef.current) {
      clearInterval(autoNextTimerRef.current);
      autoNextTimerRef.current = null;
    }
    setAutoNextCount(null);
  };

  // Video control triggers
  const togglePlay = () => {
    if (isYouTube && ytPlayerRef.current) {
      if (isPlaying) {
        ytPlayerRef.current.pauseVideo();
        setIsPlaying(false);
        if (ytStartedTimeoutRef.current) {
          clearTimeout(ytStartedTimeoutRef.current);
          ytStartedTimeoutRef.current = null;
        }
      } else {
        ytPlayerRef.current.playVideo();
        setIsPlaying(true);
      }
    } else if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
        setIsPlaying(false);
      } else {
        videoRef.current.play().catch(e => {
          console.error("Playback failed:", e);
          setVideoError("Autoplay blocked or load failed.");
        });
        setIsPlaying(true);
        setHasStarted(true);
      }
    }
  };

  const handleSeekChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    const isCompleted = completedLessonIds.includes(currentLesson?.id);
    if (val > currentTime && !isCompleted) {
      console.warn("Seeking forward is disabled for uncompleted videos");
      return;
    }
    setCurrentTime(val);
    if (isYouTube && ytPlayerRef.current) {
      ytPlayerRef.current.seekTo(val, true);
    } else if (videoRef.current) {
      videoRef.current.currentTime = val;
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setVolume(val);
    setIsMuted(val === 0);
    if (isYouTube && ytPlayerRef.current) {
      ytPlayerRef.current.setVolume(val * 100);
      ytPlayerRef.current.setMuted(val === 0);
    } else if (videoRef.current) {
      videoRef.current.volume = val;
      videoRef.current.muted = val === 0;
    }
  };

  const toggleMute = () => {
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    if (isYouTube && ytPlayerRef.current) {
      ytPlayerRef.current.setMuted(nextMuted);
    } else if (videoRef.current) {
      videoRef.current.muted = nextMuted;
    }
  };

  const handleSpeedChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const speed = parseFloat(e.target.value);
    setPlaybackRate(speed);
    if (isYouTube && ytPlayerRef.current) {
      ytPlayerRef.current.setPlaybackRate(speed);
    } else if (videoRef.current) {
      videoRef.current.playbackRate = speed;
    }
  };

  const toggleFullscreen = () => {
    if (!playerContainerRef.current) return;
    if (!isFullscreen) {
      if (playerContainerRef.current.requestFullscreen) {
        playerContainerRef.current.requestFullscreen();
      }
      setIsFullscreen(true);
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
      setIsFullscreen(false);
    }
  };

  const handleError = () => {
    setVideoError("Unable to load lesson video");
    setFailures(prev => prev + 1);
  };

  const handleReloadVideo = () => {
    setVideoError(null);
    setIsLoading(true);
    if (videoRef.current) {
      videoRef.current.load();
    }
  };

  const handleWaiting = () => {
    setBufferCount(prev => prev + 1);
    setBufferStartTime(Date.now());
  };

  const handlePlaying = () => {
    setHasStarted(true);
    if (bufferStartTime) {
      const elapsed = Date.now() - bufferStartTime;
      setBufferDuration(prev => prev + elapsed);
      setBufferStartTime(null);
    }
  };

  // Keyboard controls
  useEffect(() => {
    const handleKeys = (e: KeyboardEvent) => {
      if (!currentLesson || currentLesson.type !== "video") return;
      if (document.activeElement?.tagName === "TEXTAREA" || document.activeElement?.tagName === "INPUT") return;

      if (e.code === "Space") {
        e.preventDefault();
        togglePlay();
      } else if (e.code === "ArrowRight") {
        e.preventDefault();
        console.warn("ArrowRight forward skipping is disabled");
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        console.warn("ArrowLeft backward skipping is disabled");
      } else if (e.code === "ArrowUp" || e.code === "ArrowDown" || e.code === "KeyF") {
        e.preventDefault();
        console.warn("Keyboard shortcut is disabled");
      }
    };

    window.addEventListener("keydown", handleKeys);
    return () => window.removeEventListener("keydown", handleKeys);
  }, [isPlaying, currentTime, duration, currentLesson, isYouTube]);

  // Speech Assessors
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
      try { recognitionRef.current.stop(); } catch (e) {}
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
        setCandidateInterviewResponse(prev => prev + (prev.endsWith(" ") || !prev ? "" : " ") + finalTranscript);
      }
    };

    rec.onerror = (e: any) => console.error(e);
    rec.onend = () => setIsRecording(false);

    recognitionRef.current = rec;
    rec.start();
  };

  const stopSpeechRecognition = () => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) {}
    }
    setIsRecording(false);
    setAiVoiceState("idle");
  };

  const handleAdvanceQuestion = async () => {
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
      setTimeout(() => speakQuestion(nextQuestion), 500);
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
      
      apiService.saveLearningEvent({ eventType: "INTERVIEW_COMPLETED", lessonId: currentLesson.id });
      setXpEarnedAlert(100);
      setShowSuccessOverlay(true);
      setTimeout(() => setShowSuccessOverlay(false), 3000);
    } catch (err) {
      console.error(err);
      setAiVoiceState("idle");
    } finally {
      setSubmittingInterview(false);
    }
  };

  // Discussions Forum Helper
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

  // Course Progress Percentages
  const courseProgressPercent = useMemo(() => {
    if (!curriculum) return 0;
    return Math.round(curriculum.progress || 0);
  }, [curriculum]);

  const moduleProgressPercent = useMemo(() => {
    if (!curriculum?.sections || !currentLesson) return 0;
    const activeSection = curriculum.sections.find((s: any) => 
      s.lessons?.some((l: any) => l.id === currentLesson.id)
    );
    if (!activeSection) return 0;
    const total = activeSection.lessons?.length || 1;
    const done = activeSection.lessons?.filter((l: any) => completedLessonIds.includes(l.id)).length || 0;
    return Math.round((done / total) * 100);
  }, [curriculum, currentLesson, completedLessonIds]);

  const activeModuleTitle = useMemo(() => {
    if (!curriculum?.sections || !currentLesson) return "";
    const activeSection = curriculum.sections.find((s: any) => 
      s.lessons?.some((l: any) => l.id === currentLesson.id)
    );
    return activeSection ? activeSection.title : "";
  }, [curriculum, currentLesson]);

  const activeModuleGoal = useMemo(() => {
    if (!curriculum?.sections || !currentLesson) return "";
    const activeSection = curriculum.sections.find((s: any) => 
      s.lessons?.some((l: any) => l.id === currentLesson.id)
    );
    return activeSection ? activeSection.goal : "";
  }, [curriculum, currentLesson]);

  const formatTime = (seconds: number) => {
    if (isNaN(seconds)) return "00:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  if (loadingCurriculum || !currentLesson || !curriculum) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <div className="w-12 h-12 rounded-full border-4 border-indigo-600 border-t-transparent animate-spin" />
        <p className="text-xs text-muted-foreground font-semibold text-slate-500">Loading course curriculum...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full px-4 md:px-8 py-6 bg-slate-50 dark:bg-slate-955 text-slate-855 dark:text-slate-100">
      
      {/* Dynamic Success Overlay */}
      {showSuccessOverlay && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-md transition-all duration-300"
        >
          <div className="bg-gradient-to-br from-indigo-900 to-slate-900 border border-indigo-500/30 rounded-3xl p-8 max-w-md text-center shadow-2xl flex flex-col items-center gap-4">
            <div className="w-20 h-20 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center animate-bounce shadow-inner">
              <Award size={40} />
            </div>
            <h3 className="text-xl font-black text-white">Lesson Completed!</h3>
            <p className="text-xs text-slate-355 leading-relaxed">
              You've successfully validated this lesson with strict watch compliance.
            </p>
            <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 px-4 py-2 rounded-xl text-emerald-405 font-extrabold text-sm">
              <Sparkles size={16} />
              <span>+{xpEarnedAlert} XP Earned</span>
            </div>
          </div>
        </div>
      )}

      {/* Top Header & Breadcrumbs Area */}
      <div className="flex flex-col gap-4">
        {/* Breadcrumbs */}
        <div className="flex items-center gap-2 text-[11px] font-bold text-slate-500 dark:text-slate-455 uppercase tracking-wider">
          <button onClick={() => setActiveView("explore")} className="hover:text-indigo-655 transition-colors cursor-pointer">My Learning</button>
          <span>/</span>
          <span className="truncate max-w-[150px]">{selectedCourse.title}</span>
          <span>/</span>
          <span className="text-indigo-600 dark:text-indigo-400 truncate max-w-[150px]">{activeModuleTitle}</span>
        </div>

        {/* Course Header Card */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-5 md:p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="flex items-center gap-5">
            <div className="w-16 h-16 rounded-2xl bg-indigo-50 dark:bg-indigo-955/40 text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-800/40 flex items-center justify-center text-3xl font-black shadow-inner shrink-0">
              {selectedCourse.title?.toUpperCase().includes("HTML") ? "5" : "D"}
            </div>
            <div className="space-y-1">
              <h2 className="text-xl font-black text-slate-855 dark:text-white leading-tight">{selectedCourse.title}</h2>
              <div className="flex flex-wrap items-center gap-2 text-[10px] font-extrabold tracking-wide uppercase">
                <span className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 px-2 py-0.5 rounded-md">Beginner</span>
                <span className="text-slate-400">•</span>
                <span className="text-slate-500 dark:text-slate-455">{curriculum?.sections?.length || 0} Modules</span>
                <span className="text-slate-400">•</span>
                <span className="text-slate-500 dark:text-slate-455">4.5 Hrs</span>
                <span className="text-slate-400">•</span>
                <span className="text-slate-500 dark:text-slate-455">Updated Jun 2026</span>
              </div>
            </div>
          </div>
          <button 
            onClick={() => {
              playerContainerRef.current?.scrollIntoView({ behavior: 'smooth' });
            }}
            className="w-full md:w-auto px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-extrabold text-xs rounded-xl shadow-md cursor-pointer transition-all hover:scale-[1.02] flex items-center justify-center gap-2"
          >
            <span>Continue Learning</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start mt-2">
        
        {/* LEFT PLAYER COLUMN (8/12) */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          
          {/* Lesson Title & Video Player Area */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-5 md:p-6 shadow-sm flex flex-col gap-4">
            
            {/* Title Header Row */}
            <div className="flex justify-between items-start gap-4">
              <div className="space-y-1">
                <div className="text-[10px] font-black uppercase text-indigo-600 dark:text-indigo-400 tracking-wider">
                  {activeModuleTitle.split(":")[0]} • Lesson {1 + (curriculum.sections?.flatMap((s: any) => s.lessons || []).findIndex((l: any) => l.id === currentLesson.id) || 0)}
                </div>
                <h3 className="text-base font-black text-slate-855 dark:text-white leading-snug">{currentLesson.title}</h3>
              </div>
              <button 
                onClick={triggerLessonCompletion}
                disabled={completedLessonIds.includes(currentLesson.id)}
                className={`px-4 py-2 rounded-xl text-xs font-black transition-all cursor-pointer shrink-0 border flex items-center gap-1.5 ${
                  completedLessonIds.includes(currentLesson.id)
                    ? "bg-emerald-55 border-emerald-200 text-emerald-600 dark:bg-emerald-950/20 dark:border-emerald-800/40 cursor-not-allowed"
                    : "bg-white border-slate-202 text-slate-705 hover:border-slate-350 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-200"
                }`}
              >
                <CheckCircle size={14} className={completedLessonIds.includes(currentLesson.id) ? "text-emerald-500" : "text-slate-400"} />
                <span>{completedLessonIds.includes(currentLesson.id) ? "Completed" : "Mark as Complete"}</span>
              </button>
            </div>

            {/* Video Player Box */}
            <div 
              ref={playerContainerRef}
              className="relative aspect-video w-full bg-slate-955 rounded-2xl overflow-hidden shadow-md select-none group border border-slate-850"
            >
              {currentLesson.type === "video" ? (
                <>
                  {isYouTube ? (
                    <div className="absolute inset-0 w-full h-full overflow-hidden">
                      <div 
                        id="youtube-player" 
                        className="absolute w-full h-[150%] -top-[25%] left-0 right-0 pointer-events-none"
                      />
                      
                      {!hasStarted && (
                        <div className="absolute inset-0 bg-black z-10 pointer-events-none" />
                      )}

                      <div 
                        onClick={togglePlay}
                        className="absolute inset-0 w-full h-full cursor-pointer z-20 bg-transparent pointer-events-auto"
                      />
                    </div>
                  ) : (
                    <video
                      ref={videoRef}
                      src={currentLesson.video_url || "https://media.w3.org/2010/05/sintel/trailer_hd.mp4"}
                      preload="metadata"
                      onCanPlay={handleCanPlay}
                      onLoadedMetadata={handleLoadedMetadata}
                      onTimeUpdate={handleTimeUpdate}
                      onWaiting={handleWaiting}
                      onPlaying={handlePlaying}
                      onError={handleError}
                      onEnded={triggerLessonCompletion}
                      onClick={togglePlay}
                      className="w-full h-full object-cover cursor-pointer"
                    />
                  )}

                  {isLoading && (
                    <div className="absolute inset-0 bg-slate-955/80 flex flex-col items-center justify-center gap-3 z-40">
                      <RefreshCw className="animate-spin text-indigo-500" size={32} />
                      <span className="text-[10px] text-slate-300 font-bold uppercase tracking-wider">Streaming Video...</span>
                    </div>
                  )}

                  {videoError && (
                    <div className="absolute inset-0 bg-slate-950 flex flex-col items-center justify-center gap-3.5 text-center p-6 z-40">
                      <ShieldAlert size={44} className="text-red-500" />
                      <div>
                        <h4 className="text-sm font-black text-white">{videoError}</h4>
                        <p className="text-[10px] text-slate-455 mt-1 max-w-xs mx-auto leading-normal">
                          {videoError.toLowerCase().includes("youtube") || videoError.toLowerCase().includes("initialize")
                            ? "This can happen in Incognito Mode or if adblockers/privacy shields block YouTube embeds. Please try disabling shields or check your connection."
                            : "There was an issue playing this content. Please check your connection or try again."}
                        </p>
                      </div>
                      <button 
                        onClick={handleReloadVideo}
                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold transition-all shadow-md"
                      >
                        Retry Load
                      </button>
                    </div>
                  )}

                  {!isPlaying && !videoError && !isLoading && (
                    <button 
                      onClick={togglePlay}
                      className="absolute inset-0 flex items-center justify-center bg-black/20 hover:bg-black/35 transition-all cursor-pointer z-30 pointer-events-auto"
                    >
                      <div className="w-16 h-16 rounded-full bg-white/10 hover:bg-white/20 border border-white/30 text-white flex items-center justify-center shadow-lg backdrop-blur-sm transition-transform hover:scale-105">
                        <Play size={24} className="fill-current ml-1" />
                      </div>
                    </button>
                  )}

                  {autoNextCount !== null && (
                    <div className="absolute inset-0 bg-slate-955/95 flex flex-col items-center justify-center gap-5 text-center p-6 z-40">
                      <Sparkles className="text-indigo-400 animate-pulse" size={40} />
                      <div>
                        <h3 className="text-base font-black text-white">Video completed!</h3>
                        <p className="text-xs text-slate-400 mt-1">
                          Up next: <span className="text-indigo-400 font-extrabold">{nextLesson?.title}</span>
                        </p>
                      </div>
                      <div className="text-2xl font-black text-white font-mono bg-indigo-950/40 border border-indigo-900/30 px-5 py-2.5 rounded-2xl">
                        Starting in {autoNextCount}s...
                      </div>
                      <div className="flex gap-3">
                        <button 
                          onClick={() => {
                            cancelAutoNext();
                            if (nextLesson) setCurrentLesson(nextLesson);
                          }}
                          className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-md cursor-pointer"
                        >
                          Open Now
                        </button>
                        <button 
                          onClick={cancelAutoNext}
                          className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-355 text-xs font-bold rounded-xl border border-slate-700 cursor-pointer"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}

                  {!videoError && !isLoading && (
                    <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-slate-955 via-slate-955/60 to-transparent flex flex-col gap-2.5 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity duration-300 z-20">
                      <div className="flex items-center gap-3 w-full">
                        <span className="text-[10px] text-slate-300 font-mono font-bold">{formatTime(currentTime)}</span>
                        <div className="flex-1 h-1 rounded bg-slate-800 relative overflow-hidden select-none pointer-events-none">
                          <div 
                            className="absolute top-0 left-0 h-full bg-indigo-500 transition-all duration-100"
                            style={{ width: `${duration > 0 ? (currentTime / duration) * 100 : 0}%` }}
                          />
                        </div>
                        <span className="text-[10px] text-slate-300 font-mono font-bold">{formatTime(duration)}</span>
                      </div>

                      <div className="flex justify-between items-center w-full">
                        <div className="flex items-center gap-4 text-white">
                          <button onClick={togglePlay} className="hover:text-indigo-400 transition-colors cursor-pointer outline-none">
                            {isPlaying ? <Pause size={15} /> : <Play size={15} />}
                          </button>
                          <button onClick={toggleMute} className="hover:text-indigo-400 transition-colors cursor-pointer outline-none">
                            {isMuted ? <VolumeX size={15} /> : <Volume2 size={15} />}
                          </button>
                          <span className="text-[10px] text-slate-400 font-mono">
                            {playbackRate !== 1 ? `${playbackRate}x` : "Normal"}
                          </span>
                        </div>
                        <div className="flex items-center gap-4 text-white">
                          <button 
                            onClick={togglePlaybackRate} 
                            className="hover:text-indigo-400 transition-colors cursor-pointer outline-none text-[10px] font-bold border border-slate-700 px-1.5 py-0.5 rounded"
                          >
                            Speed
                          </button>
                          <button onClick={toggleFullscreen} className="hover:text-indigo-400 transition-colors cursor-pointer outline-none">
                            <Maximize2 size={15} />
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              ) : currentLesson.type === "pdf" ? (
                <div className="bg-slate-955 p-6 min-h-[350px] flex flex-col justify-between items-center text-center">
                  <div className="my-auto flex flex-col items-center gap-4">
                    <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center">
                      <BookOpen size={32} />
                    </div>
                    <div>
                      <h4 className="text-sm font-black text-white">{currentLesson.title}</h4>
                      <p className="text-[11px] text-slate-455 mt-1.5 max-w-xs mx-auto leading-normal">
                        We have auto-completed this reading workbook for you on load. Click below to download the study guide PDF.
                      </p>
                    </div>
                  </div>
                  <a
                    href={currentLesson.pdf_url}
                    target="_blank"
                    rel="noreferrer"
                    className="px-6 py-2.8 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-black shadow-md cursor-pointer transition-all hover:scale-105"
                  >
                    Download Handbook PDF
                  </a>
                </div>
              ) : currentLesson.type === "quiz" && currentLesson.quiz ? (
                <div className="bg-slate-955 p-6 flex flex-col gap-5 max-h-[480px] overflow-y-auto">
                  {quizSubmitted ? (
                    <div className="my-auto text-center flex flex-col items-center gap-4 py-8">
                      <div className="w-14 h-14 rounded-full bg-emerald-500/10 text-emerald-450 border border-emerald-500/20 flex items-center justify-center text-xl font-bold">
                        ✓
                      </div>
                      <div>
                        <h4 className="text-sm font-black text-white">Quiz Completed!</h4>
                        <p className="text-xs text-slate-400 mt-1">
                          Your Score: <span className="font-extrabold text-emerald-500">{quizScore}%</span>
                        </p>
                      </div>
                      <button
                        onClick={() => {
                          setQuizAnswers({});
                          setQuizSubmitted(false);
                          setQuizScore(null);
                        }}
                        className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-750 text-xs font-bold rounded-xl cursor-pointer"
                      >
                        Retry Quiz
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-5">
                      {currentLesson.quiz.questions.map((q: any, qIdx: number) => (
                        <div key={q.id} className="p-4 bg-slate-900 border border-slate-850 rounded-2xl flex flex-col gap-3">
                          <span className="text-[9px] font-black text-indigo-400 uppercase tracking-widest">Question {qIdx + 1}</span>
                          <span className="text-xs font-bold text-slate-100">{q.question}</span>
                          <div className="grid grid-cols-1 gap-2 mt-1">
                            {q.options?.map((opt: string, optIdx: number) => (
                              <button
                                key={optIdx}
                                onClick={() => setQuizAnswers(prev => ({ ...prev, [qIdx]: optIdx }))}
                                className={`p-3 rounded-xl border text-left text-xs font-semibold transition-all cursor-pointer ${
                                  quizAnswers[qIdx] === optIdx
                                    ? "bg-indigo-950 border-indigo-500 text-indigo-350"
                                    : "bg-slate-955 border-slate-855 text-slate-400 hover:border-slate-700"
                                }`}
                              >
                                {opt}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                      <div className="flex justify-end pt-3">
                        <button
                          onClick={async () => {
                            let correctCount = 0;
                            currentLesson.quiz.questions.forEach((q: any, idx: number) => {
                              const ans = quizAnswers[idx];
                              const correctStr = q.correct_option;
                              const correctIdx = q.options?.indexOf(correctStr);
                              if (ans === correctIdx) correctCount++;
                            });
                            const score = Math.round((correctCount / currentLesson.quiz.questions.length) * 100);
                            setQuizScore(score);
                            setQuizSubmitted(true);
                            try {
                              await apiService.completeLesson(currentLesson.id);
                              setCompletedLessonIds([...completedLessonIds, currentLesson.id]);
                              await fetchCurriculum(selectedCourse.id, currentLesson.id);
                              await loadEnrollments();
                              await loadData();
                              if (score >= 70) {
                                apiService.saveLearningEvent({ eventType: "QUIZ_COMPLETED", lessonId: currentLesson.id });
                                setXpEarnedAlert(50);
                                setShowSuccessOverlay(true);
                                setTimeout(() => setShowSuccessOverlay(false), 3000);
                              }
                            } catch (err) {
                              console.error(err);
                            }
                          }}
                          disabled={Object.keys(quizAnswers).length < currentLesson.quiz.questions.length}
                          className="px-6 py-2.8 bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-slate-800 disabled:text-slate-505 text-xs font-black rounded-xl cursor-pointer disabled:cursor-not-allowed shadow-md"
                        >
                          Submit Answers
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : currentLesson.type === "written_assessment" && currentLesson.written_assessment ? (
                <div className="bg-slate-955 p-6 flex flex-col gap-5 max-h-[480px] overflow-y-auto">
                  {currentLesson.written_assessment.passed ? (
                    <div className="my-auto text-center flex flex-col items-center gap-4 py-8">
                      <div className="w-14 h-14 rounded-full bg-emerald-500/10 text-emerald-455 border border-emerald-500/20 flex items-center justify-center text-xl font-bold">
                        ✓
                      </div>
                      <div>
                        <h4 className="text-sm font-black text-white">Assessment Evaluated!</h4>
                        <p className="text-xs text-slate-400 mt-1">
                          Best Score: <span className="font-extrabold text-emerald-400">{currentLesson.written_assessment.best_score}%</span>
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {currentLesson.written_assessment.questions.map((q: any, qIdx: number) => (
                        <div key={q.id} className="p-4 bg-slate-900 border border-slate-850 rounded-2xl flex flex-col gap-2">
                          <span className="text-[9px] font-black text-indigo-455 uppercase tracking-widest font-mono">Question {qIdx + 1}</span>
                          <span className="text-xs font-bold text-slate-250 leading-relaxed">{q.question_text}</span>
                          <textarea
                            value={writtenAnswers[qIdx] || ""}
                            onChange={(e) => setWrittenAnswers(prev => ({ ...prev, [qIdx]: e.target.value }))}
                            rows={3}
                            placeholder="Write your explanation here..."
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-655 resize-none font-semibold mt-1"
                          />
                        </div>
                      ))}
                      <div className="flex justify-end pt-2">
                        <button
                          onClick={async () => {
                            try {
                              await apiService.completeLesson(currentLesson.id);
                              setCompletedLessonIds([...completedLessonIds, currentLesson.id]);
                              await fetchCurriculum(selectedCourse.id, currentLesson.id);
                              await loadEnrollments();
                              await loadData();
                              setXpEarnedAlert(100);
                              setShowSuccessOverlay(true);
                              setTimeout(() => setShowSuccessOverlay(false), 3000);
                            } catch (err) {
                              console.error(err);
                            }
                          }}
                          className="px-6 py-2.8 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-black rounded-xl cursor-pointer shadow-md"
                        >
                          Submit Response
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>

            {/* Video Sub-Tabs Navigation */}
            <div className="flex gap-5 border-b border-slate-100 dark:border-slate-800/40 pb-2.5 overflow-x-auto scrollbar-hide shrink-0 mt-3">
              {[
                { id: "overview", label: "Overview" },
                { id: "notes", label: "AI Notes" },
                { id: "resources", label: "Resources" },
                { id: "transcript", label: "Transcript" },
                { id: "discussion", label: "Discussion" }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setPlayerTab(tab.id as any)}
                  className={`text-xs font-bold pb-1.5 transition-all border-b-2 cursor-pointer ${
                    playerTab === tab.id
                      ? "border-indigo-600 text-indigo-600 dark:border-indigo-405 dark:text-indigo-405 font-extrabold"
                      : "border-transparent text-slate-500 hover:text-slate-850 dark:hover:text-white"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Video Sub-Tabs Content */}
            <div className="mt-2 min-h-[220px]">
              {playerTab === "overview" && (
                <div className="space-y-5">
                  <div className="text-xs leading-relaxed text-slate-600 dark:text-slate-405">
                    <h4 className="text-slate-855 dark:text-white font-bold text-xs mb-1.5">About this lesson</h4>
                    <p className="font-semibold">
                      {currentLesson.description || "Learn the concepts of HTML5 Development. This lesson goes through basic syntax, configurations, and core workflows inside candidates' skill labs."}
                    </p>
                  </div>

                  {/* Metadata Stats Grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-slate-50 dark:bg-slate-900/60 border border-slate-100 dark:border-slate-855 p-3 rounded-2xl flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-650 dark:text-indigo-400 flex items-center justify-center shrink-0">
                        <Clock size={16} />
                      </div>
                      <div>
                        <div className="text-[9px] text-slate-400 uppercase font-mono font-bold">Duration</div>
                        <div className="text-xs font-extrabold text-slate-800 dark:text-slate-200">{currentLesson.duration || "10 min"}</div>
                      </div>
                    </div>

                    <div className="bg-slate-50 dark:bg-slate-900/60 border border-slate-100 dark:border-slate-855 p-3 rounded-2xl flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-650 dark:text-indigo-400 flex items-center justify-center shrink-0">
                        <FileText size={16} />
                      </div>
                      <div>
                        <div className="text-[9px] text-slate-400 uppercase font-mono font-bold">Type</div>
                        <div className="text-xs font-extrabold text-slate-800 dark:text-slate-205">Video Lesson</div>
                      </div>
                    </div>

                    <div className="bg-slate-50 dark:bg-slate-900/60 border border-slate-100 dark:border-slate-855 p-3 rounded-2xl flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-650 dark:text-indigo-400 flex items-center justify-center shrink-0">
                        <Award size={16} />
                      </div>
                      <div>
                        <div className="text-[9px] text-slate-400 uppercase font-mono font-bold">Difficulty</div>
                        <div className="text-xs font-extrabold text-slate-800 dark:text-slate-200">Easy</div>
                      </div>
                    </div>

                    <div className="bg-slate-50 dark:bg-slate-900/60 border border-slate-100 dark:border-slate-855 p-3 rounded-2xl flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-650 dark:text-indigo-400 flex items-center justify-center shrink-0">
                        <ChevronRight size={16} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="text-[9px] text-slate-400 uppercase font-mono font-bold">Next Up</div>
                        <div className="text-xs font-extrabold text-slate-800 dark:text-slate-200 truncate pr-1">
                          {nextLesson?.title || "End of course"}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Checklist & AI Summary grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2">
                    <div className="space-y-3">
                      <h4 className="text-slate-850 dark:text-white font-bold text-xs">What you'll learn</h4>
                      <div className="flex flex-col gap-2">
                        {[
                          "Fundamental structures & tags",
                          "Working with browser viewports",
                          "Hands-on workspace playgrounds",
                          "Validating HTML5 markup standards"
                        ].map((item, idx) => (
                          <div key={idx} className="flex items-center gap-2 text-xs font-bold text-slate-600 dark:text-slate-405">
                            <CheckCircle2 size={14} className="text-indigo-600 dark:text-indigo-400 shrink-0" />
                            <span>{item}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="bg-indigo-50/40 dark:bg-indigo-950/10 border border-indigo-100/50 dark:border-indigo-900/20 p-4 rounded-2xl flex flex-col justify-between gap-3">
                      <div>
                        <h4 className="text-indigo-955 dark:text-indigo-400 font-bold text-xs flex items-center gap-1.5">
                          <Sparkles size={14} />
                          <span>AI Summary</span>
                        </h4>
                        <p className="text-[11px] text-indigo-905/70 dark:text-slate-400 leading-normal mt-1.5 font-bold">
                          Get an instantaneous AI summary of this lesson context including code playground references.
                        </p>
                      </div>
                      <button 
                        onClick={() => handleAIClick("AI Summary")}
                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-sm cursor-pointer transition-all hover:scale-[1.01]"
                      >
                        Generate Summary
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {playerTab === "notes" && (
                <div className="space-y-4">
                  <h4 className="text-slate-850 dark:text-white font-bold text-xs">Interactive Notebook</h4>
                  <textarea
                    value={notepadText}
                    onChange={(e) => setNotepadText(e.target.value)}
                    rows={4}
                    placeholder="Capture your class notes here. Notes are saved to your candidate dashboard..."
                    className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-202 dark:border-slate-855 rounded-xl p-3 text-xs text-slate-800 dark:text-slate-205 focus:outline-none focus:border-indigo-650 resize-y font-semibold"
                  />
                  <div className="flex justify-end gap-3">
                    <button
                      onClick={() => setNotepadText("")}
                      className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-355 text-xs font-bold rounded-xl cursor-pointer"
                    >
                      Clear
                    </button>
                    <button
                      onClick={() => {
                        if (notepadText.trim()) {
                          setSavedNotes([...savedNotes, notepadText]);
                          setNotepadText("");
                        }
                      }}
                      className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-sm cursor-pointer"
                    >
                      Save Note
                    </button>
                  </div>
                  {savedNotes.length > 0 && (
                    <div className="pt-3 border-t border-slate-100 dark:border-slate-850 space-y-2">
                      <span className="text-[10px] text-slate-400 font-bold uppercase font-mono">Saved Notes</span>
                      {savedNotes.map((note, idx) => (
                        <div key={idx} className="p-3 bg-slate-50 dark:bg-slate-955 border border-slate-100 dark:border-slate-850 rounded-xl text-xs text-slate-700 dark:text-slate-350 font-bold leading-normal relative group">
                          {note}
                          <button 
                            onClick={() => setSavedNotes(savedNotes.filter((_, i) => i !== idx))}
                            className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-750 transition-opacity cursor-pointer"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {playerTab === "resources" && (
                <div className="space-y-3">
                  <h4 className="text-slate-855 dark:text-white font-bold text-xs">Resources & Downloads</h4>
                  <div className="grid grid-cols-1 gap-2.5">
                    {[
                      { title: "HTML5 Official Cheatsheet (W3C)", format: "PDF", size: "1.2 MB" },
                      { title: "Sample HTML5 Practice Workspace Setup", format: "ZIP", size: "4.5 MB" },
                      { title: "Candidate Lab Workbook - Lesson 1", format: "PDF", size: "850 KB" }
                    ].map((item, idx) => (
                      <div key={idx} className="p-3.5 bg-slate-50 dark:bg-slate-955 border border-slate-100 dark:border-slate-850 rounded-xl flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded bg-indigo-50 dark:bg-indigo-950/40 text-indigo-650 dark:text-indigo-400 flex items-center justify-center font-bold text-[10px] shrink-0">
                            {item.format}
                          </div>
                          <div>
                            <div className="text-xs font-bold text-slate-800 dark:text-slate-200">{item.title}</div>
                            <div className="text-[9px] text-slate-400 font-bold font-mono">{item.size}</div>
                          </div>
                        </div>
                        <button className="text-indigo-600 dark:text-indigo-400 font-extrabold text-[10px] uppercase hover:underline cursor-pointer">
                          Download
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {playerTab === "transcript" && (
                <div className="space-y-4 max-h-[300px] overflow-y-auto pr-1">
                  <h4 className="text-slate-855 dark:text-white font-bold text-xs font-black">Video Transcription</h4>
                  <div className="space-y-3 leading-relaxed">
                    {[
                      { time: 0, speaker: "Instructor", text: "Welcome to this HTML5 course. In this first lesson, we will focus on understanding the basics and setting up the local coding workspace." },
                      { time: 45, speaker: "Instructor", text: "We need an editor like VS Code or another IDE. Let's write our first skeleton index.html file." },
                      { time: 120, speaker: "Instructor", text: "HTML5 introduces semantic structures. This defines explicit blocks like header, footer, article, and section..." }
                    ].map((line, idx) => (
                      <div key={idx} className="flex gap-3 text-xs leading-normal">
                        <span className="font-mono font-black text-indigo-605 dark:text-indigo-405 shrink-0 bg-indigo-50 dark:bg-indigo-950/40 px-1.5 py-0.5 rounded text-[10px]">
                          {formatTime(line.time)}
                        </span>
                        <div>
                          <span className="font-extrabold text-slate-800 dark:text-slate-200">{line.speaker}: </span>
                          <span className="text-slate-650 dark:text-slate-400 font-semibold">{line.text}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {playerTab === "discussion" && (
                <div className="space-y-4">
                  <h4 className="text-slate-855 dark:text-white font-bold text-xs font-black">Student Forum Q&A</h4>
                  <div className="flex gap-3">
                    <input
                      type="text"
                      placeholder="Ask a question about this lesson..."
                      className="flex-1 bg-slate-50 dark:bg-slate-955 border border-slate-202 dark:border-slate-855 rounded-xl px-4 py-2.5 text-xs text-slate-805 dark:text-slate-205 placeholder-slate-500 focus:outline-none focus:border-indigo-655 font-semibold"
                    />
                    <button className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-sm cursor-pointer whitespace-nowrap">
                      Post Question
                    </button>
                  </div>
                  <div className="pt-2 space-y-3">
                    <div className="p-3 bg-slate-50 dark:bg-slate-955 border border-slate-100 dark:border-slate-855 rounded-xl space-y-1">
                      <div className="flex justify-between items-center text-[10px]">
                        <span className="font-extrabold text-slate-800 dark:text-slate-250">Siva Kumar</span>
                        <span className="text-slate-400 font-bold">2 hours ago</span>
                      </div>
                      <p className="text-xs text-slate-600 dark:text-slate-400 font-semibold">
                        What's the keyboard shortcut in VS Code to auto-fill the skeleton HTML structure?
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Bottom AI Study Tools Row */}
            <div className="border-t border-slate-100 dark:border-slate-855 pt-4 mt-2">
              <span className="text-[10px] text-slate-400 font-bold uppercase font-mono tracking-wider">AI Study Companions</span>
              <div className="flex flex-wrap gap-2.5 mt-2.5">
                {[
                  { name: "AI Summary", icon: Sparkles, color: "text-indigo-600 bg-indigo-50 border-indigo-100 dark:text-indigo-400 dark:bg-indigo-950/20 dark:border-indigo-900/30" },
                  { name: "Explain Like I'm 10", icon: Brain, color: "text-purple-600 bg-purple-50 border-purple-100 dark:text-purple-400 dark:bg-purple-950/20 dark:border-purple-900/30" },
                  { name: "Generate Quiz", icon: CheckCircle2, color: "text-emerald-600 bg-emerald-50 border-emerald-100 dark:text-emerald-400 dark:bg-emerald-950/20 dark:border-emerald-900/30" },
                  { name: "Code Playground", icon: Code, color: "text-amber-600 bg-amber-50 border-amber-100 dark:text-amber-400 dark:bg-amber-950/20 dark:border-amber-900/30" },
                  { name: "Flashcards", icon: FileText, color: "text-blue-600 bg-blue-50 border-blue-100 dark:text-blue-400 dark:bg-blue-950/20 dark:border-blue-900/30" },
                  { name: "Interview Q&A", icon: HelpCircle, color: "text-rose-600 bg-rose-50 border-rose-100 dark:text-rose-400 dark:bg-rose-950/20 dark:border-rose-900/30" },
                  { name: "Career Tips", icon: Award, color: "text-teal-605 bg-teal-50 border-teal-100 dark:text-teal-400 dark:bg-teal-950/20 dark:border-teal-900/30" }
                ].map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleAIClick(item.name)}
                    className={`flex items-center gap-2 px-3 py-2 border rounded-xl text-xs font-bold cursor-pointer transition-all hover:scale-105 active:scale-95 ${item.color}`}
                  >
                    <item.icon size={13} className="shrink-0" />
                    <span>{item.name}</span>
                  </button>
                ))}
              </div>
            </div>

          </div>
        </div>

        {/* RIGHT SIDEBAR WIDGETS COLUMN (4/12) */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          
          {/* Progress ring Card */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-5 md:p-6 shadow-sm flex flex-col gap-5">
            <div>
              <span className="text-[10px] font-black uppercase text-slate-400 font-mono tracking-wider">Your Stats</span>
              <h3 className="text-sm font-black text-slate-850 dark:text-white mt-0.5">Overall Progress</h3>
            </div>
            
            {/* SVG Ring Row */}
            <div className="flex items-center gap-5">
              <div className="relative shrink-0 flex items-center justify-center">
                <svg className="w-18 h-18 transform -rotate-90">
                  <circle
                    cx="36"
                    cy="36"
                    r="30"
                    className="stroke-slate-100 dark:stroke-slate-800"
                    strokeWidth="6.5"
                    fill="transparent"
                  />
                  <circle
                    cx="36"
                    cy="36"
                    r="30"
                    className="stroke-indigo-600 transition-all duration-500"
                    strokeWidth="6.5"
                    fill="transparent"
                    strokeDasharray={2 * Math.PI * 30}
                    strokeDashoffset={2 * Math.PI * 30 * (1 - courseProgressPercent / 100)}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute text-sm font-black text-slate-855 dark:text-white font-mono">
                  {courseProgressPercent}%
                </div>
              </div>
              <div>
                <h4 className="text-xs font-extrabold text-slate-800 dark:text-slate-205">You've completed</h4>
                <p className="text-[11px] text-slate-500 font-bold mt-0.5">
                  {completedLessonIds.length} of {curriculum.sections?.flatMap((s: any) => s.lessons || []).length || 48} lessons
                </p>
              </div>
            </div>

            {/* Streak & Stats Footer grid */}
            <div className="grid grid-cols-3 gap-3 border-t border-slate-100 dark:border-slate-855 pt-4">
              <div className="text-center space-y-0.5 border-r border-slate-100 dark:border-slate-855">
                <div className="text-[9px] text-slate-400 uppercase font-mono font-bold">Streak</div>
                <div className="text-xs font-extrabold text-orange-500 flex items-center justify-center gap-1">
                  <Flame size={12} className="fill-current" />
                  <span>{userStats.streak} Days</span>
                </div>
              </div>
              <div className="text-center space-y-0.5 border-r border-slate-100 dark:border-slate-855">
                <div className="text-[9px] text-slate-400 uppercase font-mono font-bold">Level</div>
                <div className="text-xs font-extrabold text-indigo-600 dark:text-indigo-405 flex items-center justify-center gap-1">
                  <Award size={12} />
                  <span>{1 + Math.floor(userStats.xp / 100)}</span>
                </div>
              </div>
              <div className="text-center space-y-0.5">
                <div className="text-[9px] text-slate-400 uppercase font-mono font-bold">XP Earned</div>
                <div className="text-xs font-extrabold text-indigo-650 dark:text-indigo-405 flex items-center justify-center gap-1 font-mono">
                  <span>{userStats.xp}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Module Collapsible Dropdown Roadmap Card */}
          <div className="bg-white dark:bg-slate-900 border border-slate-202 dark:border-slate-800 rounded-3xl p-5 md:p-6 shadow-sm flex flex-col gap-4">
            <div>
              <span className="text-[10px] font-black uppercase text-slate-400 font-mono tracking-wider">Syllabus Navigation</span>
              <h3 className="text-sm font-black text-slate-855 dark:text-white mt-0.5">Modules Roadmap</h3>
            </div>

            <div className="flex flex-col gap-2.5 max-h-[480px] overflow-y-auto pr-1 scrollbar-thin">
              {curriculum?.sections?.map((section: any, secIdx: number) => {
                const totalInSec = section.lessons?.length || 0;
                const completedInSec = section.lessons?.filter((l: any) => completedLessonIds.includes(l.id))?.length || 0;
                const sectionNo = secIdx + 1;
                const isExpanded = expandedModules.includes(section.id);
                
                return (
                  <div key={section.id} className="border border-slate-100 dark:border-slate-850 rounded-2xl overflow-hidden bg-slate-50/40 dark:bg-slate-950/20">
                    <button
                      onClick={() => toggleModule(section.id)}
                      className="w-full px-4 py-3.5 flex justify-between items-center text-left text-xs font-black text-slate-800 dark:text-white hover:bg-slate-100/50 dark:hover:bg-slate-855/50 transition-colors cursor-pointer"
                    >
                      <div className="flex flex-col pr-2">
                        <span className="text-[9px] font-mono text-indigo-600 dark:text-indigo-400 uppercase tracking-widest">
                          Module {sectionNo}
                        </span>
                        <span className="mt-0.5 text-slate-800 dark:text-slate-100 text-xs font-extrabold truncate max-w-[180px]">
                          {section.title.split(":").slice(1).join(":") || section.title}
                        </span>
                      </div>
                      <div className="flex items-center gap-2.5 shrink-0">
                        <span className="text-[9px] font-mono font-bold bg-slate-100 dark:bg-slate-800 text-slate-550 dark:text-slate-400 px-2 py-0.5 rounded-full">
                          {completedInSec}/{totalInSec}
                        </span>
                        <ChevronRight 
                          size={14} 
                          className={`text-slate-400 transition-transform duration-300 ${isExpanded ? "transform rotate-90" : ""}`} 
                        />
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="p-3 border-t border-slate-100 dark:border-slate-855 flex flex-col gap-2 bg-white dark:bg-slate-900">
                        {section.lessons?.map((less: any) => {
                          const completed = completedLessonIds.includes(less.id);
                          const isLocked = less.is_locked;
                          const active = currentLesson.id === less.id;

                          let stateLabel = "Available";
                          let stateColor = "text-indigo-500 bg-indigo-500/10";
                          
                          if (completed) {
                            stateLabel = "Completed";
                            stateColor = "text-emerald-500 bg-emerald-500/10";
                          } else if (isLocked) {
                            stateLabel = "Locked";
                            stateColor = "text-slate-400 bg-slate-100 dark:bg-slate-800/40";
                          } else if (active) {
                            stateLabel = "In Progress";
                            stateColor = "text-blue-500 bg-blue-500/10 animate-pulse";
                          }

                          return (
                            <button
                              key={less.id}
                              disabled={isLocked}
                              onClick={() => {
                                pauseActiveVideo();
                                setCurrentLesson(less);
                                setPlayerTab("overview");
                              }}
                              className={`flex items-center justify-between p-3 rounded-xl border text-left text-xs transition-all w-full cursor-pointer relative overflow-hidden ${
                                active
                                  ? "bg-indigo-50 border-indigo-200 dark:bg-indigo-950/20 dark:border-indigo-800/60 text-indigo-650 dark:text-indigo-400 font-extrabold shadow-sm"
                                  : isLocked
                                    ? "bg-slate-50 dark:bg-slate-955 border-slate-100 dark:border-slate-900 text-slate-400 opacity-60 cursor-not-allowed"
                                    : "bg-white dark:bg-slate-900 border-slate-202 dark:border-slate-800 text-slate-750 dark:text-slate-355 hover:border-indigo-500/20"
                              }`}
                            >
                              <div className="flex items-center gap-2.5 min-w-0 pr-2 relative z-10">
                                {completed ? (
                                  <CheckCircle2 size={13} className="text-emerald-500 shrink-0" />
                                ) : isLocked ? (
                                  <Lock size={12} className="text-slate-400 shrink-0" />
                                ) : active ? (
                                  <Play size={12} className="text-blue-500 shrink-0 animate-bounce" />
                                ) : (
                                  <ChevronRight size={12} className="text-indigo-500 shrink-0" />
                                )}
                                <span className="truncate font-semibold text-slate-855 dark:text-slate-200">{less.title}</span>
                              </div>

                              <div className="flex items-center gap-1.5 shrink-0 relative z-10">
                                <span className={`text-[7px] font-mono font-bold px-1.5 py-0.5 rounded-full uppercase ${stateColor}`}>
                                  {stateLabel}
                                </span>
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* AI Mentor Sidebar Chat Widget Card */}
          <div className="bg-white dark:bg-slate-900 border border-slate-202 dark:border-slate-800 rounded-3xl p-5 md:p-6 shadow-sm flex flex-col gap-4">
            <div className="flex justify-between items-center">
              <div>
                <span className="text-[10px] font-black uppercase text-indigo-600 dark:text-indigo-400 font-mono tracking-wider">AI Mentor Widget</span>
                <h3 className="text-sm font-black text-slate-850 dark:text-white mt-0.5">Study Helper</h3>
              </div>
              <div className="w-8 h-8 rounded-full bg-indigo-50 dark:bg-indigo-950/40 text-indigo-605 dark:text-indigo-405 border border-indigo-100 dark:border-indigo-900/30 flex items-center justify-center relative animate-pulse shrink-0">
                <Brain size={16} />
              </div>
            </div>

            <p className="text-[11px] text-slate-500 font-bold leading-normal bg-indigo-50/20 dark:bg-slate-955/30 p-2.5 rounded-xl border border-indigo-100/10">
              Ask me anything about this lesson. I can summarize, explain concepts, generate quick practice quiz questions, or share tips!
            </p>

            {/* Dynamic Message Panel */}
            <div className="bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-855 rounded-2xl p-3 flex flex-col gap-3 h-[240px] overflow-y-auto pr-1">
              {mentorMessages.length === 0 ? (
                <div className="my-auto text-center flex flex-col items-center gap-2 p-4 text-slate-400">
                  <MessageSquare size={24} className="opacity-40 animate-pulse text-indigo-500" />
                  <span className="text-[10px] font-bold">Ask anything to initiate session chat...</span>
                </div>
              ) : (
                mentorMessages.map((msg: any) => {
                  const isUser = msg.sender === "user";
                  return (
                    <div 
                      key={msg.id}
                      className={`flex flex-col max-w-[85%] rounded-2xl px-3 py-2.5 text-xs leading-normal font-semibold ${
                        isUser
                          ? "bg-indigo-600 text-white self-end rounded-br-none"
                          : "bg-white border border-slate-100 dark:bg-slate-900 dark:border-slate-800 text-slate-800 dark:text-slate-200 self-start rounded-bl-none shadow-sm"
                      }`}
                    >
                      <span>{msg.message}</span>
                      <span className={`text-[7px] font-mono mt-1 ${isUser ? "text-indigo-200 self-end" : "text-slate-405"}`}>
                        {msg.created_at ? new Date(msg.created_at).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : ""}
                      </span>
                    </div>
                  );
                })
              )}

              {loadingMentor && (
                <div className="bg-white border border-slate-100 dark:bg-slate-900 dark:border-slate-800 text-slate-400 self-start rounded-2xl rounded-bl-none px-4 py-3 text-xs leading-normal font-semibold shadow-sm flex items-center gap-2">
                  <Loader2 size={13} className="animate-spin text-indigo-500" />
                  <span className="text-[10px] font-mono uppercase tracking-wider font-bold">Mentor thinking...</span>
                </div>
              )}
            </div>

            {/* Quick Prompts Chips */}
            <div className="flex flex-wrap gap-1.5 pt-1">
              {[
                `What is ${selectedCourse.title?.split(" ")[0]}?`,
                "Give me an example",
                "Summarize key terms"
              ].map((chip, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMentorMessage(chip)}
                  className="bg-slate-50 hover:bg-indigo-50 hover:text-indigo-600 border border-slate-100 dark:bg-slate-950 dark:border-slate-855 dark:hover:bg-indigo-955/25 text-[10px] font-bold text-slate-500 px-2.5 py-1.5 rounded-lg transition-colors cursor-pointer"
                >
                  {chip}
                </button>
              ))}
            </div>

            {/* Input & Send controls */}
            <div className="flex gap-2 border border-slate-100 dark:border-slate-850 p-1.5 rounded-2xl bg-slate-50 dark:bg-slate-955">
              <input
                type="text"
                value={mentorInput}
                onChange={(e) => setMentorInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && mentorInput.trim()) {
                    handleSendMentorMessage(mentorInput);
                  }
                }}
                placeholder="Ask AI Mentor anything..."
                className="flex-1 bg-transparent text-xs text-slate-800 dark:text-slate-205 placeholder-slate-500 outline-none px-2 font-semibold"
              />
              <button
                onClick={() => {
                  if (mentorInput.trim()) {
                    handleSendMentorMessage(mentorInput);
                  }
                }}
                disabled={!mentorInput.trim() || loadingMentor}
                className="w-8 h-8 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-slate-200 disabled:text-slate-400 dark:disabled:bg-slate-855 dark:disabled:text-slate-600 flex items-center justify-center cursor-pointer disabled:cursor-not-allowed shadow-sm transition-all"
              >
                <ArrowRight size={14} />
              </button>
            </div>
          </div>

        </div>

      </div>

      {isYouTube && (
        <Script 
          src="https://www.youtube.com/iframe_api" 
          strategy="afterInteractive"
        />
      )}
    </div>
  );
}

function extractYouTubeId(url: string, courseId?: string, lessonId?: string): string | null {
  if (!url) return null;
  const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
  const match = url.match(regExp);
  if (match && match[2].length === 11) {
    return match[2];
  }
  // Graceful fallback for placeholder or generic URLs to ensure a premium player experience
  if (url.includes("youtube.com") || url.includes("youtu.be") || url.startsWith("url")) {
    const cid = String(courseId || "").toUpperCase();
    const lid = String(lessonId || "");
    
    // Stable hash function to distribute fallback videos across lessons
    let hash = 0;
    for (let i = 0; i < lid.length; i++) {
      hash = lid.charCodeAt(i) + ((hash << 5) - hash);
    }
    const idx = Math.abs(hash);
    
    if (cid.includes("D1") || cid.includes("DOCKER")) {
      const dockerVids = ["3c-iKanfgbA", "fqMOX6JJhGo", "pTFZFxd4hOI", "gAkwW2tuIqE", "ScMzIvxBSi4"];
      return dockerVids[idx % dockerVids.length];
    } else if (cid.includes("H1") || cid.includes("HTML")) {
      const htmlVids = ["MDLn5-zSQQI", "kUMe1FH4WHY", "hu-q2zYwEYs", "PlxWf493en4", "ok-plXXgbWA"];
      return htmlVids[idx % htmlVids.length];
    }
    
    return "Ke90Tje7VS0"; // Default React video if no course match
  }
  return null;
}
