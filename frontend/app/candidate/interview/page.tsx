"use client";

import { useEffect, useState } from "react";
import { apiService } from "@/services/api";
import { Mic, MicOff, MessageSquare, Play, Sparkles, CheckCircle, ArrowRight, User, Cpu } from "lucide-react";

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

  const fetchApps = async () => {
    try {
      const data = await apiService.getApplications();
      const intApps = data.filter((a: any) => a.status.toLowerCase() === "interview" || a.status.toLowerCase() === "ranking" || a.status.toLowerCase() === "recommendation" || a.status.toLowerCase() === "offer" || a.status.toLowerCase() === "onboarding");
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
        // Initialize questions
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
      // Admin route fetch, but let's query safely if candidate needs report summary
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
  };

  const submitAnswer = async () => {
    if (!answer.trim() || !interview) return;
    setSubmitting(true);
    const candidateAns = answer;
    setAnswer("");
    
    // Append candidate text
    setDialogue((prev) => [...prev, { role: "Candidate", text: candidateAns }]);

    try {
      const data = await apiService.answerInterviewQuestion(interview.id, candidateAns);
      if (data.next_question === "TARA_FINISHED") {
        setInterviewFinished(true);
        setInterviewStarted(false);
        setWaveActive(false);
        stopStream();
        await loadAnalysis(interview.id);
      } else {
        setCurrQuestion(data.next_question);
        setDialogue((prev) => [...prev, { role: "TARA AI", text: data.next_question }]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 max-w-5xl mx-auto text-gray-500">
        Loading interview chamber...
      </div>
    );
  }

  if (apps.length === 0) {

    return (
      <div className="p-8 md:p-12 max-w-2xl mx-auto text-center flex flex-col justify-center items-center gap-6 min-h-[60vh] glass-panel border border-gray-800 rounded-3xl bg-[#0c0d14]/40 mt-10 shadow-xl font-sans">
        <div className="flex items-center gap-3 bg-purple-950/30 border border-purple-500/10 px-4 py-2.5 rounded-full text-purple-400 text-xs font-bold w-fit animate-pulse">
          <Cpu size={14} />
          <span>Tara AI Recruiter</span>
        </div>
        
        <div className="relative p-6 rounded-2xl border border-purple-500/10 bg-purple-950/5 text-purple-300 italic max-w-md text-xs leading-relaxed">
          "Hello! I do not have any scheduled virtual interview sessions registered for you at this stage. Complete your assigned proctored assessments first, and once they are evaluated, I will connect with you here for your live video interview."
        </div>
        
        <div className="border border-gray-850 p-4 rounded-xl bg-gray-900/10 text-left w-full max-w-sm border-gray-800/60">
          <div className="flex justify-between text-xs mb-2 text-gray-500">
            <span>Interview Stage:</span>
            <span className="text-gray-400 font-semibold uppercase">Pending Assessment</span>
          </div>
          <div className="flex justify-between text-xs text-gray-500 font-sans">
            <span>Tara AI Status:</span>
            <span className="text-purple-400 font-medium">Awaiting Test Results</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 md:p-12 max-w-7xl mx-auto flex flex-col gap-8">
      <div>
        <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2">
          <span>Tara AI Interview</span>
          <Sparkles size={20} className="text-purple-400 animate-pulse" />
        </h1>
        <p className="text-sm text-gray-400 mt-1">
          Autonomous conversational assessment engine hosted by Tara AI.
        </p>
      </div>

      {!interviewStarted && !interviewFinished && (
        <div className="glass-panel p-8 rounded-2xl border border-gray-800 text-center flex flex-col items-center justify-center gap-6 min-h-[40vh] bg-[#0c0d14]/40">
          <div className="w-16 h-16 rounded-full bg-purple-900/20 flex items-center justify-center border border-purple-500/20 glow-primary">
            <Cpu size={28} className="text-purple-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Ready to connect with Tara AI</h2>
            <p className="text-xs text-gray-500 max-w-md mt-2 leading-relaxed">
              Tara AI will ask questions regarding your professional skills, projects, and custom assessment decisions. 
              The interview is fully adaptive based on your statements.
            </p>
          </div>
          <button
            onClick={startInterview}
            className="bg-purple-600 hover:bg-purple-500 px-6 py-3 rounded-xl text-xs font-bold text-white transition-all shadow-md flex items-center gap-2"
          >
            <Play size={12} fill="white" />
            <span>Connect Webcam & Microphone</span>
          </button>
        </div>
      )}

      {/* Active Conversation Layout */}
      {interviewStarted && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Column A: Feeds */}
          <div className="flex flex-col gap-6">
            
            {/* Webcam feed */}
            <div className="glass-panel rounded-2xl border border-gray-800 overflow-hidden bg-[#0d0e15] relative aspect-video flex items-center justify-center">
              <div className="absolute top-4 left-4 z-20 flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping" />
                <span className="text-[10px] font-bold text-red-500 tracking-wider">LIVE FEED</span>
              </div>

              {!isSimulated && stream ? (
                <video
                  ref={(el) => {
                    if (el) el.srcObject = stream;
                  }}
                  autoPlay
                  playsInline
                  muted={isMuted}
                  className="w-full h-full object-cover transform -scale-x-100"
                />
              ) : (
                <div className="flex flex-col items-center justify-center text-center p-6">
                  <User className="text-gray-800/80 scale-[3.5] pointer-events-none mb-4" />
                  {isSimulated && (
                    <div className="mt-4 bg-amber-950/20 border border-amber-900/30 text-amber-400 text-[8px] font-bold px-2 py-1 rounded-md uppercase tracking-wider font-sans">
                      Simulated Webcam Active
                    </div>
                  )}
                </div>
              )}

              {/* Sound wave visual */}
              {waveActive && !isMuted && (
                <div className="absolute bottom-4 left-4 flex items-center gap-1 bg-black/40 px-2 py-1 rounded-lg border border-white/5 h-6">
                  {[...Array(6)].map((_, i) => (
                    <span
                      key={i}
                      className="w-0.5 bg-purple-400 rounded-full animate-bounce"
                      style={{
                        height: `${Math.random() * 100}%`,
                        animationDelay: `${i * 0.1}s`,
                        animationDuration: "0.5s"
                      }}
                    />
                  ))}
                </div>
              )}

              <div className="absolute bottom-4 right-4 z-20 flex gap-2">
                <button
                  onClick={() => setIsMuted(!isMuted)}
                  className={`p-2 rounded-xl border ${
                    isMuted ? "bg-red-950/40 border-red-800/40 text-red-400" : "bg-[#12131e]/60 border-gray-800 text-gray-400"
                  } hover:scale-105 transition-transform`}
                >
                  {isMuted ? <MicOff size={14} /> : <Mic size={14} />}
                </button>
              </div>
            </div>

            {/* Tara AI Portrait screen */}
            <div className="glass-panel p-6 rounded-2xl border border-gray-800 bg-[#0d0e15]/40 flex flex-col gap-3">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-tara flex items-center justify-center font-bold text-white">T</div>
                <div>
                  <h4 className="text-xs font-bold text-white">Tara AI</h4>
                  <span className="text-[9px] text-purple-400 font-semibold tracking-wide">Recruiter Agent</span>
                </div>
              </div>
              <p className="text-xs text-purple-300 italic leading-relaxed mt-2 p-3 rounded-xl border border-purple-500/10 bg-purple-950/5">
                "{currQuestion}"
              </p>
            </div>

          </div>

          {/* Column B: Transcript & Answer Console */}
          <div className="lg:col-span-2 flex flex-col gap-6 h-[55vh]">
            
            {/* Dialogue list */}
            <div className="glass-panel p-6 rounded-2xl border border-gray-800 flex-1 overflow-y-auto flex flex-col gap-4">
              <h3 className="text-xs font-bold text-white flex items-center gap-2 border-b border-gray-800 pb-3">
                <MessageSquare size={14} className="text-purple-400" />
                <span>Interview Live Transcript</span>
              </h3>

              <div className="flex flex-col gap-4 flex-1">
                {dialogue.map((bubble, i) => (
                  <div
                    key={i}
                    className={`flex flex-col max-w-[80%] ${
                      bubble.role === "Candidate" ? "self-end items-end" : "self-start items-start"
                    }`}
                  >
                    <span className="text-[9px] text-gray-500 font-semibold mb-1">{bubble.role}</span>
                    <div
                      className={`p-3 rounded-2xl text-xs leading-relaxed ${
                        bubble.role === "Candidate"
                          ? "bg-purple-600 text-white rounded-tr-none"
                          : "bg-gray-800/40 text-gray-300 rounded-tl-none border border-gray-800/60"
                      }`}
                    >
                      {bubble.text}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Input console */}
            <div className="glass-panel p-4 rounded-2xl border border-gray-800 flex gap-3 items-center">
              <input
                type="text"
                disabled={submitting}
                placeholder="Type your spoken answer response..."
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submitAnswer()}
                className="flex-1 bg-[#12131e] border border-gray-800 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-purple-500 transition-colors"
              />
              <button
                onClick={submitAnswer}
                disabled={submitting || !answer.trim()}
                className="bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white px-4 py-3 rounded-xl text-xs font-bold transition-all shadow-md shrink-0 flex items-center gap-1.5"
              >
                <span>Send</span>
                <ArrowRight size={12} />
              </button>
            </div>

          </div>

        </div>
      )}

      {/* Completed & Analysis Screen */}
      {interviewFinished && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Success summary */}
          <div className="lg:col-span-2 glass-panel p-8 rounded-2xl border border-gray-800 flex flex-col justify-between min-h-[45vh] bg-[#0c0d14]/40">
            <div className="flex flex-col gap-4">
              <div className="w-14 h-14 bg-emerald-950/40 border border-emerald-800/30 flex items-center justify-center rounded-2xl text-emerald-400">
                <CheckCircle size={28} />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Interview Process Completed</h2>
                <p className="text-xs text-gray-500 mt-2 leading-relaxed">
                  Excellent job. Tara AI has evaluated your conversation transcript and structural reasoning patterns. 
                  The scoring report is detailed below.
                </p>
              </div>

              {!analysis ? (
                <div className="border border-gray-800/60 p-5 rounded-2xl bg-[#0d0e15]/40 mt-4 text-center">
                  <span className="text-xs text-gray-500 font-semibold block">Not enough data available</span>
                  <span className="text-[10px] text-gray-600 block mt-1">Evaluation report is pending calculations.</span>
                </div>
              ) : (
                <div className="border border-gray-800/60 p-5 rounded-2xl bg-[#0d0e15]/40 mt-4">
                  <h3 className="text-xs font-bold text-white mb-2">Tara's Evaluation Notes</h3>
                  <p className="text-xs text-gray-400 leading-relaxed italic">
                    "{analysis.report_summary}"
                  </p>
                </div>
              )}
            </div>

            <div className="mt-8 border-t border-gray-800/60 pt-6">
              <p className="text-[10px] text-gray-500">
                Next Stage: The Candidate Ranking Agent is currently computing your composite score percentile relative to alternative applicants.
              </p>
            </div>
          </div>

          {/* Scores breakdown cards */}
          <div className="glass-panel p-6 rounded-2xl border border-gray-800 bg-[#0d0e15]/40 flex flex-col gap-6">
            <h3 className="text-xs font-bold text-white border-b border-gray-800 pb-3 flex items-center gap-2">
              <Cpu size={14} className="text-purple-400" />
              <span>Metrics scorecard</span>
            </h3>

            {!analysis ? (
              <div className="text-center py-12 text-gray-500 text-xs font-semibold">
                Not enough data available
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-gray-400">Technical competency:</span>
                  <span className="font-bold text-purple-400">{analysis.technical_score}%</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-gray-400">Communication quality:</span>
                  <span className="font-bold text-indigo-400">{analysis.communication_score}%</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-gray-400">Confidence delivery:</span>
                  <span className="font-bold text-indigo-400">{analysis.confidence_score}%</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-gray-400">Structured logic:</span>
                  <span className="font-bold text-purple-400">{analysis.thinking_score}%</span>
                </div>

                <div className="border-t border-gray-800/80 pt-4 mt-2 flex justify-between items-center text-xs font-bold text-white">
                  <span>Aggregate average:</span>
                  <span className="text-sm text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-400">
                    {analysis.final_score}%
                  </span>
                </div>
              </div>
            )}
          </div>

        </div>
      )}

    </div>
  );
}
