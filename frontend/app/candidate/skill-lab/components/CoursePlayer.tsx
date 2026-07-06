"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import Script from "next/script";
import { apiService } from "@/services/api";
import { useAuthStore } from "@/store/authStore";
import { 
  Play, Pause, BookOpen, Brain, Trash2, ArrowRight, Clock, ShieldAlert, 
  RefreshCw, Upload, Code, CheckCircle, Volume2, VolumeX, Maximize2, 
  Minimize2, Lock, Sparkles, Award, FileText, CheckCircle2, ChevronRight,
  MessageSquare, Loader2, Flame, HelpCircle, Star
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
  const [playerTab, setPlayerTab] = useState<"overview" | "summary" | "notes" | "resources" | "transcript" | "discussion">("overview");

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
  const [isChatActive, setIsChatActive] = useState(false);

  // AI Summary Tab States
  const [lessonSummaries, setLessonSummaries] = useState<Record<string, string>>({});
  const [generatingSummary, setGeneratingSummary] = useState<Record<string, boolean>>({});
  const streamIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // AI Mentor Sidebar Chat Widget States
  const [mentorSessionId, setMentorSessionId] = useState<string | null>(null);
  const [mentorMessages, setMentorMessages] = useState<any[]>([]);
  const [mentorInput, setMentorInput] = useState("");
  const [loadingMentor, setLoadingMentor] = useState(false);

  // Collapse/Expand Module helper - Only one expanded at a time
  const toggleModule = (modId: string) => {
    setExpandedModules((prev: string[]) => 
      prev.includes(modId) ? [] : [modId]
    );
  };

  // Clean up streaming on unmount
  useEffect(() => {
    return () => {
      if (streamIntervalRef.current) {
        clearInterval(streamIntervalRef.current);
      }
    };
  }, []);

  // Clear streaming when lesson changes
  useEffect(() => {
    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current);
      streamIntervalRef.current = null;
    }
  }, [currentLesson]);

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
          if (msgs && msgs.length > 0) {
            setIsChatActive(true);
          }
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
    
    setIsChatActive(true);
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


  const handleGenerateSummary = async (force = false) => {
    if (!mentorSessionId || generatingSummary[currentLesson.id]) return;
    if (!force && lessonSummaries[currentLesson.id]) return;
    
    setGeneratingSummary(prev => ({ ...prev, [currentLesson.id]: true }));
    
    const transcriptText = getLessonTranscriptText(currentLesson);
    const prompt = `Please generate an AI summary for the lesson "${currentLesson.title}" based on the following video transcript:
    
    "${transcriptText}"
    
    Format the output exactly under these markdown headers:
    ### Summary
    [Brief paragraph explaining the lesson concept]
    
    ### Key Concepts
    [3 bullet points]
    
    ### Real-world Uses
    [2 bullet points]
    
    ### Best Practices
    [2 bullet points]
    
    ### Common Mistakes
    [2 bullet points]
    
    ### Important Points
    [2 bullet points]`;
    
    try {
      const res = await apiService.sendAIMentorChat(mentorSessionId, prompt, "tutor");
      if (res && res.response) {
        const responseText = res.response;
        
        // Simulating streaming of words
        const words = responseText.split(" ");
        let currentText = "";
        let wordIdx = 0;
        
        setGeneratingSummary(prev => ({ ...prev, [currentLesson.id]: false }));
        setLessonSummaries(prev => ({ ...prev, [currentLesson.id]: "" }));
        
        if (streamIntervalRef.current) {
          clearInterval(streamIntervalRef.current);
        }
        
        streamIntervalRef.current = setInterval(() => {
          if (wordIdx < words.length) {
            currentText += (wordIdx === 0 ? "" : " ") + words[wordIdx];
            setLessonSummaries(prev => ({ ...prev, [currentLesson.id]: currentText }));
            wordIdx++;
          } else {
            if (streamIntervalRef.current) {
              clearInterval(streamIntervalRef.current);
              streamIntervalRef.current = null;
            }
          }
        }, 15);
      }
    } catch (err) {
      console.error("Failed to generate AI Summary:", err);
      setGeneratingSummary(prev => ({ ...prev, [currentLesson.id]: false }));
      setLessonSummaries(prev => ({ 
        ...prev, 
        [currentLesson.id]: "### Error\nFailed to connect to the AI service. Please verify your connection and try again." 
      }));
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
    <div className="w-full flex flex-col gap-8 text-slate-800 dark:text-slate-100">
      
      {/* Dynamic Success Overlay */}
      {showSuccessOverlay && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm transition-all duration-300"
        >
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 max-w-md text-center shadow-xl flex flex-col items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 flex items-center justify-center animate-bounce shadow-sm">
              <Award size={32} />
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Lesson Completed!</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              You've successfully validated this lesson with strict watch compliance.
            </p>
            <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 px-4 py-2 rounded-xl text-emerald-600 dark:text-emerald-400 font-extrabold text-sm">
              <Sparkles size={16} />
              <span>+{xpEarnedAlert} XP Earned</span>
            </div>
          </div>
        </div>
      )}

      {/* Course Hero & Progress Card Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
        
        {/* Left Column: Course Hero Details (No Continue Learning Button) */}
        <div className="lg:col-span-8 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 flex flex-col justify-center gap-4 shadow-xs">
          <div className="space-y-3.5">
            {/* Metadata Badges */}
            <div className="flex flex-wrap items-center gap-2.5 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
              <span>{selectedCourse.title?.toUpperCase().includes("HTML") ? "HTML5 Development" : "Docker Fundamentals"}</span>
              <span>•</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-extrabold">Beginner</span>
              <span>•</span>
              <span>{curriculum?.sections?.length || 0} Modules</span>
              <span>•</span>
              <span>4.5 Hours</span>
              <span>•</span>
              <span>12K Learners</span>
              <span>•</span>
              <span>Updated Jun 2026</span>
            </div>

            {/* Course Title */}
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white leading-tight">
              {selectedCourse.title}
            </h2>

            {/* Rating */}
            <div className="flex items-center gap-1.5 text-xs text-amber-500 font-semibold">
              <div className="flex items-center gap-0.5">
                <Star size={13} className="fill-current" />
                <Star size={13} className="fill-current" />
                <Star size={13} className="fill-current" />
                <Star size={13} className="fill-current" />
                <Star size={13} className="fill-current opacity-40" />
              </div>
              <span className="text-slate-700 dark:text-slate-300 font-bold">4.8</span>
              <span className="text-slate-400 dark:text-slate-500">(1.2K ratings)</span>
            </div>
          </div>
        </div>

        {/* Right Column: Progress Card */}
        <div className="lg:col-span-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 flex flex-col justify-between gap-5 shadow-xs">
          <div className="space-y-3">
            <div className="flex justify-between items-end">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 font-mono">Your Progress</span>
              <span className="text-xl font-bold text-slate-900 dark:text-white font-mono leading-none">{courseProgressPercent}%</span>
            </div>
            
            {/* Linear Progress Bar */}
            <div className="w-full h-1.5 bg-slate-105 dark:bg-slate-800 rounded-full overflow-hidden">
              <div 
                className="h-full bg-blue-600 dark:bg-blue-500 transition-all duration-300" 
                style={{ width: `${courseProgressPercent}%` }} 
              />
            </div>

            <div className="flex justify-between items-center text-[10px] text-slate-500 dark:text-slate-400 font-medium">
              <span>{completedLessonIds.length} of {curriculum.sections?.flatMap((s: any) => s.lessons || []).length || 48} lessons</span>
              <span>Today's Goal: 40%</span>
            </div>
          </div>

          {/* Streak & Stats Row */}
          <div className="border-t border-slate-100 dark:border-slate-805 pt-4 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-bold text-orange-500">
              <Flame size={14} className="fill-current" />
              <span>{userStats.streak} Day Streak</span>
            </div>
            <div className="text-xs text-slate-500 dark:text-slate-400 font-bold">
              Level {1 + Math.floor(userStats.xp / 100)} • {userStats.xp} XP
            </div>
          </div>
        </div>

      </div>

      {/* Main Content Layout Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* LEFT PLAYER COLUMN (8/12) */}
        <div className="lg:col-span-8 flex flex-col gap-8">
          
          {/* Constrained Aspect-Video Player Box */}
          <div className="w-full max-w-[850px] mx-auto lg:mx-0 flex flex-col gap-4">
            
            {/* Breadcrumb line for lesson context */}
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500 uppercase tracking-widest">
                {activeModuleTitle.split(":")[0]} • Lesson {1 + (curriculum.sections?.flatMap((s: any) => s.lessons || []).findIndex((l: any) => l.id === currentLesson.id) || 0)}
              </span>
              <button 
                onClick={triggerLessonCompletion}
                disabled={completedLessonIds.includes(currentLesson.id)}
                className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition-all cursor-pointer shrink-0 border flex items-center gap-1 ${
                  completedLessonIds.includes(currentLesson.id)
                    ? "bg-emerald-50 border-emerald-205 text-emerald-650 dark:bg-emerald-950/20 dark:border-emerald-800/40 cursor-not-allowed"
                    : "bg-white border-slate-200 text-slate-700 hover:border-slate-300 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-200"
                }`}
              >
                <CheckCircle size={11} className={completedLessonIds.includes(currentLesson.id) ? "text-emerald-500" : "text-slate-400"} />
                <span>{completedLessonIds.includes(currentLesson.id) ? "Completed" : "Mark as Complete"}</span>
              </button>
            </div>

            <div 
              ref={playerContainerRef}
              className="relative aspect-video w-full bg-black rounded-xl overflow-hidden shadow-xs select-none group border border-slate-200 dark:border-slate-800/80"
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
                    <div className="absolute inset-0 bg-black/65 flex flex-col items-center justify-center gap-3 z-40">
                      <RefreshCw className="animate-spin text-blue-500" size={24} />
                      <span className="text-[9px] text-slate-300 font-bold uppercase tracking-wider">Streaming Video...</span>
                    </div>
                  )}

                  {videoError && (
                    <div className="absolute inset-0 bg-slate-900 flex flex-col items-center justify-center gap-3 text-center p-6 z-40">
                      <ShieldAlert size={36} className="text-red-500" />
                      <div>
                        <h4 className="text-xs font-bold text-white">{videoError}</h4>
                        <p className="text-[9px] text-slate-400 mt-1 max-w-xs mx-auto leading-normal">
                          YouTube Embed failed to initialize. If issues persist, verify shields or privacy extensions.
                        </p>
                      </div>
                      <button 
                        onClick={handleReloadVideo}
                        className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition-all shadow-sm"
                      >
                        Retry Load
                      </button>
                    </div>
                  )}

                  {!isPlaying && !videoError && !isLoading && (
                    <button 
                      onClick={togglePlay}
                      className="absolute inset-0 flex items-center justify-center bg-black/20 hover:bg-black/30 transition-all cursor-pointer z-30 pointer-events-auto"
                    >
                      <div className="w-14 h-14 rounded-full bg-white/10 hover:bg-white/20 border border-white/30 text-white flex items-center justify-center shadow-lg backdrop-blur-sm transition-transform hover:scale-105">
                        <Play size={20} className="fill-current ml-0.5" />
                      </div>
                    </button>
                  )}

                  {autoNextCount !== null && (
                    <div className="absolute inset-0 bg-slate-900/95 flex flex-col items-center justify-center gap-4 text-center p-6 z-40">
                      <Sparkles className="text-blue-400 animate-pulse" size={32} />
                      <div>
                        <h3 className="text-sm font-bold text-white">Video completed!</h3>
                        <p className="text-[11px] text-slate-405 mt-1">
                          Up next: <span className="text-blue-400 font-extrabold">{nextLesson?.title}</span>
                        </p>
                      </div>
                      <div className="text-lg font-bold text-white font-mono bg-slate-800/40 border border-slate-700/30 px-4 py-2 rounded-xl">
                        Starting in {autoNextCount}s...
                      </div>
                      <div className="flex gap-2.5">
                        <button 
                          onClick={() => {
                            cancelAutoNext();
                            if (nextLesson) setCurrentLesson(nextLesson);
                          }}
                          className="px-4 py-2 bg-blue-600 hover:bg-blue-705 text-white text-xs font-bold rounded-lg shadow-sm cursor-pointer"
                        >
                          Open Now
                        </button>
                        <button 
                          onClick={cancelAutoNext}
                          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-355 text-xs font-bold rounded-lg border border-slate-700 cursor-pointer"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}

                  {!videoError && !isLoading && (
                    <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/80 via-black/30 to-transparent flex flex-col gap-2 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity duration-300 z-20">
                      <div className="flex items-center gap-2.5 w-full">
                        <span className="text-[9px] text-slate-300 font-mono font-bold">{formatTime(currentTime)}</span>
                        <div className="flex-1 h-1 rounded bg-slate-800/60 relative overflow-hidden select-none pointer-events-none">
                          <div 
                            className="absolute top-0 left-0 h-full bg-blue-500 transition-all duration-100"
                            style={{ width: `${duration > 0 ? (currentTime / duration) * 100 : 0}%` }}
                          />
                        </div>
                        <span className="text-[9px] text-slate-300 font-mono font-bold">{formatTime(duration)}</span>
                      </div>

                      <div className="flex justify-between items-center w-full">
                        <div className="flex items-center gap-3.5 text-white">
                          <button onClick={togglePlay} className="hover:text-blue-400 transition-colors cursor-pointer outline-none">
                            {isPlaying ? <Pause size={14} /> : <Play size={14} />}
                          </button>
                          <button onClick={toggleMute} className="hover:text-blue-400 transition-colors cursor-pointer outline-none">
                            {isMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
                          </button>
                          <span className="text-[9px] text-slate-400 font-mono">
                            {playbackRate !== 1 ? `${playbackRate}x` : "Normal"}
                          </span>
                        </div>
                        <div className="flex items-center gap-3.5 text-white">
                          <button 
                            onClick={togglePlaybackRate} 
                            className="hover:text-blue-400 transition-colors cursor-pointer outline-none text-[9px] font-bold border border-slate-700 px-1.5 py-0.5 rounded"
                          >
                            Speed
                          </button>
                          <button onClick={toggleFullscreen} className="hover:text-blue-400 transition-colors cursor-pointer outline-none">
                            <Maximize2 size={14} />
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              ) : currentLesson.type === "pdf" ? (
                <div className="bg-slate-50 dark:bg-slate-950 p-6 min-h-[350px] flex flex-col justify-between items-center text-center">
                  <div className="my-auto flex flex-col items-center gap-4">
                    <div className="w-14 h-14 rounded-xl bg-blue-50 dark:bg-blue-955/20 text-blue-600 dark:text-blue-450 border border-blue-105 dark:border-blue-900/30 flex items-center justify-center">
                      <BookOpen size={28} />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900 dark:text-white">{currentLesson.title}</h4>
                      <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-1 max-w-xs mx-auto leading-normal">
                        Click below to open and study the handbook PDF for this module.
                      </p>
                    </div>
                  </div>
                  <a
                    href={currentLesson.pdf_url}
                    target="_blank"
                    rel="noreferrer"
                    className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold shadow-sm cursor-pointer transition-all hover:scale-105"
                  >
                    Download Handbook PDF
                  </a>
                </div>
              ) : currentLesson.type === "quiz" && currentLesson.quiz ? (
                <div className="bg-slate-50 dark:bg-slate-950 p-5 flex flex-col gap-4 max-h-[480px] overflow-y-auto">
                  {quizSubmitted ? (
                    <div className="my-auto text-center flex flex-col items-center gap-4 py-8">
                      <div className="w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 flex items-center justify-center text-lg font-bold">
                        ✓
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-slate-900 dark:text-white">Quiz Completed!</h4>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                          Your Score: <span className="font-extrabold text-emerald-600 dark:text-emerald-400">{quizScore}%</span>
                        </p>
                      </div>
                      <button
                        onClick={() => {
                          setQuizAnswers({});
                          setQuizSubmitted(false);
                          setQuizScore(null);
                        }}
                        className="px-4 py-2 bg-white border border-slate-202 text-slate-700 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-200 text-xs font-bold rounded-lg cursor-pointer"
                      >
                        Retry Quiz
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-5">
                      {currentLesson.quiz.questions.map((q: any, qIdx: number) => (
                        <div key={q.id} className="p-4 bg-white border border-slate-200 dark:bg-slate-900 dark:border-slate-800 rounded-xl flex flex-col gap-2.5">
                          <span className="text-[8px] font-mono text-slate-400 dark:text-slate-500 uppercase tracking-widest">Question {qIdx + 1}</span>
                          <span className="text-xs font-bold text-slate-805 dark:text-slate-100">{q.question}</span>
                          <div className="grid grid-cols-1 gap-2 mt-1">
                            {q.options?.map((opt: string, optIdx: number) => (
                              <button
                                key={optIdx}
                                onClick={() => setQuizAnswers(prev => ({ ...prev, [qIdx]: optIdx }))}
                                className={`p-2.5 rounded-lg border text-left text-xs font-medium transition-all cursor-pointer ${
                                  quizAnswers[qIdx] === optIdx
                                    ? "bg-blue-50 border-blue-400 text-blue-700 dark:bg-blue-955/20 dark:border-blue-800 dark:text-blue-300"
                                    : "bg-slate-50 border-slate-200 hover:border-slate-300 dark:bg-slate-950 dark:border-slate-850 dark:text-slate-400 dark:hover:border-slate-700"
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
                          className="px-5 py-2 bg-blue-600 hover:bg-blue-705 text-white disabled:bg-slate-200 disabled:text-slate-400 dark:disabled:bg-slate-805 dark:disabled:text-slate-600 text-xs font-bold rounded-lg cursor-pointer disabled:cursor-not-allowed shadow-sm"
                        >
                          Submit Answers
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : currentLesson.type === "written_assessment" && currentLesson.written_assessment ? (
                <div className="bg-slate-50 dark:bg-slate-955 p-5 flex flex-col gap-4 max-h-[480px] overflow-y-auto">
                  {currentLesson.written_assessment.passed ? (
                    <div className="my-auto text-center flex flex-col items-center gap-4 py-8">
                      <div className="w-12 h-12 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 flex items-center justify-center text-lg font-bold">
                        ✓
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-slate-900 dark:text-white">Assessment Evaluated!</h4>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                          Best Score: <span className="font-bold text-emerald-600 dark:text-emerald-405">{currentLesson.written_assessment.best_score}%</span>
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {currentLesson.written_assessment.questions.map((q: any, qIdx: number) => (
                        <div key={q.id} className="p-4 bg-white border border-slate-200 dark:bg-slate-900 dark:border-slate-800 rounded-xl flex flex-col gap-2">
                          <span className="text-[8px] font-mono text-slate-455 dark:text-slate-505 uppercase tracking-widest">Question {qIdx + 1}</span>
                          <span className="text-xs font-bold text-slate-800 dark:text-slate-200 leading-relaxed">{q.question_text}</span>
                          <textarea
                            value={writtenAnswers[qIdx] || ""}
                            onChange={(e) => setWrittenAnswers(prev => ({ ...prev, [qIdx]: e.target.value }))}
                            rows={3}
                            placeholder="Write your explanation here..."
                            className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 dark:bg-slate-950 dark:border-slate-850 dark:text-slate-200 resize-none font-medium mt-1"
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
                          className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg cursor-pointer shadow-sm"
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
            <div className="flex gap-5 border-b border-slate-200 dark:border-slate-800 pb-2 mt-4 overflow-x-auto scrollbar-hide shrink-0">
              {[
                { id: "overview", label: "Overview" },
                { id: "summary", label: "AI Summary" },
                { id: "notes", label: "Notes" },
                { id: "resources", label: "Resources" },
                { id: "transcript", label: "Transcript" },
                { id: "discussion", label: "Discussion" }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setPlayerTab(tab.id as any)}
                  className={`text-xs font-bold pb-2 transition-all border-b-2 cursor-pointer ${
                    playerTab === tab.id
                      ? "border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400 font-extrabold"
                      : "border-transparent text-slate-500 hover:text-slate-800"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Video Sub-Tabs Content */}
            <div className="mt-4 min-h-[160px]">
              {playerTab === "overview" && (
                <div className="space-y-4 text-xs font-medium text-slate-600 dark:text-slate-400 leading-relaxed">
                  <div className="space-y-1">
                    <h4 className="text-slate-900 dark:text-white font-bold text-xs">About this lesson</h4>
                    <p>
                      {currentLesson.description || "Learn the concepts of HTML5 Development. This lesson goes through basic syntax, configurations, and core workflows inside candidates' skill labs."}
                    </p>
                  </div>
                  {activeModuleGoal && (
                    <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80">
                      <span className="text-[9px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 font-mono">Module Goal</span>
                      <p className="text-[11px] text-slate-500 mt-0.5 leading-normal">{activeModuleGoal}</p>
                    </div>
                  )}
                </div>
              )}

              {playerTab === "summary" && (
                <div className="space-y-4">
                  <div className="flex justify-between items-center pb-2 border-b border-slate-100 dark:border-slate-800/60">
                    <h4 className="text-slate-900 dark:text-white font-bold text-xs">AI Summary</h4>
                    {lessonSummaries[currentLesson.id] && (
                      <button
                        onClick={() => handleGenerateSummary(true)}
                        className="text-[10px] text-blue-600 dark:text-blue-400 font-bold hover:underline cursor-pointer"
                      >
                        Regenerate Summary
                      </button>
                    )}
                  </div>
                  
                  {!lessonSummaries[currentLesson.id] && !generatingSummary[currentLesson.id] ? (
                    <div className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-6 rounded-xl text-center space-y-3">
                      <Sparkles className="text-blue-500 mx-auto" size={24} />
                      <p className="text-xs text-slate-500 dark:text-slate-400 font-semibold">
                        Get an AI summary for the currently playing lesson video.
                      </p>
                      <button
                        onClick={() => handleGenerateSummary()}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-lg shadow-sm cursor-pointer"
                      >
                        Generate Summary
                      </button>
                    </div>
                  ) : generatingSummary[currentLesson.id] ? (
                    <div className="bg-slate-50 dark:bg-slate-955 border border-slate-205 dark:border-slate-800 p-6 rounded-xl text-center space-y-2">
                      <RefreshCw className="animate-spin text-blue-500 mx-auto" size={24} />
                      <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                        Analyzing video transcript and generating summary...
                      </p>
                    </div>
                  ) : (
                    <div className="prose dark:prose-invert max-w-none text-xs leading-relaxed text-slate-700 dark:text-slate-300 font-medium space-y-4">
                      {parseAndRenderSummary(lessonSummaries[currentLesson.id])}
                    </div>
                  )}
                </div>
              )}

              {playerTab === "notes" && (
                <div className="space-y-3">
                  <h4 className="text-slate-900 dark:text-white font-bold text-xs font-black">Class Notes</h4>
                  <textarea
                    value={notepadText}
                    onChange={(e) => setNotepadText(e.target.value)}
                    rows={4}
                    placeholder="Type lesson notes..."
                    className="w-full bg-slate-50 dark:bg-slate-955 border border-slate-200 dark:border-slate-800 rounded-lg p-3 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:border-blue-505 resize-y font-medium"
                  />
                  <div className="flex justify-end gap-2.5">
                    <button
                      onClick={() => setNotepadText("")}
                      className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300 text-xs font-bold rounded-lg cursor-pointer"
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
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg shadow-sm cursor-pointer"
                    >
                      Save Note
                    </button>
                  </div>
                </div>
              )}

              {playerTab === "resources" && (
                <div className="space-y-2">
                  <h4 className="text-slate-900 dark:text-white font-bold text-xs">Resources & Assets</h4>
                  <div className="grid grid-cols-1 gap-2">
                    {[
                      { title: "HTML5 Official Cheatsheet (W3C)", format: "PDF", size: "1.2 MB" },
                      { title: "Sample HTML5 Practice Workspace Setup", format: "ZIP", size: "4.5 MB" }
                    ].map((item, idx) => (
                      <div key={idx} className="p-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded bg-blue-50 dark:bg-blue-955/40 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-[9px] shrink-0">
                            {item.format}
                          </div>
                          <div>
                            <div className="text-xs font-bold text-slate-800 dark:text-slate-205">{item.title}</div>
                            <div className="text-[8px] text-slate-405 font-bold font-mono">{item.size}</div>
                          </div>
                        </div>
                        <button className="text-blue-600 dark:text-blue-400 font-extrabold text-[9px] uppercase hover:underline cursor-pointer">
                          Download
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {playerTab === "transcript" && (
                <div className="space-y-3 max-h-[250px] overflow-y-auto pr-1">
                  <h4 className="text-slate-900 dark:text-white font-bold text-xs">Transcription</h4>
                  <div className="space-y-2.5">
                    {[
                      { time: 0, speaker: "Instructor", text: "Welcome to this course. Today we are setting up our local workspace." },
                      { time: 45, speaker: "Instructor", text: "Let's open VS Code and write our skeleton tags." }
                    ].map((line, idx) => (
                      <div key={idx} className="flex gap-2.5 text-xs">
                        <span className="font-mono font-bold text-blue-600 dark:text-blue-400 shrink-0 bg-blue-50 dark:bg-blue-955/40 px-1.5 py-0.5 rounded text-[9px]">
                          {formatTime(line.time)}
                        </span>
                        <p className="text-slate-600 dark:text-slate-400"><span className="font-bold">{line.speaker}:</span> {line.text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {playerTab === "discussion" && (
                <div className="space-y-2">
                  <h4 className="text-slate-900 dark:text-white font-bold text-xs">Student Q&A</h4>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Ask a question..."
                      className="flex-1 bg-slate-50 dark:bg-slate-950 border border-slate-202 dark:border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-800 dark:text-slate-200 placeholder-slate-405 focus:outline-none focus:border-blue-500 font-medium"
                    />
                    <button className="px-4 py-2 bg-blue-600 hover:bg-blue-705 text-white text-xs font-bold rounded-lg shadow-sm cursor-pointer">
                      Ask
                    </button>
                  </div>
                </div>
              )}
            </div>

          </div>
        </div>

        {/* RIGHT SIDEBAR WIDGETS COLUMN (4/12) - Entire Sidebar is Sticky */}
        <div className="lg:col-span-4 flex flex-col gap-8 lg:sticky lg:top-6 self-start max-h-[calc(100vh-4rem)] overflow-y-auto pr-1 scrollbar-none">
          
          {/* Section: Progress Card */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 flex flex-col justify-between gap-5 shadow-xs">
            <div className="space-y-3">
              <div className="flex justify-between items-end">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 font-mono">Your Progress</span>
                <span className="text-xl font-bold text-slate-900 dark:text-white font-mono leading-none">{courseProgressPercent}%</span>
              </div>
              
              {/* Linear Progress Bar */}
              <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-blue-600 dark:bg-blue-500 transition-all duration-300" 
                  style={{ width: `${courseProgressPercent}%` }} 
                />
              </div>

              <div className="flex justify-between items-center text-[10px] text-slate-500 dark:text-slate-405 font-medium">
                <span>{completedLessonIds.length} of {curriculum.sections?.flatMap((s: any) => s.lessons || []).length || 48} lessons</span>
                <span>Today's Goal: 40%</span>
              </div>
            </div>

            {/* Streak & Stats Row */}
            <div className="border-t border-slate-100 dark:border-slate-800/80 pt-4 flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-bold text-orange-500">
                <Flame size={14} className="fill-current" />
                <span>{userStats.streak} Day Streak</span>
              </div>
              <div className="text-xs text-slate-505 dark:text-slate-400 font-bold">
                Level {1 + Math.floor(userStats.xp / 100)} • {userStats.xp} XP
              </div>
            </div>
          </div>

          {/* Section: Modules Content Roadmap (Fixed Height scroll container) */}
          <div className="space-y-3 flex flex-col">
            <span className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500 font-mono tracking-wider">Modules Content</span>
            
            {/* Independently Scrollable Container */}
            <div className="flex flex-col gap-2 h-[500px] max-h-[550px] overflow-y-auto pr-1.5 custom-scrollbar bg-slate-50/20 dark:bg-slate-950/10 p-1 rounded-lg border border-slate-100 dark:border-slate-850">
              {curriculum?.sections?.map((section: any, secIdx: number) => {
                const totalInSec = section.lessons?.length || 0;
                const completedInSec = section.lessons?.filter((l: any) => completedLessonIds.includes(l.id))?.length || 0;
                const sectionNo = secIdx + 1;
                const isExpanded = expandedModules.includes(section.id);
                
                return (
                  <div key={section.id} className="border border-slate-202 dark:border-slate-800 rounded-lg overflow-hidden bg-white dark:bg-slate-900 shadow-xs">
                    <button
                      onClick={() => toggleModule(section.id)}
                      className="w-full px-3.5 py-3 flex justify-between items-center text-left text-xs font-bold text-slate-800 dark:text-white hover:bg-slate-50 dark:hover:bg-slate-850/50 transition-colors cursor-pointer"
                    >
                      <div className="flex flex-col pr-2">
                        <span className="text-[8px] font-mono text-blue-600 dark:text-blue-400 uppercase tracking-widest">
                          Module {sectionNo}
                        </span>
                        <span className="mt-0.5 text-slate-808 dark:text-slate-100 text-xs font-bold truncate max-w-[150px]">
                          {section.title.split(":").slice(1).join(":") || section.title}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-[8px] font-mono font-bold bg-slate-100 dark:bg-slate-800 text-slate-550 dark:text-slate-400 px-2 py-0.5 rounded-full">
                          {completedInSec}/{totalInSec} Completed
                        </span>
                        <ChevronRight 
                          size={13} 
                          className={`text-slate-400 transition-transform duration-300 ${isExpanded ? "transform rotate-90" : ""}`} 
                        />
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="p-2 border-t border-slate-100 dark:border-slate-800/80 flex flex-col gap-1.5 bg-white dark:bg-slate-900">
                        {section.lessons?.map((less: any) => {
                          const completed = completedLessonIds.includes(less.id);
                          const isLocked = less.is_locked;
                          const active = currentLesson.id === less.id;

                          let stateLabel = "Available";
                          let stateColor = "text-blue-500 bg-blue-500/10";
                          
                          if (completed) {
                            stateLabel = "Completed";
                            stateColor = "text-emerald-500 bg-emerald-500/10";
                          } else if (isLocked) {
                            stateLabel = "Locked";
                            stateColor = "text-slate-400 bg-slate-100 dark:bg-slate-805/40";
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
                              className={`flex items-center justify-between p-2.5 rounded border text-left text-xs transition-all w-full cursor-pointer relative overflow-hidden ${
                                active
                                  ? "bg-blue-50/50 border-blue-200 dark:bg-blue-955/20 dark:border-blue-800 text-blue-700 dark:text-blue-300 font-bold shadow-xs"
                                  : isLocked
                                    ? "bg-slate-50/50 dark:bg-slate-950/60 border-slate-100 dark:border-slate-850 text-slate-400 opacity-60 cursor-not-allowed"
                                    : "bg-white dark:bg-slate-900 border-slate-202 dark:border-slate-800 text-slate-705 dark:text-slate-300 hover:border-blue-500/20"
                              }`}
                            >
                              <div className="flex items-center justify-between w-full text-xs font-semibold">
                                <div className="flex items-center gap-2.5 min-w-0 pr-2">
                                  {completed ? (
                                    <CheckCircle2 size={13} className="text-emerald-500 shrink-0" />
                                  ) : isLocked ? (
                                    <Lock size={12} className="text-slate-400 shrink-0" />
                                  ) : active ? (
                                    <Play size={12} className="text-blue-500 shrink-0 animate-pulse" />
                                  ) : (
                                    <ChevronRight size={12} className="text-slate-400 shrink-0" />
                                  )}
                                  <span className="truncate text-slate-800 dark:text-slate-200">{less.title}</span>
                                </div>
                                <span className="text-[9px] text-slate-400 dark:text-slate-500 font-mono font-bold shrink-0">{less.duration || "10 min"}</span>
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

          {/* AI Mentor Box */}
          <div className="space-y-2.5">
            <span className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500 font-mono tracking-wider">Ask AI Mentor</span>
            
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 flex flex-col gap-3.5 shadow-sm">
              <div className="flex justify-between items-center pb-2 border-b border-slate-100 dark:border-slate-800/80">
                <span className="text-xs font-bold text-slate-800 dark:text-white">Study Helper</span>
                <div className="w-6 h-6 rounded-full bg-blue-50 dark:bg-blue-955/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                  <Brain size={12} />
                </div>
              </div>

              {!isChatActive && mentorMessages.length === 0 ? (
                <div className="space-y-3">
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed font-medium">
                    Need help? Ask AI to explain concepts, generate quick practice questions, or give career applications.
                  </p>
                  
                  <div className="flex flex-col gap-2">
                    {[
                      "Explain this lesson in simple terms",
                      "Generate a quick quiz for me",
                      "Career applications for this topic"
                    ].map((prompt, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSendMentorMessage(prompt)}
                        className="w-full text-left text-xs bg-slate-50 dark:bg-slate-950 hover:bg-blue-50/50 dark:hover:bg-blue-955/20 border border-slate-100 dark:border-slate-850 p-2.5 rounded-lg text-slate-600 dark:text-slate-300 font-medium transition-colors cursor-pointer"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="bg-slate-50 dark:bg-slate-955 border border-slate-200/60 dark:border-slate-800 rounded-lg p-2.5 flex flex-col gap-2.5 h-[200px] overflow-y-auto pr-1">
                  {mentorMessages.map((msg: any) => {
                    const isUser = msg.sender === "user";
                    return (
                      <div 
                        key={msg.id}
                        className={`flex flex-col max-w-[85%] rounded-lg px-2.5 py-1.5 text-xs leading-relaxed font-medium ${
                          isUser
                            ? "bg-blue-600 text-white self-end rounded-br-none shadow-xs"
                            : "bg-white border border-slate-202 dark:bg-slate-900 dark:border-slate-800 text-slate-805 dark:text-slate-200 self-start rounded-bl-none shadow-xs"
                        }`}
                      >
                        <span>{msg.message}</span>
                        <span className={`text-[7px] font-mono mt-1 ${isUser ? "text-blue-200 self-end" : "text-slate-400"}`}>
                          {msg.created_at ? new Date(msg.created_at).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : ""}
                        </span>
                      </div>
                    );
                  })}

                  {loadingMentor && (
                    <div className="bg-white border border-slate-200 dark:bg-slate-900 dark:border-slate-800 text-slate-400 self-start rounded-lg rounded-bl-none px-2.5 py-1.5 text-[10px] leading-normal font-semibold shadow-xs flex items-center gap-1.5">
                      <Loader2 size={11} className="animate-spin text-blue-500" />
                      <span className="text-[8px] font-mono uppercase tracking-wider font-bold">Thinking...</span>
                    </div>
                  )}
                </div>
              )}

              {/* Input & Send controls */}
              <div className="flex gap-2 border border-slate-202 dark:border-slate-800 p-1 rounded-lg bg-slate-50 dark:bg-slate-950">
                <input
                  type="text"
                  value={mentorInput}
                  onChange={(e) => setMentorInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && mentorInput.trim()) {
                      handleSendMentorMessage(mentorInput);
                    }
                  }}
                  placeholder="Ask AI Mentor..."
                  className="flex-1 bg-transparent text-xs text-slate-805 dark:text-slate-200 placeholder-slate-400 outline-none px-2 font-medium"
                />
                <button
                  onClick={() => {
                    if (mentorInput.trim()) {
                      handleSendMentorMessage(mentorInput);
                    }
                  }}
                  disabled={!mentorInput.trim() || loadingMentor}
                  className="w-7 h-7 rounded-lg bg-blue-600 hover:bg-blue-700 text-white disabled:bg-slate-250 disabled:text-slate-400 dark:disabled:bg-slate-800 dark:disabled:text-slate-650 flex items-center justify-center cursor-pointer disabled:cursor-not-allowed shadow-sm transition-all"
                >
                  <ArrowRight size={12} />
                </button>
              </div>
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

function getLessonTranscriptText(lesson: any): string {
  if (!lesson) return "";
  const title = lesson.title?.toLowerCase() || "";
  
  if (title.includes("docker") || title.includes("container")) {
    return "Instructor: Welcome back! Today we are exploring Docker containerization. We will understand how containers achieve isolation, build a container image, and run it. Best practices include using lightweight base images and keeping containers stateless. Common mistakes include running containers as root or embedding secrets directly in the image.";
  }
  if (title.includes("html") || title.includes("structure")) {
    return "Instructor: In this session, we will write our skeleton HTML5 structure. We will focus on semantic tags like header, main, and footer. Best practices include setting viewports for responsiveness. Common mistakes include using layout tables and abusing nested unlabelled div structures.";
  }
  if (title.includes("introduction") || title.includes("getting started")) {
    return "Instructor: Welcome! In this introductory lesson, we will focus on understanding the course roadmap, local environment setups, and basic editor structures. We will verify our environment variables and configurations to prepare for hands-on assignments.";
  }
  
  return `Instructor: In this session, we will cover the core concepts of ${lesson.title || "this course"}. We will analyze design patterns, step through code implementations, evaluate common mistakes, and explore real-world use cases.`;
}

function parseAndRenderSummary(text: string): React.ReactNode {
  if (!text) return null;
  
  const sections = text.split(/(?=###)/);
  const elements: React.ReactNode[] = [];
  
  sections.forEach((sec, idx) => {
    const trimmed = sec.trim();
    if (!trimmed) return;
    
    if (trimmed.startsWith("###")) {
      const firstNewLine = trimmed.indexOf("\n");
      const heading = trimmed.slice(3, firstNewLine === -1 ? undefined : firstNewLine).trim();
      const content = firstNewLine === -1 ? "" : trimmed.slice(firstNewLine).trim();
      
      const lines = content.split("\n").map(l => l.trim()).filter(Boolean);
      elements.push(
        <div key={idx} className="space-y-1.5">
          <h5 className="font-bold text-slate-900 dark:text-white text-xs uppercase tracking-wider text-blue-600 dark:text-blue-400 mt-2">{heading}</h5>
          <ul className="list-disc pl-4 space-y-1 text-slate-600 dark:text-slate-400 font-medium">
            {lines.map((line, lIdx) => (
              <li key={lIdx}>
                {line.replace(/^[-\*•]\s*/, "")}
              </li>
            ))}
          </ul>
        </div>
      );
    } else {
      elements.push(
        <p key={idx} className="text-xs font-semibold text-slate-600 dark:text-slate-400 leading-relaxed bg-slate-50 dark:bg-slate-950 p-3 rounded-lg border border-slate-100 dark:border-slate-800/80">
          {trimmed}
        </p>
      );
    }
  });
  
  return <div className="space-y-4">{elements}</div>;
}
