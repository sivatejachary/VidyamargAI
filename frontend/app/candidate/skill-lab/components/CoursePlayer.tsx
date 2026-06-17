"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import { apiService } from "@/services/api";
import { useAuthStore } from "@/store/authStore";
import { 
  Play, Pause, BookOpen, Brain, Trash2, ArrowRight, Clock, ShieldAlert, 
  RefreshCw, Upload, Code, CheckCircle, Volume2, VolumeX, Maximize2, 
  Minimize2, Lock, Sparkles, Award, FileText, CheckCircle2, ChevronRight
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

  // YouTube player state refs and helper
  const isYouTube = useMemo(() => {
    return !!(currentLesson?.video_url && (currentLesson.video_url.includes("youtube.com") || currentLesson.video_url.includes("youtu.be")));
  }, [currentLesson?.video_url]);
  const ytPlayerRef = useRef<any>(null);
  const ytIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const ytStartedTimeoutRef = useRef<NodeJS.Timeout | null>(null);

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
          if (res && res.lessonId === currentLesson.id && res.playbackPosition > 0) {
            console.log(`Resuming lesson at position: ${res.playbackPosition}`);
            if (videoRef.current) {
              videoRef.current.currentTime = res.playbackPosition;
            }
          } else {
            // Local fallback
            const cached = localStorage.getItem(`resume:lesson:${currentLesson.id}`);
            if (cached && videoRef.current) {
              videoRef.current.currentTime = parseFloat(cached);
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
    if (ytIntervalRef.current) {
      clearInterval(ytIntervalRef.current);
      ytIntervalRef.current = null;
    }
    if (ytPlayerRef.current) {
      try {
        ytPlayerRef.current.destroy();
      } catch (e) {
        console.error("Error destroying YT player:", e);
      }
      ytPlayerRef.current = null;
    }

    if (!currentLesson || currentLesson.type !== "video" || !isYouTube) return;

    setIsLoading(true);
    setIsPlaying(false);
    setVideoError(null);

    const videoId = extractYouTubeId(currentLesson.video_url);
    if (!videoId) {
      setVideoError("Invalid YouTube URL");
      setIsLoading(false);
      return;
    }

    let checkInterval: NodeJS.Timeout | null = null;
    let initialized = false;

    const initializeYTPlayer = () => {
      if (initialized) return;
      if ((window as any).YT && (window as any).YT.Player) {
        initialized = true;
        if (checkInterval) clearInterval(checkInterval);
        
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
              },
              onStateChange: (event: any) => {
                const state = event.data;
                // Playing is 1, Paused is 2, Ended is 0
                if (state === 1) {
                  setIsPlaying(true);
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
                setVideoError("Unable to load YouTube video");
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

    // Load YouTube iframe API script if not present
    if (!(window as any).YT) {
      const tag = document.createElement('script');
      tag.src = 'https://www.youtube.com/iframe_api';
      const firstScriptTag = document.getElementsByTagName('script')[0];
      firstScriptTag.parentNode?.insertBefore(tag, firstScriptTag);
    }

    // Set callback if script is loading
    const previousCallback = (window as any).onYouTubeIframeAPIReady;
    (window as any).onYouTubeIframeAPIReady = () => {
      if (previousCallback) previousCallback();
      initializeYTPlayer();
    };

    // Fallback polling check in case API is already loaded/loading
    checkInterval = setInterval(initializeYTPlayer, 200);

    return () => {
      if (checkInterval) clearInterval(checkInterval);
      if (ytIntervalRef.current) clearInterval(ytIntervalRef.current);
      if (ytStartedTimeoutRef.current) clearTimeout(ytStartedTimeoutRef.current);
      if (ytPlayerRef.current) {
        try {
          ytPlayerRef.current.destroy();
        } catch (e) {}
      }
    };
  }, [currentLesson?.id, isYouTube]);

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
    if (val > currentTime) {
      console.warn("Seeking forward is disabled");
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
    <div className="flex flex-col gap-6 max-w-7xl mx-auto w-full">
      
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
            <p className="text-xs text-slate-350 leading-relaxed">
              You've successfully validated this lesson with strict watch compliance.
            </p>
            <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 px-4 py-2 rounded-xl text-emerald-400 font-extrabold text-sm">
              <Sparkles size={16} />
              <span>+{xpEarnedAlert} XP Earned</span>
            </div>
          </div>
        </div>
      )}

      {/* Title & Navigation top row */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-105 dark:border-slate-850 pb-5">
        <div className="space-y-1">
          <button 
            onClick={() => setActiveView("explore")}
            className="text-[10px] font-extrabold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 cursor-pointer uppercase tracking-wider"
          >
            <span>← Back to Explore Courses</span>
          </button>
          <h2 className="text-lg font-black text-slate-800 dark:text-white leading-tight">
            {selectedCourse.title}
          </h2>
        </div>

        {/* Global Progress Indicators */}
        <div className="flex items-center gap-6 shrink-0 w-full md:w-auto">
          <div className="flex-1 md:flex-initial space-y-1">
            <div className="flex justify-between text-[10px] font-bold text-slate-500 uppercase">
              <span>Course Progress</span>
              <span className="text-indigo-600 dark:text-indigo-400 font-black">{courseProgressPercent}%</span>
            </div>
            <div className="w-full md:w-36 h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-indigo-600 dark:bg-indigo-400 transition-all duration-500" style={{ width: `${courseProgressPercent}%` }} />
            </div>
          </div>

          <div className="flex-1 md:flex-initial space-y-1">
            <div className="flex justify-between text-[10px] font-bold text-slate-500 uppercase">
              <span>Streak</span>
              <span className="text-emerald-500 font-black">{userStats.streak} Days</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700 dark:text-slate-300">
              <Award size={14} className="text-amber-500" />
              <span>Level {1 + Math.floor(userStats.xp / 100)}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* PLAYER AREA COLUMN (8/12) */}
        <div className="lg:col-span-8 flex flex-col gap-6">
          
          {/* Main Course Player Window */}
          <div className="bg-slate-900 border border-slate-850 rounded-3xl overflow-hidden shadow-2xl relative">
            
            {/* Header info bar */}
            <div className="bg-slate-950 px-5 py-3 border-b border-slate-900 flex justify-between items-center text-xs font-bold text-slate-400">
              <div className="flex items-center gap-2 truncate pr-4">
                <span className="text-[10px] font-mono bg-indigo-950 text-indigo-400 border border-indigo-850 px-2 py-0.5 rounded">
                  {activeModuleTitle.split(":")[0]}
                </span>
                <span className="truncate text-slate-200">{currentLesson.title}</span>
              </div>
              <div className="flex items-center gap-1.5 text-[10px] font-mono shrink-0">
                <Clock size={11} />
                <span>{currentLesson.duration || "10 min"}</span>
              </div>
            </div>

            {/* Video Player */}
            {currentLesson.type === "video" ? (
              <div 
                ref={playerContainerRef} 
                className="relative aspect-video w-full bg-black group select-none"
              >
                {isYouTube ? (
                  <div key={currentLesson.id} className="absolute inset-0 w-full h-full overflow-hidden">
                    <div 
                      id="youtube-player" 
                      className="absolute w-full h-[150%] -top-[25%] left-0 right-0 pointer-events-none"
                    />
                    
                    {/* Black cover overlay to hide cued YouTube video & logo before playback starts */}
                    {!hasStarted && (
                      <div className="absolute inset-0 bg-black z-10 pointer-events-none" />
                    )}

                    {/* Transparent Click Overlay to intercept pointer events and toggle play/pause */}
                    <div 
                      onClick={togglePlay}
                      className="absolute inset-0 w-full h-full cursor-pointer z-15 bg-transparent pointer-events-auto"
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

                {/* Loading State Overlay */}
                {isLoading && (
                  <div className="absolute inset-0 bg-slate-955/80 flex flex-col items-center justify-center gap-3">
                    <RefreshCw className="animate-spin text-indigo-500" size={32} />
                    <span className="text-xs text-slate-300 font-bold uppercase tracking-wider">Streaming Video...</span>
                  </div>
                )}

                {/* Custom Error Overlay */}
                {videoError && (
                  <div className="absolute inset-0 bg-slate-950 flex flex-col items-center justify-center gap-3.5 text-center p-6">
                    <ShieldAlert size={44} className="text-red-500" />
                    <div>
                      <h4 className="text-sm font-black text-white">Unable to load lesson video</h4>
                      <p className="text-[11px] text-slate-450 mt-1 max-w-xs mx-auto">
                        We had trouble fetching the video from the CDN edge server.
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

                {/* Centered Play Button Overlay when paused */}
                {!isPlaying && !videoError && !isLoading && (
                  <button 
                    onClick={togglePlay}
                    className="absolute inset-0 flex items-center justify-center bg-black/20 hover:bg-black/35 transition-all cursor-pointer animate-fade-in z-20 pointer-events-auto"
                  >
                    <div className="w-16 h-16 rounded-full bg-white/10 hover:bg-white/20 border border-white/30 text-white flex items-center justify-center shadow-lg backdrop-blur-sm transition-transform hover:scale-110">
                      <Play size={24} className="fill-current ml-1" />
                    </div>
                  </button>
                )}

                {/* Auto Next Countdown Overlay */}
                {autoNextCount !== null && (
                  <div className="absolute inset-0 bg-slate-950/95 flex flex-col items-center justify-center gap-5 text-center p-6 z-30">
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
                        className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-350 text-xs font-bold rounded-xl border border-slate-700 cursor-pointer"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {/* Custom Controls Bar */}
                {!videoError && !isLoading && (
                  <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-slate-950 via-slate-950/60 to-transparent flex flex-col gap-2.5 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity duration-300 z-20">
                    {/* Time progress bar (Non-interactive) */}
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
                          {isPlaying ? <Pause size={16} /> : <Play size={16} />}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : currentLesson.type === "pdf" ? (
              <div className="bg-slate-950 p-6 min-h-[350px] flex flex-col justify-between items-center text-center">
                <div className="my-auto flex flex-col items-center gap-4">
                  <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center">
                    <BookOpen size={32} />
                  </div>
                  <div>
                    <h4 className="text-sm font-black text-white">{currentLesson.title}</h4>
                    <p className="text-[11px] text-slate-450 mt-1.5 max-w-xs mx-auto leading-normal">
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
              <div className="bg-slate-950 p-6 flex flex-col gap-5">
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
                        <p className="text-xs font-bold text-slate-200">{q.question}</p>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 mt-1">
                          {q.options.map((opt: string, optIdx: number) => (
                            <button
                              key={optIdx}
                              onClick={() => setQuizAnswers(prev => ({ ...prev, [qIdx]: optIdx }))}
                              className={`p-3 rounded-xl border text-left text-xs font-semibold transition-all cursor-pointer ${
                                quizAnswers[qIdx] === optIdx
                                  ? "bg-indigo-600 text-white border-indigo-600 font-bold shadow-md"
                                  : "bg-slate-950 border-slate-850 text-slate-300 hover:border-indigo-500/30"
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
                            
                            // Gamification & events
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
                        className="px-6 py-2.8 bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-slate-800 disabled:text-slate-500 text-xs font-black rounded-xl cursor-pointer disabled:cursor-not-allowed shadow-md"
                      >
                        Submit Answers
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : currentLesson.type === "written_assessment" && currentLesson.written_assessment ? (
              <div className="bg-slate-950 p-6 flex flex-col gap-5">
                {currentLesson.written_assessment.passed ? (
                  <div className="my-auto text-center flex flex-col items-center gap-4 py-8">
                    <div className="w-14 h-14 rounded-full bg-emerald-500/10 text-emerald-450 border border-emerald-500/20 flex items-center justify-center text-xl font-bold">
                      ✓
                    </div>
                    <div>
                      <h4 className="text-sm font-black text-white">Assessment Evaluated!</h4>
                      <p className="text-xs text-slate-400 mt-1">
                        Best Score: <span className="font-extrabold text-emerald-400">{currentLesson.written_assessment.best_score}%</span>
                      </p>
                      {currentLesson.written_assessment.feedback && (
                        <p className="text-[10px] text-slate-400 bg-slate-900 p-3 rounded-xl border border-slate-850 mt-3 max-w-md mx-auto leading-relaxed">
                          Feedback: {currentLesson.written_assessment.feedback}
                        </p>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="space-y-5">
                    {currentLesson.written_assessment.questions.map((q: string, qIdx: number) => (
                      <div key={qIdx} className="p-4 bg-slate-900 border border-slate-850 rounded-2xl flex flex-col gap-3">
                        <span className="text-[9px] font-black text-indigo-400 uppercase tracking-widest">Question {qIdx + 1}</span>
                        <p className="text-xs font-bold text-slate-200">{q}</p>
                        
                        <textarea
                          placeholder="Type your explanation answer here..."
                          value={writtenAnswers[qIdx] || ""}
                          onChange={(e) => setWrittenAnswers(prev => ({ ...prev, [qIdx]: e.target.value }))}
                          rows={4}
                          className="w-full bg-slate-950 border border-slate-850 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
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
                            
                            setXpEarnedAlert(50);
                            setShowSuccessOverlay(true);
                            setTimeout(() => setShowSuccessOverlay(false), 3000);
                          } catch (err) {
                            console.error(err);
                          }
                        }}
                        disabled={Object.keys(writtenAnswers).length < currentLesson.written_assessment.questions.length}
                        className="px-6 py-2.8 bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-slate-800 disabled:text-slate-500 text-xs font-black rounded-xl cursor-pointer disabled:cursor-not-allowed shadow-md"
                      >
                        Submit Assessment
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : currentLesson.type === "ai_interview" && currentLesson.module_interview ? (
              <div className="bg-slate-950 p-6 flex flex-col gap-5">
                {interviewResult ? (
                  <div className="my-auto text-center flex flex-col items-center gap-4 py-8">
                    <div className="w-14 h-14 rounded-full bg-emerald-500/10 text-emerald-450 border border-emerald-500/20 flex items-center justify-center text-xl font-bold">
                      ✓
                    </div>
                    <div>
                      <h4 className="text-sm font-black text-white">AI Evaluation Completed!</h4>
                      <p className="text-xs text-slate-400 mt-1">
                        Interview Score: <span className="font-extrabold text-emerald-400">{interviewResult.interview_score}%</span>
                      </p>
                      <div className="text-left text-[10px] text-slate-400 bg-slate-900 p-4 rounded-xl border border-slate-850 mt-3 max-w-md mx-auto leading-relaxed">
                        <span className="font-bold text-slate-350 uppercase tracking-widest block text-[9px] mb-1">Feedback Report:</span>
                        <p>{interviewResult.feedback}</p>
                      </div>
                    </div>
                  </div>
                ) : !interviewStarted ? (
                  <div className="my-auto text-center flex flex-col items-center gap-4 py-8">
                    <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center">
                      <Brain size={28} />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-white">Ready for your AI interview validation?</h4>
                      <p className="text-[10px] text-slate-450 mt-1 max-w-xs mx-auto leading-relaxed">
                        TARA will evaluate your viva verbal explanations. This requires mic permissions for speech-to-text.
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
                  <div className="flex flex-col gap-4">
                    {/* Transcript Box */}
                    <div className="min-h-[200px] max-h-[250px] overflow-y-auto bg-slate-900 border border-slate-850 p-4 rounded-2xl flex flex-col gap-3.5 scrollbar-thin">
                      {interviewTranscript.map((msg, idx) => (
                        <div
                          key={idx}
                          className={`max-w-[80%] rounded-2xl p-3 text-xs leading-relaxed ${
                            msg.role === "candidate"
                              ? "bg-indigo-600 text-white self-end rounded-tr-none"
                              : "bg-slate-950 border border-slate-900 text-slate-200 self-start rounded-tl-none"
                          }`}
                        >
                          <span className="text-[8px] font-black uppercase opacity-75 block mb-0.5">
                            {msg.role === "candidate" ? "You" : "TARA AI Assessor"}
                          </span>
                          <p className="font-semibold">{msg.text}</p>
                        </div>
                      ))}
                    </div>

                    {/* Microphone status and controls */}
                    <div className="bg-slate-900 border border-slate-850 p-4 rounded-2xl flex flex-col gap-3">
                      <div className="flex justify-between items-center">
                        <span className="text-[9px] font-black text-slate-450 uppercase tracking-widest">
                          Question {currentInterviewQuestionIdx + 1} of {currentLesson.module_interview.questions.length}
                        </span>

                        <div className="flex items-center gap-1.5 text-xs font-bold text-slate-400">
                          <Clock size={12} />
                          <span>{Math.floor(interviewTimeRemaining / 60)}:{(interviewTimeRemaining % 60).toString().padStart(2, '0')}</span>
                        </div>
                      </div>

                      {interviewInputMode === "voice" ? (
                        <div className="flex flex-col items-center gap-3 py-2">
                          <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                              aiVoiceState === "listening"
                                ? "bg-red-500 text-white animate-pulse"
                                : aiVoiceState === "speaking"
                                  ? "bg-indigo-500 text-white"
                                  : "bg-slate-805 text-slate-450"
                            }`}>
                              <Brain size={16} />
                            </div>
                            <span className="text-xs font-bold text-slate-200 capitalize">
                              {aiVoiceState === "listening" ? "Listening to response..." : aiVoiceState === "speaking" ? "TARA is speaking..." : "Assessor Ready"}
                            </span>
                          </div>

                          <textarea
                            placeholder="Voice transcript text will stream here as you speak..."
                            value={candidateInterviewResponse}
                            onChange={(e) => setCandidateInterviewResponse(e.target.value)}
                            rows={2}
                            className="w-full bg-slate-950 border border-slate-850 rounded-xl p-3 text-xs text-slate-350 focus:outline-none"
                          />
                        </div>
                      ) : (
                        <textarea
                          placeholder="Type your structured explanation answer here..."
                          value={candidateInterviewResponse}
                          onChange={(e) => setCandidateInterviewResponse(e.target.value)}
                          rows={3}
                          className="w-full bg-slate-950 border border-slate-850 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                        />
                      )}

                      <div className="flex justify-between items-center border-t border-slate-850 pt-3">
                        <button
                          onClick={() => setInterviewInputMode(interviewInputMode === "voice" ? "type" : "voice")}
                          className="text-[10px] text-indigo-400 font-bold hover:underline cursor-pointer"
                        >
                          Switch to {interviewInputMode === "voice" ? "Keyboard Typing" : "Voice Assessment"}
                        </button>

                        <button
                          onClick={handleAdvanceQuestion}
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
            ) : currentLesson.type === "assignment" && currentLesson.assignment ? (
              <div className="bg-slate-950 p-6 flex flex-col gap-4">
                <div>
                  <span className="text-[9px] font-black text-indigo-400 uppercase tracking-widest">
                    Practical Homework Project
                  </span>
                  <h3 className="text-xs font-bold text-white mt-1">{currentLesson.assignment.title}</h3>
                </div>

                <div className="p-4 bg-slate-900 border border-slate-850 rounded-2xl space-y-3">
                  <h4 className="text-xs font-bold text-slate-300">Overview Description:</h4>
                  <p className="text-xs text-slate-400 leading-relaxed">{currentLesson.assignment.description}</p>
                </div>

                <div className="border border-dashed border-slate-800 rounded-3xl p-6.5 text-center flex flex-col items-center justify-center gap-3 bg-slate-900">
                  <Upload className="text-indigo-400/60 shrink-0" size={24} />
                  <div>
                    <span className="text-xs font-bold text-white block">Submit Code Archive</span>
                    <span className="text-[9px] text-slate-500 mt-1 block">Drag & drop your files, or click to upload (.py, .zip)</span>
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
                    className="px-4 py-2 bg-slate-950 border border-slate-850 text-[10px] text-slate-300 font-bold rounded-xl cursor-pointer hover:bg-slate-900"
                  >
                    {assignmentFilename ? "Replace File" : "Choose File"}
                  </label>

                  {assignmentFilename && (
                    <span className="text-[10px] text-emerald-400 font-mono font-bold mt-1">Selected: {assignmentFilename}</span>
                  )}
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    disabled={!assignmentUploaded || submittingAssignment}
                    onClick={async () => {
                      setSubmittingAssignment(true);
                      setTimeout(async () => {
                        try {
                          await apiService.completeLesson(currentLesson.id);
                          setCompletedLessonIds([...completedLessonIds, currentLesson.id]);
                          await fetchCurriculum(selectedCourse.id, currentLesson.id);
                          await loadEnrollments();
                          await loadData();
                          
                          setXpEarnedAlert(50);
                          setShowSuccessOverlay(true);
                          setTimeout(() => setShowSuccessOverlay(false), 3000);
                        } catch (err) {
                          console.error(err);
                        } finally {
                          setSubmittingAssignment(false);
                        }
                      }, 1500);
                    }}
                    className="px-4.5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-slate-800 disabled:text-slate-500 text-xs font-bold rounded-xl cursor-pointer"
                  >
                    {submittingAssignment ? "Submitting Code..." : "Submit Assignment Code"}
                  </button>
                </div>
              </div>
            ) : currentLesson.type === "project" && currentLesson.project ? (
              <div className="bg-slate-955 p-6 flex flex-col gap-4">
                <div>
                  <span className="text-[9px] font-black text-emerald-400 uppercase tracking-widest">
                    Capstone Coding Project
                  </span>
                  <h3 className="text-xs font-bold text-white mt-1">{currentLesson.project.title}</h3>
                </div>

                <div className="p-4 bg-slate-900 border border-slate-855 rounded-2xl space-y-3">
                  <h4 className="text-xs font-bold text-slate-300">Task Objectives:</h4>
                  <p className="text-xs text-slate-400 leading-relaxed">{currentLesson.project.description}</p>
                </div>

                <div className="border border-dashed border-slate-800 rounded-3xl p-6.5 text-center flex flex-col items-center justify-center gap-3 bg-slate-900">
                  <Upload className="text-indigo-450/60 shrink-0" size={24} />
                  <div>
                    <span className="text-xs font-bold text-white block">Submit Finished Project</span>
                    <span className="text-[9px] text-slate-500 mt-1 block">Drag & drop your files, or click to upload (.zip)</span>
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
                    className="px-4 py-2 bg-slate-950 border border-slate-850 text-[10px] text-slate-300 font-bold rounded-xl cursor-pointer hover:bg-slate-900"
                  >
                    {projectFilename ? "Replace File" : "Choose File"}
                  </label>

                  {projectFilename && (
                    <span className="text-[10px] text-emerald-400 font-mono font-bold mt-1">Selected: {projectFilename}</span>
                  )}
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    disabled={!projectUploaded || submittingProject}
                    onClick={async () => {
                      setSubmittingProject(true);
                      setTimeout(async () => {
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
                        } finally {
                          setSubmittingProject(false);
                        }
                      }, 1500);
                    }}
                    className="px-4.5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-slate-800 disabled:text-slate-500 text-xs font-bold rounded-xl cursor-pointer"
                  >
                    {submittingProject ? "Submitting Code..." : "Submit Capstone Project"}
                  </button>
                </div>
              </div>
            ) : null}

            {/* Linear navigation buttons */}
            <div className="bg-slate-950 px-5 py-4 border-t border-slate-900 flex justify-between items-center gap-3">
              <button
                onClick={async () => {
                  const idx = flatLessons.findIndex(l => l.id === currentLesson.id);
                  if (idx > 0) {
                    setCurrentLesson(flatLessons[idx - 1]);
                  }
                }}
                disabled={flatLessons.findIndex(l => l.id === currentLesson.id) === 0}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-850 text-slate-300 disabled:text-slate-600 disabled:bg-slate-950 disabled:border-transparent text-xs font-bold rounded-xl border border-slate-800 cursor-pointer disabled:cursor-not-allowed transition-all"
              >
                Previous
              </button>

              <button
                onClick={async () => {
                  if (nextLesson) {
                    // Complete current lesson if not completed yet
                    if (!completedLessonIds.includes(currentLesson.id)) {
                      try {
                        await apiService.completeLesson(currentLesson.id);
                        setCompletedLessonIds([...completedLessonIds, currentLesson.id]);
                        await fetchCurriculum(selectedCourse.id, currentLesson.id);
                        await loadEnrollments();
                        await loadData();
                      } catch (err) {
                        console.error("Error completing lesson on Next click:", err);
                      }
                    }
                    setCurrentLesson(nextLesson);
                  }
                }}
                disabled={!nextLesson || (nextLesson.is_locked && !completedLessonIds.includes(nextLesson.id) && !isNextUnlocked)}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-850 text-slate-300 disabled:text-slate-600 disabled:bg-slate-950 disabled:border-transparent text-xs font-bold rounded-xl border border-slate-800 cursor-pointer disabled:cursor-not-allowed transition-all"
              >
                Next
              </button>
            </div>
          </div>

          {/* Tabbed Menu Below Player */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm flex flex-col gap-5">
            <div className="flex gap-5 border-b border-slate-100 dark:border-slate-800/40 pb-2.5 overflow-x-auto scrollbar-hide shrink-0">
              {[
                { id: "overview", label: "Overview" },
                { id: "notes", label: "Notes" },
                { id: "resources", label: "Resources" },
                { id: "transcript", label: "Transcript" },
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
                <h4 className="text-slate-800 dark:text-white font-bold text-xs">About this Session</h4>
                <p>
                  This session forms part of the module curriculum. Watching video materials completely, studying PDFs, and completing quizzes validates the learning requirements to unlock certifications.
                </p>
                <div className="flex gap-4.5 text-[10px] text-slate-500 border-t border-slate-100 dark:border-slate-800/40 pt-3.5 mt-3 w-full font-mono">
                  <span>Module Progress: {moduleProgressPercent}%</span>
                  <span>Rating: {selectedCourse.rating || "4.8"} ★</span>
                  <span>Level: {selectedCourse.level || "Intermediate"}</span>
                </div>
              </div>
            )}

            {playerTab === "notes" && (
              <div className="flex flex-col gap-4">
                <div className="flex justify-between items-center text-[10px] text-slate-500 font-bold uppercase tracking-wider">
                  <span>Jot down notes while watching</span>
                  {notesStatus && (
                    <span className={`font-mono ${notesStatus === "Saving..." ? "text-indigo-500" : "text-emerald-500"}`}>
                      ● {notesStatus}
                    </span>
                  )}
                </div>

                <textarea
                  placeholder="Start typing notes... Your draft is saved automatically every 3 seconds."
                  value={notepadText}
                  onChange={(e) => setNotepadText(e.target.value)}
                  rows={4}
                  className="w-full bg-slate-50 dark:bg-slate-955 border border-slate-205 dark:border-slate-800 rounded-2xl p-4 text-xs text-slate-800 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}

            {playerTab === "resources" && (
              <div className="flex flex-col gap-3 text-xs text-slate-650 dark:text-slate-400 font-semibold">
                <h4 className="text-slate-800 dark:text-white font-bold text-xs">Handbooks & Resources</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-1">
                  <a 
                    href={currentLesson.pdf_url || "#"} 
                    target="_blank" 
                    rel="noreferrer"
                    className="p-4 bg-slate-50 dark:bg-slate-950 border border-slate-202 dark:border-slate-850 rounded-2xl flex items-center gap-3 hover:border-indigo-500/30 transition-all cursor-pointer"
                  >
                    <FileText className="text-indigo-500" size={20} />
                    <div className="text-left">
                      <span className="font-bold text-slate-700 dark:text-slate-350 block">Module Study Guide</span>
                      <span className="text-[10px] text-slate-500">Download reference handbook PDF</span>
                    </div>
                  </a>

                  <div className="p-4 bg-slate-50 dark:bg-slate-950 border border-slate-202 dark:border-slate-855 rounded-2xl flex items-center gap-3">
                    <Code className="text-emerald-500" size={20} />
                    <div className="text-left">
                      <span className="font-bold text-slate-700 dark:text-slate-350 block">Interactive Sandbox</span>
                      <span className="text-[10px] text-slate-500">Execute code via terminal console</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {playerTab === "transcript" && (
              <div className="text-xs text-slate-650 dark:text-slate-400 space-y-3.5 max-h-52 overflow-y-auto scrollbar-thin pr-2">
                <h4 className="text-slate-800 dark:text-white font-bold text-xs">Video Transcription</h4>
                <div className="flex flex-col gap-3 font-semibold">
                  {[
                    { time: 0, text: "Welcome to this structured learning lecture. Today we are exploring core building blocks." },
                    { time: 6, text: "Let's first understand the architectural schema and why the engine works this way." },
                    { time: 15, text: "Next, we will go through some practical code implementation and step-by-step executions." },
                    { time: 30, text: "In conclusion, make sure to test these algorithms inside your local dev console sandbox." }
                  ].map((line, i) => (
                    <div key={i} className="flex gap-4 items-start hover:bg-slate-55 dark:hover:bg-slate-950 p-1.5 rounded-xl transition-all">
                      <button 
                        onClick={() => {
                          if (videoRef.current) {
                            videoRef.current.currentTime = line.time;
                            if (!isPlaying) togglePlay();
                          }
                        }}
                        className="text-[10px] font-mono font-bold text-indigo-500 hover:underline shrink-0 cursor-pointer"
                      >
                        {formatTime(line.time)}
                      </button>
                      <p className="leading-relaxed">{line.text}</p>
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
                    <div className="p-6 bg-slate-55 dark:bg-slate-950 border border-slate-202 dark:border-slate-850 rounded-2xl text-center text-xs text-slate-500 font-bold">
                      No discussion threads started yet. Be the first to start a thread!
                    </div>
                  ) : (
                    forumPosts.map((post) => (
                      <div key={post.id} className="p-3.5 bg-slate-50 dark:bg-slate-950 border border-slate-202 dark:border-slate-850 rounded-2xl text-xs">
                        <h5 className="font-extrabold text-slate-850 dark:text-white leading-tight">{post.title}</h5>
                        <p className="text-slate-650 dark:text-slate-400 mt-1 text-[11px] font-semibold leading-relaxed">{post.content}</p>
                        
                        <div className="flex justify-between items-center text-[10px] text-slate-500 mt-3 border-t border-slate-102 dark:border-slate-850 pt-2 font-bold font-mono">
                          <span>By {post.author} • {post.date}</span>
                          <span>{post.repliesCount} replies</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                <div className="border-t border-slate-102 dark:border-slate-850 pt-4 flex flex-col gap-3">
                  <span className="text-xs font-bold text-slate-800 dark:text-white">Start a new thread</span>
                  <input
                    type="text"
                    placeholder="Thread title..."
                    value={newPostTitle}
                    onChange={(e) => setNewPostTitle(e.target.value)}
                    className="bg-slate-50 dark:bg-slate-955 border border-slate-202 dark:border-slate-800 rounded-xl p-2.5 text-xs text-slate-800 dark:text-slate-100 focus:outline-none"
                  />
                  <textarea
                    placeholder="Type details..."
                    value={newPostContent}
                    onChange={(e) => setNewPostContent(e.target.value)}
                    rows={2}
                    className="bg-slate-50 dark:bg-slate-955 border border-slate-202 dark:border-slate-805 rounded-xl p-2.5 text-xs text-slate-850 dark:text-slate-100 focus:outline-none"
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

        {/* ROADMAP CHECKLIST SYLLABUS COLUMN (4/12) */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          <div className="bg-white dark:bg-slate-900 border border-slate-202 dark:border-slate-800 rounded-3xl p-6 shadow-sm flex flex-col gap-4">
            <div>
              <h4 className="text-[10px] font-black uppercase tracking-wider text-slate-400 font-mono">Syllabus Navigation</h4>
              <h3 className="text-sm font-black text-slate-800 dark:text-white mt-1 leading-snug">Modules Roadmap</h3>
            </div>

            <div className="flex flex-col gap-4.5 mt-2 max-h-[600px] overflow-y-auto pr-1 scrollbar-thin">
              {curriculum?.sections?.map((section: any) => (
                <div key={section.id} className="space-y-3">
                  <span className="text-[10px] font-black text-indigo-600 dark:text-indigo-400 block border-b border-slate-100 dark:border-slate-850 pb-1.5 uppercase tracking-wider font-mono">
                    {section.title.split(":")[0]}
                  </span>

                  <div className="flex flex-col gap-2.5">
                    {section.lessons?.map((less: any) => {
                      const completed = completedLessonIds.includes(less.id);
                      const isLocked = less.is_locked;
                      const active = currentLesson.id === less.id;

                      // Sidebar visual state derivations
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
                            setCurrentLesson(less);
                            setPlayerTab("overview");
                          }}
                          className={`flex items-center justify-between p-3.5 rounded-2xl border text-left text-xs transition-all w-full cursor-pointer relative overflow-hidden ${
                            active
                              ? "bg-indigo-50 border-indigo-200 dark:bg-indigo-950/20 dark:border-indigo-800/60 text-indigo-650 dark:text-indigo-400 font-extrabold shadow-sm"
                              : isLocked
                                ? "bg-slate-50 dark:bg-slate-950 border-slate-100 dark:border-slate-900 text-slate-400 opacity-60 cursor-not-allowed"
                                : "bg-white dark:bg-slate-900 border-slate-202 dark:border-slate-800 text-slate-750 dark:text-slate-350 hover:border-indigo-500/20"
                          }`}
                        >
                          <div className="flex items-center gap-2.5 min-w-0 pr-2 relative z-10">
                            {completed ? (
                              <CheckCircle2 size={15} className="text-emerald-500 shrink-0" />
                            ) : isLocked ? (
                              <Lock size={14} className="text-slate-400 shrink-0" />
                            ) : active ? (
                              <Play size={14} className="text-blue-500 shrink-0 animate-bounce" />
                            ) : (
                              <ChevronRight size={14} className="text-indigo-500 shrink-0" />
                            )}
                            <span className="truncate font-semibold text-slate-850 dark:text-slate-200">{less.title}</span>
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0 relative z-10">
                            <span className={`text-[8px] font-mono font-bold px-2 py-0.5 rounded-full uppercase ${stateColor}`}>
                              {stateLabel}
                            </span>
                          </div>
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

function extractYouTubeId(url: string): string | null {
  if (!url) return null;
  const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
  const match = url.match(regExp);
  return (match && match[2].length === 11) ? match[2] : null;
}
