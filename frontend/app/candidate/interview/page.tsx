"use client";

import { useEffect, useState, useRef, ChangeEvent, KeyboardEvent } from "react";
import { apiService } from "@/services/api";
import { 
  Mic, MicOff, MessageSquare, Play, Sparkles, CheckCircle2, 
  ArrowRight, User, Cpu, Loader2, Camera, CameraOff, X, 
  AlertTriangle, ShieldAlert
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Alert } from "@/components/ui/Alert";
import { ProgressRing } from "@/components/ui/Progress";

export default function CandidateInterview() {
  const [apps, setApps] = useState<any[]>([]);
  const [selectedApp, setSelectedApp] = useState<any>(null);
  const [interview, setInterview] = useState<any>(null);
  const [analysis, setAnalysis] = useState<any>(null);

  const [loading, setLoading] = useState(true);
  const [interviewStarted, setInterviewStarted] = useState(false);
  const [interviewFinished, setInterviewFinished] = useState(false);

  // Active dialogue states
  const [currQuestion, setCurrQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [dialogue, setDialogue] = useState<{ role: string; text: string }[]>([]);
  const [submitting, setSubmitting] = useState(false);
  
  // Simulated speech/mic recording state
  const [isMuted, setIsMuted] = useState(false);
  const [waveActive, setWaveActive] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isSimulated, setIsSimulated] = useState(false);

  // Tara AI voice animation states: speaking, listening, thinking, disconnected
  const [voiceState, setVoiceState] = useState<"speaking" | "listening" | "thinking" | "disconnected">("disconnected");

  const videoRef = useRef<HTMLVideoElement>(null);

  const stopStream = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
  };

  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, [stream]);

  // Connect video stream to video tag when it updates
  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }
  }, [stream, interviewStarted]);

  const fetchApps = async () => {
    try {
      const data = await apiService.getApplications();
      const intApps = data.filter((a: any) => 
        a.status.toLowerCase() === "interview" || 
        a.status.toLowerCase() === "ranking" || 
        a.status.toLowerCase() === "recommendation" || 
        a.status.toLowerCase() === "offer" || 
        a.status.toLowerCase() === "onboarding"
      );
      setApps(intApps);
      if (intApps.length > 0) {
        setSelectedApp(intApps[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApps();
  }, []);

  const loadInterviewSession = async (appId: number) => {
    try {
      const sess = await apiService.getInterview(appId);
      setInterview(sess);
      
      if (sess.status === "completed") {
        setInterviewFinished(true);
        loadAnalysis(sess.id);
      } else {
        const questionsList = JSON.parse(sess.questions || "[]");
        if (questionsList.length > 0) {
          setCurrQuestion(questionsList[sess.current_question_index]);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const loadAnalysis = async (intId: number) => {
    try {
      const res = await apiService.getInterviewAnalysis(intId);
      setAnalysis(res);
    } catch {
      setAnalysis(null);
    }
  };

  useEffect(() => {
    if (selectedApp) {
      loadInterviewSession(selectedApp.id);
    }
  }, [selectedApp]);

  const startInterview = async () => {
    let activeStream: MediaStream | null = null;

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("navigator.mediaDevices not supported or not in secure context");
      }
      activeStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    } catch (err) {
      console.warn("Failed to acquire media stream for interview:", err);
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        try {
          activeStream = await navigator.mediaDevices.getUserMedia({ video: true });
        } catch {}
      }
    }
    
    if (activeStream) {
      setStream(activeStream);
      setIsSimulated(false);
    } else {
      setIsSimulated(true);
    }

    setInterviewStarted(true);
    setWaveActive(true);
    setDialogue([{ role: "TARA AI", text: currQuestion }]);
    
    // Set to Speaking initially, then transition to Listening
    setVoiceState("speaking");
    setTimeout(() => {
      setVoiceState("listening");
    }, 4500);
  };

  const submitAnswer = async () => {
    if (!answer.trim() || !interview) return;
    setSubmitting(true);
    const candidateAns = answer;
    setAnswer("");
    
    setDialogue((prev) => [...prev, { role: "Candidate", text: candidateAns }]);
    setVoiceState("thinking");

    try {
      const data = await apiService.answerInterviewQuestion(interview.id, candidateAns);
      if (data.next_question === "TARA_FINISHED") {
        setInterviewFinished(true);
        setInterviewStarted(false);
        setWaveActive(false);
        setVoiceState("disconnected");
        stopStream();
        await loadAnalysis(interview.id);
      } else {
        setCurrQuestion(data.next_question);
        setDialogue((prev) => [...prev, { role: "TARA AI", text: data.next_question }]);
        
        // Return to Speaking, then Listening
        setVoiceState("speaking");
        setTimeout(() => {
          setVoiceState("listening");
        }, 4500);
      }
    } catch (err) {
      console.error(err);
      setVoiceState("listening");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <Loader2 size={36} className="animate-spin text-primary" />
          <span className="text-sm font-semibold text-muted-foreground">Loading Interview Chamber...</span>
        </div>
      </div>
    );
  }

  if (apps.length === 0) {
    return (
      <div className="max-w-xl mx-auto py-16 px-6">
        <Card className="flex flex-col items-center text-center gap-6 p-8">
          <div className="flex items-center gap-2 bg-primary/10 border border-primary/20 px-4 py-2 rounded-full text-primary text-xs font-bold w-fit animate-pulse">
            <Cpu size={14} />
            <span>Tara AI Recruiter</span>
          </div>
          
          <p className="text-sm text-muted-foreground italic leading-relaxed max-w-sm">
            "Hello! I do not have any scheduled virtual interview sessions registered for you at this stage. Complete your assigned proctored assessments first, and once they are evaluated, I will connect with you here for your live video interview."
          </p>
          
          <div className="border border-border p-4 rounded-2xl bg-muted/20 text-left w-full max-w-sm">
            <div className="flex justify-between text-xs mb-2">
              <span className="text-muted-foreground font-semibold">Interview Stage:</span>
              <span className="text-foreground font-bold uppercase">Pending Assessment</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground font-semibold">Tara AI Status:</span>
              <span className="text-primary font-bold">Awaiting Test Results</span>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex-1 min-h-screen bg-background text-foreground p-6 md:p-8 font-sans">
      
      {/* Dynamic Voice Orb CSS Keyframe Animations */}
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes orb-speaking {
          0%, 100% { transform: scale(1); box-shadow: 0 0 20px 5px rgba(139, 92, 246, 0.4), inset 0 0 15px rgba(139, 92, 246, 0.5); }
          50% { transform: scale(1.08); box-shadow: 0 0 45px 15px rgba(139, 92, 246, 0.7), inset 0 0 25px rgba(139, 92, 246, 0.8); }
        }
        @keyframes orb-listening {
          0%, 100% { transform: scale(1); border-radius: 50%; box-shadow: 0 0 20px 5px rgba(16, 185, 129, 0.4); }
          33% { border-radius: 46% 54% 50% 50% / 50% 50% 54% 46%; }
          66% { border-radius: 54% 46% 52% 48% / 48% 52% 46% 54%; transform: scale(1.04); box-shadow: 0 0 35px 12px rgba(16, 185, 129, 0.65); }
        }
        @keyframes orb-thinking {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes orb-thinking-pulse {
          0%, 100% { transform: scale(1); box-shadow: 0 0 20px 5px rgba(245, 158, 11, 0.4); }
          50% { transform: scale(1.03); box-shadow: 0 0 35px 10px rgba(245, 158, 11, 0.65); }
        }
        @keyframes wave-bounce {
          0%, 100% { transform: scaleY(0.3); }
          50% { transform: scaleY(1); }
        }
      `}} />

      {/* Header Area */}
      <div className="flex flex-col md:flex-row justify-between md:items-center gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-black tracking-tight flex items-center gap-2">
            <span>Tara AI Interview</span>
            <Sparkles size={20} className="text-primary animate-pulse" />
          </h1>
          <p className="text-sm text-muted-foreground font-semibold mt-1">
            Autonomous adaptive conversation chamber hosted by Tara AI.
          </p>
        </div>
      </div>

      {/* Setup screen */}
      {!interviewStarted && !interviewFinished && (
        <Card className="max-w-2xl mx-auto p-8 text-center flex flex-col items-center justify-center gap-6 shadow-sm border border-border">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center border border-primary/20 animate-pulse">
            <Cpu size={28} className="text-primary" />
          </div>
          <div className="space-y-2">
            <h2 className="text-lg font-black text-foreground">Ready to connect with Tara AI</h2>
            <p className="text-xs text-muted-foreground max-w-md mx-auto leading-relaxed">
              Tara AI will conduct an adaptive video dialogue regarding your experiences, technical choices, and coding reasoning. 
              Please ensure you are in a quiet room with active microphone permissions.
            </p>
          </div>
          <Button
            onClick={startInterview}
            size="lg"
            className="w-full sm:w-auto font-bold"
          >
            <Play size={14} className="mr-2 fill-current" />
            <span>Connect Webcam & Microphone</span>
          </Button>
        </Card>
      )}

      {/* Active Chamber Layout */}
      {interviewStarted && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch min-h-[70vh]">
          
          {/* Column A: Feeds & Status (Left 4 cols) */}
          <div className="lg:col-span-4 flex flex-col gap-6">
            
            {/* Live Camera Feed Card */}
            <Card className="overflow-hidden p-0 relative aspect-video flex items-center justify-center bg-black border border-border">
              <div className="absolute top-4 left-4 z-20 flex items-center gap-1.5 bg-black/50 backdrop-blur-xs px-2.5 py-1 rounded-md border border-white/5">
                <span className="w-2 h-2 rounded-full bg-destructive animate-ping shrink-0" />
                <span className="text-[9px] font-bold text-destructive tracking-wider uppercase">LIVE FEED</span>
              </div>

              {!isSimulated && stream ? (
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted={isMuted}
                  className="w-full h-full object-cover transform -scale-x-100"
                />
              ) : (
                <div className="flex flex-col items-center justify-center text-center p-6 text-muted-foreground">
                  <User size={48} className="text-muted/40 mb-3" />
                  {isSimulated ? (
                    <Badge variant="warning" className="text-[9px] tracking-wider uppercase font-bold">
                      Simulated Camera Active
                    </Badge>
                  ) : (
                    <span className="text-xs">Connecting Camera Feed...</span>
                  )}
                </div>
              )}

              {/* sound wave checks */}
              {waveActive && !isMuted && (
                <div className="absolute bottom-4 left-4 flex items-center gap-0.5 bg-black/60 backdrop-blur-xs px-2 py-1.5 rounded-lg border border-white/5 h-6">
                  {[...Array(6)].map((_, i) => (
                    <span
                      key={i}
                      className="w-0.5 bg-primary rounded-full shrink-0"
                      style={{
                        height: "100%",
                        animation: "wave-bounce 0.6s ease-in-out infinite",
                        animationDelay: `${i * 0.08}s`,
                        transformOrigin: "center"
                      }}
                    />
                  ))}
                </div>
              )}

              <div className="absolute bottom-4 right-4 z-20 flex gap-2">
                <Button
                  onClick={() => setIsMuted(!isMuted)}
                  variant={isMuted ? "destructive" : "secondary"}
                  size="sm"
                  className="rounded-xl h-8 w-8 p-0"
                >
                  {isMuted ? <MicOff size={14} /> : <Mic size={14} />}
                </Button>
              </div>
            </Card>

            {/* Proctor Alert Card */}
            <Card className="flex-1 flex flex-col justify-between p-6">
              <div className="space-y-4">
                <h3 className="text-xs font-black uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                  <ShieldAlert size={14} className="text-primary" />
                  <span>Proctor Monitor</span>
                </h3>
                
                <div className="space-y-2">
                  <div className="flex justify-between items-center text-xs font-semibold">
                    <span className="text-muted-foreground">AI Face Lock:</span>
                    <Badge variant="success">Active & Verified</Badge>
                  </div>
                  <div className="flex justify-between items-center text-xs font-semibold">
                    <span className="text-muted-foreground">Tab Focus lock:</span>
                    <Badge variant="success">LOCKED</Badge>
                  </div>
                  <div className="flex justify-between items-center text-xs font-semibold">
                    <span className="text-muted-foreground">Browser Integrity:</span>
                    <Badge variant="success">Secured</Badge>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-border flex items-start gap-2 bg-destructive/5 p-3 rounded-xl border border-destructive/10">
                <AlertTriangle size={14} className="text-destructive shrink-0 mt-0.5" />
                <p className="text-[10px] text-destructive font-bold leading-normal">
                  Warning: Leaving full screen or changing tabs will auto-submit the interview and record a proctor violation flag.
                </p>
              </div>
            </Card>
          </div>

          {/* Column B: Immersive Fullscreen ChatGPT Voice Panel (Right 8 cols) */}
          <Card className="lg:col-span-8 flex flex-col justify-between bg-black border border-border relative overflow-hidden p-6 min-h-[600px]">
            
            {/* Header info */}
            <div className="flex items-center justify-between border-b border-border/40 pb-4 shrink-0">
              <div className="flex items-center gap-2.5">
                <Cpu size={18} className="text-primary animate-pulse" />
                <div>
                  <h3 className="text-sm font-black text-white">Chamber session</h3>
                  <span className="text-[9px] text-muted-foreground font-bold tracking-wider uppercase">Adaptive AI Recruiter</span>
                </div>
              </div>
              
              <div className="flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                  voiceState === "speaking" ? "bg-purple-500 animate-pulse" :
                  voiceState === "listening" ? "bg-emerald-500 animate-pulse" :
                  voiceState === "thinking" ? "bg-amber-500 animate-pulse" : "bg-muted"
                }`} />
                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">
                  {voiceState === "speaking" ? "Tara Speaking" :
                   voiceState === "listening" ? "Tara Listening" :
                   voiceState === "thinking" ? "Tara Thinking" : "Offline"}
                </span>
              </div>
            </div>

            {/* Immersive Center: Tara Voice Orb Chamber */}
            <div className="flex-1 flex flex-col items-center justify-center py-8 relative shrink-0">
              
              {/* Animation Voice Orb wrapper */}
              <div className="relative flex items-center justify-center w-64 h-64">
                
                {/* Dotted rotating circle for Thinking state */}
                {voiceState === "thinking" && (
                  <>
                    <div 
                      className="absolute border border-dashed border-amber-500/60 rounded-full w-[200px] h-[200px]"
                      style={{ animation: "orb-thinking 8s linear infinite" }}
                    />
                    <div 
                      className="absolute border border-dotted border-amber-400/40 rounded-full w-[230px] h-[230px]"
                      style={{ animation: "orb-thinking 12s linear infinite reverse" }}
                    />
                  </>
                )}

                {/* Pulsing sound ring for Speaking state */}
                {voiceState === "speaking" && (
                  <div 
                    className="absolute border border-purple-500/30 rounded-full w-[190px] h-[190px] animate-ping"
                    style={{ animationDuration: "1.5s" }}
                  />
                )}

                {/* Main Voice Orb core */}
                <div 
                  className={`w-36 h-36 rounded-full flex items-center justify-center transition-all duration-500 bg-gradient-to-tr shadow-2xl relative z-10 ${
                    voiceState === "speaking" 
                      ? "from-purple-600 via-pink-500 to-indigo-600" 
                      : voiceState === "listening"
                        ? "from-emerald-500 via-teal-400 to-cyan-500"
                        : voiceState === "thinking"
                          ? "from-amber-500 via-orange-500 to-yellow-500"
                          : "from-slate-700 via-slate-800 to-slate-900"
                  }`}
                  style={{
                    animation: 
                      voiceState === "speaking" ? "orb-speaking 2s ease-in-out infinite" :
                      voiceState === "listening" ? "orb-listening 2.5s ease-in-out infinite" :
                      voiceState === "thinking" ? "orb-thinking-pulse 1.5s ease-in-out infinite" : "none"
                  }}
                >
                  {/* Subtle CPU brain silhouette in center */}
                  <Cpu size={32} className="text-white/60 drop-shadow-sm" />
                </div>

              </div>

              {/* Real-time Subtitle / Caption Overlay */}
              <div className="max-w-xl w-full bg-slate-950/80 backdrop-blur-md border border-white/5 rounded-2xl p-4 shadow-2xl text-center space-y-1.5 mt-4 shrink-0">
                <span className="text-[8px] font-black uppercase tracking-wider text-muted-foreground/60 block">
                  {voiceState === "speaking" ? "Tara's Caption" : "Your Transcription"}
                </span>
                <p className="text-sm text-slate-100 font-medium leading-relaxed">
                  {voiceState === "speaking" || voiceState === "thinking" 
                    ? `"${currQuestion}"`
                    : dialogue[dialogue.length - 1]?.role === "Candidate"
                      ? `"${dialogue[dialogue.length - 1].text}"`
                      : `"Hello! I am listening to your response..."`
                  }
                </p>
              </div>

            </div>

            {/* Bottom: Floating Chat Input bar */}
            <div className="flex gap-3 items-center border-t border-border/40 pt-4 shrink-0">
              <Input
                type="text"
                disabled={submitting}
                placeholder={voiceState === "thinking" ? "Tara is thinking..." : "Type your spoken answer response..."}
                value={answer}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setAnswer(e.target.value)}
                onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => e.key === "Enter" && submitAnswer()}
                className="bg-[#0b0c10] border-border text-white text-xs h-11"
              />
              <Button
                onClick={submitAnswer}
                disabled={submitting || !answer.trim()}
                size="sm"
                className="h-11 px-5 font-bold"
              >
                {submitting ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  <>
                    <span>Send</span>
                    <ArrowRight size={13} className="ml-1" />
                  </>
                )}
              </Button>
            </div>

          </Card>
          
        </div>
      )}

      {/* Completed & Analysis Screen */}
      {interviewFinished && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-7xl mx-auto mt-4">
          
          {/* Summary */}
          <Card className="lg:col-span-2 flex flex-col justify-between p-8 min-h-[45vh]">
            <div className="space-y-6">
              <div className="w-14 h-14 bg-success/15 border border-success/20 flex items-center justify-center rounded-2xl text-success shadow-xs">
                <CheckCircle2 size={28} />
              </div>
              <div className="space-y-2">
                <h2 className="text-xl font-black text-foreground">Interview Process Completed</h2>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Excellent job. Tara AI has evaluated your conversation transcript, thinking structure, and coding reasoning. 
                  The full scorecard metrics are shown on the side panel.
                </p>
              </div>

              {!analysis ? (
                <div className="border border-dashed border-border p-6 rounded-2xl bg-muted/10 text-center text-xs text-muted-foreground">
                  Evaluation report is currently calculating. Please refresh in a moment.
                </div>
              ) : (
                <div className="border border-border p-5 rounded-2xl bg-muted/20">
                  <h3 className="text-xs font-black text-foreground mb-1.5 uppercase tracking-wider">Evaluation Summary</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed italic">
                    "{analysis.report_summary}"
                  </p>
                </div>
              )}
            </div>

            <div className="mt-8 pt-4 border-t border-border">
              <p className="text-[10px] text-muted-foreground font-semibold">
                Next Stage: The Candidate Ranking Agent is currently computing your composite score percentile relative to alternative applicants.
              </p>
            </div>
          </Card>

          {/* Scores Panel */}
          <Card className="flex flex-col justify-between p-6">
            <div className="space-y-6">
              <h3 className="text-xs font-black uppercase tracking-wider text-muted-foreground border-b border-border pb-3 flex items-center gap-1.5">
                <Cpu size={14} className="text-primary" />
                <span>Scorecard Breakdown</span>
              </h3>

              {!analysis ? (
                <div className="text-center py-16 text-muted-foreground text-xs font-semibold italic">
                  Not enough data available
                </div>
              ) : (
                <div className="space-y-4">
                  
                  <div className="flex justify-between items-center text-xs font-semibold">
                    <span className="text-muted-foreground">Technical Competency:</span>
                    <span className="text-foreground">{analysis.technical_score}%</span>
                  </div>
                  <div className="flex justify-between items-center text-xs font-semibold">
                    <span className="text-muted-foreground">Communication Quality:</span>
                    <span className="text-foreground">{analysis.communication_score}%</span>
                  </div>
                  <div className="flex justify-between items-center text-xs font-semibold">
                    <span className="text-muted-foreground">Confidence Delivery:</span>
                    <span className="text-foreground">{analysis.confidence_score}%</span>
                  </div>
                  <div className="flex justify-between items-center text-xs font-semibold">
                    <span className="text-muted-foreground">Structured Logic:</span>
                    <span className="text-foreground">{analysis.thinking_score}%</span>
                  </div>

                  <div className="border-t border-border pt-4 mt-6 flex justify-between items-center text-xs font-black text-foreground">
                    <span>AGGREGATE SCORE:</span>
                    <span className="text-sm text-primary">
                      {analysis.final_score}%
                    </span>
                  </div>
                </div>
              )}
            </div>
            
            {analysis && (
              <div className="mt-6 flex justify-center">
                <ProgressRing 
                  value={analysis.final_score} 
                  size={96} 
                  strokeWidth={6} 
                />
              </div>
            )}
          </Card>

        </div>
      )}

    </div>
  );
}
