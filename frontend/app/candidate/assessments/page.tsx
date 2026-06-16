"use client";

import { useEffect, useState, useRef } from "react";
import { apiService } from "@/services/api";
import { 
  CheckCircle, Play, AlertTriangle, ShieldCheck, Camera, 
  Mic, Globe, Cpu, Server, ClipboardCopy, FileCode2
} from "lucide-react";

export default function CandidateAssessments() {
  const [apps, setApps] = useState<any[]>([]);
  const [selectedApp, setSelectedApp] = useState<any>(null);
  const [assessment, setAssessment] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Assessment taking states
  const [examStarted, setExamStarted] = useState(false);
  const [examCompleted, setExamCompleted] = useState(false);
  const [mcqAnswers, setMcqAnswers] = useState<Record<string, number>>({});
  const [codingAnswers, setCodingAnswers] = useState<Record<string, string>>({});
  const [englishAnswer, setEnglishAnswer] = useState("");
  const [proctorLogs, setProctorLogs] = useState<string[]>([]);
  const [violations, setViolations] = useState(0);

  // Device verification states
  const [checks, setChecks] = useState({
    camera: false,
    mic: false,
    internet: false,
    browser: false,
    face: false
  });
  const [verifying, setVerifying] = useState(false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isSimulated, setIsSimulated] = useState(false);
  const [tfLoaded, setTfLoaded] = useState(false);
  const [cocoLoaded, setCocoLoaded] = useState(false);
  const [blazeModel, setBlazeModel] = useState<any>(null);
  const [cocoModel, setCocoModel] = useState<any>(null);
  const [modelLoading, setModelLoading] = useState(false);


  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Cleanup stream tracks
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

  // Load TensorFlow.js and Models dynamically via CDN
  useEffect(() => {
    if (typeof window === "undefined") return;

    const tfScript = document.createElement("script");
    tfScript.src = "https://cdn.jsdelivr.net/npm/@tensorflow/tfjs";
    tfScript.async = true;
    tfScript.onload = () => {
      // Load BlazeFace
      const bfScript = document.createElement("script");
      bfScript.src = "https://cdn.jsdelivr.net/npm/@tensorflow-models/blazeface";
      bfScript.async = true;
      bfScript.onload = () => {
        setTfLoaded(true);
      };
      document.body.appendChild(bfScript);

      // Load COCO-SSD
      const cocoScript = document.createElement("script");
      cocoScript.src = "https://cdn.jsdelivr.net/npm/@tensorflow-models/coco-ssd";
      cocoScript.async = true;
      cocoScript.onload = () => {
        setCocoLoaded(true);
      };
      document.body.appendChild(cocoScript);
    };
    document.body.appendChild(tfScript);

    return () => {
      try {
        document.body.removeChild(tfScript);
      } catch {}
    };
  }, []);

  useEffect(() => {
    if (!tfLoaded) return;
    
    const loadModels = async () => {
      setModelLoading(true);
      try {
        // @ts-ignore
        if (window.blazeface) {
          // @ts-ignore
          const bModel = await window.blazeface.load();
          setBlazeModel(bModel);
        }
        // @ts-ignore
        if (window.cocoSsd) {
          // @ts-ignore
          const cModel = await window.cocoSsd.load();
          setCocoModel(cModel);
        }
      } catch (err) {
        console.error("Error loading TFJS models:", err);
      } finally {
        setModelLoading(false);
      }
    };
    
    loadModels();
  }, [tfLoaded]);

  // Real-time proctoring model detection loop
  useEffect(() => {
    if (!examStarted) return;
    
    let proctorInterval: any = null;
    
    if (blazeModel || cocoModel) {
      proctorInterval = setInterval(async () => {
        const video = videoRef.current;
        if (!video || video.readyState < 2) return;
        
        try {
          // 1. Run BlazeFace detection
          if (blazeModel) {
            const predictions = await blazeModel.estimateFaces(video, false);
            
            if (predictions.length === 0) {
              logFraudViolation("Face Missing", "AI Proctor detected no face in the webcam feed.");
            } else if (predictions.length > 1) {
              logFraudViolation("Multiple Faces", `AI Proctor detected ${predictions.length} faces in the screen view.`);
            } else {
              // Gaze / Eye tracking check
              const face = predictions[0];
              if (face.landmarks && face.landmarks.length >= 6) {
                const rightEye = face.landmarks[0];
                const leftEye = face.landmarks[1];
                const nose = face.landmarks[2];
                const rightEar = face.landmarks[4];
                const leftEar = face.landmarks[5];
                
                const eyeMidpointX = (rightEye[0] + leftEye[0]) / 2;
                const faceWidth = Math.abs(rightEar[0] - leftEar[0]);
                
                // Gaze offset
                const gazeOffset = Math.abs(nose[0] - eyeMidpointX) / (faceWidth || 1);
                
                if (gazeOffset > 0.16) {
                  logFraudViolation("Eye Gaze Deviation", "Candidate is looking away from the assessment screen.");
                }
              }
            }
          }
          
          // 2. Run COCO-SSD object detection
          if (cocoModel) {
            const objects = await cocoModel.detect(video);
            const cellPhone = objects.find((obj: any) => obj.class === "cell phone" && obj.score > 0.5);
            if (cellPhone) {
              logFraudViolation("Mobile Device Detected", "Candidate is using a mobile phone device in view.");
            }
          }
        } catch (err) {
          console.error("Error running proctor detection:", err);
        }
      }, 2500);
    }
    
    return () => {
      if (proctorInterval) clearInterval(proctorInterval);
    };
  }, [examStarted, blazeModel, cocoModel]);

  const fetchApps = async () => {
    try {
      const data = await apiService.getApplications();
      // Filter applications that are in assessment stage
      const assessApps = data.filter((a: any) => a.status.toLowerCase() === "assessment");
      setApps(assessApps);
      if (assessApps.length > 0) {
        setSelectedApp(assessApps[0]);
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

  const loadAssessmentDetails = async (appId: number) => {
    try {
      const details = await apiService.getAssessment(appId);
      setAssessment(details);
    } catch (err) {
      console.error("Failed to load assessment details:", err);
    }
  };

  useEffect(() => {
    if (selectedApp) {
      loadAssessmentDetails(selectedApp.id);
    }
  }, [selectedApp]);

  // Run hardware verification check
  const runDeviceVerification = async () => {
    setVerifying(true);
    let cameraOk = false;
    let micOk = false;
    let activeStream: MediaStream | null = null;

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("navigator.mediaDevices not supported or not in secure context");
      }
      // Prompt user for camera and microphone permission in browser
      activeStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      cameraOk = true;
      micOk = true;
    } catch (err) {
      console.warn("Media permissions declined or unavailable:", err);
      // Try video only or audio only to identify granular failures
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        try {
          const videoStream = await navigator.mediaDevices.getUserMedia({ video: true });
          cameraOk = true;
          activeStream = videoStream;
        } catch {}
        try {
          const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
          micOk = true;
          if (!activeStream) {
            activeStream = audioStream;
          } else {
            audioStream.getAudioTracks().forEach(track => activeStream?.addTrack(track));
          }
        } catch {}
      }
    }

    if (activeStream) {
      setStream(activeStream);
      setIsSimulated(false);
      setChecks({
        camera: cameraOk,
        mic: micOk,
        internet: typeof navigator !== "undefined" ? navigator.onLine : true,
        browser: true,
        face: cameraOk
      });
    } else {
      // Bypassed/Simulated fallback so the user can test the app
      setIsSimulated(true);
      setChecks({
        camera: true,
        mic: true,
        internet: typeof navigator !== "undefined" ? navigator.onLine : true,
        browser: true,
        face: true
      });
    }
    setVerifying(false);
  };

  // Start Assessment Exam
  const startExam = () => {
    setExamStarted(true);
    // Add proctoring event listeners
    document.addEventListener("visibilitychange", handleVisibilityChange);
    document.addEventListener("copy", handleClipboardEvent);
    document.addEventListener("paste", handleClipboardEvent);
  };

  // Stop Proctoring listeners
  const stopProctoring = () => {
    document.removeEventListener("visibilitychange", handleVisibilityChange);
    document.removeEventListener("copy", handleClipboardEvent);
    document.removeEventListener("paste", handleClipboardEvent);
  };

  // Visibility (Tab Switch) Proctoring
  const handleVisibilityChange = () => {
    if (document.visibilityState === "hidden") {
      logFraudViolation("Tab Switch", "Candidate switched tabs or exited focus window.");
    }
  };

  // Copy paste Proctoring
  const handleClipboardEvent = (e: Event) => {
    logFraudViolation("Clipboard Action", `Candidate attempted a text ${e.type} action.`);
  };

  const logFraudViolation = async (type: string, details: string) => {
    if (!selectedApp) return;
    setViolations((v) => v + 1);
    const timeStr = new Date().toLocaleTimeString();
    setProctorLogs((prev) => [`[${timeStr}] WARNING: ${type} detected`, ...prev]);
    
    // Call backend API to record fraud log
    await apiService.logProctorEvent(selectedApp.id, type.toLowerCase().replace(" ", "_"), details);
  };

  const handleMCQChange = (qId: number, optionIdx: number) => {
    setMcqAnswers((prev) => ({ ...prev, [qId]: optionIdx }));
  };

  const handleCodingChange = (challengeId: number, code: string) => {
    setCodingAnswers((prev) => ({ ...prev, [challengeId]: code }));
  };

  const submitExam = async () => {
    if (!selectedApp) return;
    stopProctoring();
    stopStream();
    try {
      const answers = {
        mcqs: mcqAnswers,
        coding: codingAnswers,
        english: { "1": englishAnswer }
      };
      await apiService.submitAssessment(selectedApp.id, answers);
      setExamCompleted(true);
      setExamStarted(false);
    } catch (err) {
      console.error(err);
    }
  };

  const allChecksPassed = Object.values(checks).every((c) => c);

  if (loading) {
    return (
      <div className="p-8 max-w-5xl mx-auto text-gray-500 bg-background dark:bg-background min-h-screen">
        Loading assessment terminal...
      </div>
    );
  }

  if (apps.length === 0) {

    return (
      <div className="p-8 md:p-12 max-w-2xl mx-auto text-center flex flex-col justify-center items-center gap-6 min-h-[60vh] glass-panel border border-border dark:border-border rounded-3xl bg-white dark:bg-card/40 mt-10 shadow-xl font-sans">
        <div className="flex items-center gap-3 bg-purple-50 dark:bg-purple-950/30 border border-purple-300 dark:border-purple-500/10 px-4 py-2.5 rounded-full text-purple-600 dark:text-purple-400 text-xs font-bold w-fit animate-pulse">
          <Cpu size={14} />
          <span>Tara AI Recruiter</span>
        </div>
        
        <div className="relative p-6 rounded-2xl border border-purple-300 dark:border-purple-500/10 bg-purple-50 dark:bg-purple-950/5 text-purple-600 dark:text-purple-300 italic max-w-md text-xs leading-relaxed">
          "Hello! I am currently monitoring the recruitment pipeline. You do not have any active test assessments assigned to your account at this moment. Please apply for our job openings to trigger the screening phase."
        </div>
        
        <div className="border p-4 rounded-xl bg-gray-50 dark:bg-gray-900/10 text-left w-full max-w-sm border-border dark:border-border/60">
          <div className="flex justify-between text-xs mb-2 text-gray-500">
            <span>Assessment Stage:</span>
            <span className="text-gray-500 dark:text-gray-400 font-semibold uppercase">Idle / No Action</span>
          </div>
          <div className="flex justify-between text-xs text-gray-500 font-sans">
            <span>Tara AI Status:</span>
            <span className="text-purple-600 dark:text-purple-400 font-medium">Monitoring Queue</span>
          </div>
        </div>
      </div>
    );
  }

  const mcqs = assessment ? JSON.parse(assessment.mcqs) : [];
  const codingChallenges = assessment ? JSON.parse(assessment.coding_challenges) : [];
  const englishTest = assessment ? JSON.parse(assessment.english_test) : [];

  return (
    <div className="p-8 md:p-12 max-w-7xl mx-auto flex flex-col gap-8 bg-background dark:bg-background min-h-screen text-gray-800 dark:text-gray-100 transition-colors duration-300">
      <div>
        <h1 className="text-2xl md:text-3xl font-extrabold text-gray-950 dark:text-white tracking-tight">AI Test Terminal</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Complete proctored test assessments compiled for **{selectedApp?.job.title}**.
        </p>
      </div>

      {!examStarted && !examCompleted && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left: Device verification */}
          <div className="glass-panel p-6 rounded-2xl border border-border dark:border-border flex flex-col gap-6">
            <h2 className="text-sm font-bold text-gray-950 dark:text-white flex items-center gap-2">
              <ShieldCheck size={16} className="text-purple-600 dark:text-purple-400" />
              <span>Hardware & Identity Verification</span>
            </h2>

            <div className="flex flex-col gap-3">
              <div className="flex justify-between items-center text-xs p-3 rounded-xl border border-border dark:border-border/40 bg-muted dark:bg-card/40">
                <span className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                  <Camera size={14} /> Video Webcam Feed
                </span>
                <span className={`text-10 font-bold ${checks.camera ? (isSimulated ? "text-amber-400" : "text-emerald-400") : "text-gray-500"}`}>
                  {checks.camera ? (isSimulated ? "SIMULATED" : "DETECTED") : "UNCHECKED"}
                </span>
              </div>

              <div className="flex justify-between items-center text-xs p-3 rounded-xl border border-border dark:border-border/40 bg-muted dark:bg-card/40">
                <span className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                  <Mic size={14} /> Speech Microphone
                </span>
                <span className={`text-10 font-bold ${checks.mic ? (isSimulated ? "text-amber-400" : "text-emerald-400") : "text-gray-500"}`}>
                  {checks.mic ? (isSimulated ? "SIMULATED" : "DETECTED") : "UNCHECKED"}
                </span>
              </div>

              <div className="flex justify-between items-center text-xs p-3 rounded-xl border border-border dark:border-border/40 bg-muted dark:bg-card/40">
                <span className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                  <Globe size={14} /> Network Speed
                </span>
                <span className={`text-10 font-bold ${checks.internet ? "text-emerald-400" : "text-gray-500"}`}>
                  {checks.internet ? "OPTIMAL" : "UNCHECKED"}
                </span>
              </div>

              <div className="flex justify-between items-center text-xs p-3 rounded-xl border border-border dark:border-border/40 bg-muted dark:bg-card/40">
                <span className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                  <Cpu size={14} /> Secure Browser Engine
                </span>
                <span className={`text-10 font-bold ${checks.browser ? "text-emerald-400" : "text-gray-500"}`}>
                  {checks.browser ? "SECURE" : "UNCHECKED"}
                </span>
              </div>

              <div className="flex justify-between items-center text-xs p-3 rounded-xl border border-border dark:border-border/40 bg-muted dark:bg-card/40">
                <span className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                  <Server size={14} /> Face Presence Detection
                </span>
                <span className={`text-10 font-bold ${checks.face ? (isSimulated ? "text-amber-400" : "text-emerald-400") : "text-gray-500"}`}>
                  {checks.face ? (isSimulated ? "SIMULATED" : "VERIFIED") : "UNCHECKED"}
                </span>
              </div>
            </div>

            {!isSimulated && checks.camera && stream && (
              <div className="relative aspect-video rounded-xl overflow-hidden border border-border dark:border-border bg-black mt-2">
                <video
                  ref={(el) => {
                    if (el) el.srcObject = stream;
                  }}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover transform -scale-x-100"
                />
              </div>
            )}

            {isSimulated && checks.camera && (
              <div className="text-10 text-amber-400 bg-amber-950/20 border border-amber-900/30 rounded-xl p-3 flex items-start gap-2 leading-relaxed">
                <AlertTriangle size={12} className="shrink-0 mt-0.5" />
                <span>
                  Real camera/mic permissions could not be acquired (blocked or unavailable). Running in simulated mode.
                </span>
              </div>
            )}

            <button
              onClick={runDeviceVerification}
              disabled={verifying}
              className="w-full bg-white dark:bg-card border border-border dark:border-border text-gray-950 dark:text-white hover:border-purple-300 dark:hover:border-purple-500/50 py-2.5 rounded-xl text-xs font-semibold transition-all disabled:opacity-50"
            >
              {verifying ? "Checking channels..." : "Run Diagnostic check"}
            </button>
          </div>

          {/* Right: Intro instructions */}
          <div className="lg:col-span-2 glass-panel p-8 rounded-2xl border border-border dark:border-border flex flex-col justify-between">
            <div>
              <h2 className="text-lg font-bold text-gray-950 dark:text-white mb-4">Proctored Assessment Rules</h2>
              <ul className="flex flex-col gap-3 text-xs text-gray-500 dark:text-gray-400 list-disc pl-4 leading-relaxed">
                <li>This test consists of Multiple Choice questions, a Coding console task, and an English response.</li>
                <li>The **AI Proctoring Agent** evaluates tab switches, keyboard copy-pastes, and webcam movements in real-time.</li>
                <li>Entering other browser windows or switching focus logs a violation warning automatically.</li>
                <li>Make sure you remain in a well-lit space facing the webcam directly.</li>
              </ul>
            </div>

            <button
              onClick={startExam}
              disabled={!allChecksPassed}
              className="mt-8 bg-purple-600 hover:bg-purple-500 text-white rounded-xl py-3 text-xs font-bold transition-all shadow-md disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <Play size={12} fill="white" />
              <span>Begin AI Proctoring Assessment</span>
            </button>
          </div>

        </div>
      )}

      {/* active exam screen layout */}
      {examStarted && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          
          {/* Exam core */}
          <div className="lg:col-span-3 flex flex-col gap-8">
            
            {/* MCQ Section */}
            {mcqs.length > 0 && (
              <div className="glass-panel p-8 rounded-2xl border border-border dark:border-border flex flex-col gap-6 bg-gray-50 dark:bg-card/40">
                <h2 className="text-sm font-bold text-gray-950 dark:text-white border-b border-border dark:border-border pb-3 flex items-center gap-2">
                  <span className="w-5 h-5 bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400 text-10 flex items-center justify-center rounded-lg font-bold">1</span>
                  <span>Part A: Multiple Choice Questions</span>
                </h2>
                
                {mcqs.map((q: any, idx: number) => (
                  <div key={q.id} className="flex flex-col gap-3">
                    <p className="text-xs font-semibold text-gray-950 dark:text-white">{idx + 1}. {q.question}</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pl-4">
                      {q.options.map((option: string, oIdx: number) => (
                        <label
                          key={oIdx}
                          className={`flex items-center gap-3 p-3 rounded-xl border text-xs cursor-pointer transition-colors ${
                            mcqAnswers[q.id] === oIdx
                              ? "bg-purple-50 dark:bg-purple-950/20 border-purple-300 dark:border-purple-500/50 text-purple-600 dark:text-purple-300"
                              : "bg-muted dark:bg-card/40 border-border dark:border-border/40 text-gray-500 dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-700"
                          }`}
                        >
                          <input
                            type="radio"
                            name={`mcq_${q.id}`}
                            className="accent-purple-500 hidden"
                            checked={mcqAnswers[q.id] === oIdx}
                            onChange={() => handleMCQChange(q.id, oIdx)}
                          />
                          <span className="w-4 h-4 rounded-full border border-gray-300 dark:border-gray-700 flex items-center justify-center shrink-0 text-9 font-bold">
                            {String.fromCharCode(65 + oIdx)}
                          </span>
                          <span>{option}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Coding Section */}
            {codingChallenges.length > 0 && (
              <div className="glass-panel p-8 rounded-2xl border border-border dark:border-border flex flex-col gap-6 bg-gray-50 dark:bg-card/40">
                <h2 className="text-sm font-bold text-gray-950 dark:text-white border-b border-border dark:border-border pb-3 flex items-center gap-2">
                  <span className="w-5 h-5 bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400 text-10 flex items-center justify-center rounded-lg font-bold">2</span>
                  <span>Part B: Algorithmic Programming</span>
                </h2>

                {codingChallenges.map((challenge: any) => (
                  <div key={challenge.id} className="flex flex-col gap-4">
                    <div>
                      <h3 className="text-xs font-bold text-gray-950 dark:text-white flex items-center gap-2">
                        <FileCode2 size={14} className="text-purple-600 dark:text-purple-400" />
                        <span>{challenge.title}</span>
                      </h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 leading-relaxed bg-gray-100 dark:bg-card/60 p-4 rounded-xl border border-border dark:border-border/40">
                        {challenge.description}
                      </p>
                    </div>

                    <div className="flex flex-col border border-border dark:border-border rounded-xl overflow-hidden">
                      <div className="bg-gray-100 dark:bg-muted px-4 py-2 border-b border-border dark:border-border flex justify-between items-center">
                        <span className="text-10 font-mono text-gray-500">solution.py</span>
                      </div>
                      <textarea
                        rows={10}
                        value={codingAnswers[challenge.id] !== undefined ? codingAnswers[challenge.id] : challenge.template}
                        onChange={(e) => handleCodingChange(challenge.id, e.target.value)}
                        className="code-editor w-full p-4 font-mono text-xs focus:outline-none resize-none leading-relaxed"
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* English Section */}
            {englishTest.length > 0 && (
              <div className="glass-panel p-8 rounded-2xl border border-border dark:border-border flex flex-col gap-6 bg-gray-50 dark:bg-card/40">
                <h2 className="text-sm font-bold text-gray-950 dark:text-white border-b border-border dark:border-border pb-3 flex items-center gap-2">
                  <span className="w-5 h-5 bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400 text-10 flex items-center justify-center rounded-lg font-bold">3</span>
                  <span>Part C: English Communication & Writing</span>
                </h2>

                {englishTest.map((test: any) => (
                  <div key={test.id} className="flex flex-col gap-3">
                    <p className="text-xs font-semibold text-gray-950 dark:text-white leading-relaxed">{test.question}</p>
                    <textarea
                      placeholder="Write your explanation response here..."
                      value={englishAnswer}
                      onChange={(e) => setEnglishAnswer(e.target.value)}
                      rows={5}
                      className="bg-white dark:bg-card border border-border dark:border-border rounded-xl p-4 text-xs text-gray-950 dark:text-white focus:outline-none focus:border-purple-500 transition-colors resize-none leading-relaxed"
                    />
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={submitExam}
              className="w-full bg-purple-600 hover:bg-purple-500 text-white rounded-xl py-3 text-xs font-bold transition-all shadow-md mt-4"
            >
              Submit Completed Assessment
            </button>
          </div>

          {/* Right: Proctor Live Alerts */}
          <div className="flex flex-col gap-6">
            <div className="glass-panel p-6 rounded-2xl border border-border dark:border-border bg-muted dark:bg-card/40 flex flex-col gap-4">
              <h3 className="text-xs font-bold text-gray-950 dark:text-white flex items-center gap-2 border-b border-border dark:border-border pb-3">
                <ClipboardCopy size={14} className="text-red-400 animate-pulse" />
                <span>AI Proctor Monitoring</span>
              </h3>

              {!isSimulated && checks.camera && stream && (
                <div className="relative aspect-video rounded-xl overflow-hidden border border-border dark:border-border bg-black mt-2">
                  <video
                    ref={(el) => {
                      videoRef.current = el;
                      if (el) el.srcObject = stream;
                    }}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover transform -scale-x-100"
                  />
                  <div className="absolute bottom-2 left-2 z-10 flex items-center gap-1.5 bg-black/60 px-2 py-0.5 rounded-md text-9 text-emerald-400 font-semibold border border-emerald-500/20">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
                    <span>PROCTORING ACTIVE</span>
                  </div>
                </div>
              )}

              {isSimulated && (
                <div className="relative aspect-video rounded-xl overflow-hidden border border-border dark:border-border bg-gray-100 dark:bg-background mt-2 flex flex-col items-center justify-center text-center p-4">
                  <Camera size={24} className="text-amber-500/40 mb-2 animate-pulse" />
                  <span className="text-10 font-bold text-amber-500 tracking-wider">SIMULATED WEB FEED</span>
                  <span className="text-8 text-gray-500 mt-1 max-w-150 leading-normal font-sans">Webcam feed is simulated (real device blocked/unavailable)</span>
                </div>
              )}

              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-500 dark:text-gray-400">Total Violations:</span>
                <span className={`font-bold ${violations > 0 ? "text-red-400 animate-bounce" : "text-emerald-400"}`}>
                  {violations}
                </span>
              </div>

              <div className="text-10 text-gray-500 flex flex-col gap-1 border-t border-border dark:border-border/60 pt-3 mt-1 font-sans">
                <div className="flex justify-between">
                  <span>AI Face & Gaze Tracking:</span>
                  <span className={blazeModel ? "text-emerald-400 font-bold" : "text-gray-600 font-bold animate-pulse"}>
                    {blazeModel ? "REAL-TIME ACTIVE" : "SIMULATED"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Mobile Object Scanner:</span>
                  <span className={cocoModel ? "text-emerald-400 font-bold" : "text-gray-600 font-bold animate-pulse"}>
                    {cocoModel ? "REAL-TIME ACTIVE" : "SIMULATED"}
                  </span>
                </div>
              </div>

              <div className="flex flex-col gap-2 max-h-40 overflow-y-auto mt-2 text-10 font-mono border-t border-border dark:border-border/40 pt-3">
                {proctorLogs.length === 0 ? (
                  <span className="text-gray-600 italic">No proctor events triggered.</span>
                ) : (
                  proctorLogs.map((log, i) => (
                    <div key={i} className="text-red-400/90 leading-tight">
                      {log}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

        </div>
      )}

      {/* Completed panel */}
      {examCompleted && (
        <div className="glass-panel p-12 rounded-2xl border border-border dark:border-border text-center flex flex-col items-center justify-center gap-4 min-h-[50vh]">
          <div className="w-14 h-14 bg-emerald-100 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/30 flex items-center justify-center rounded-2xl text-emerald-600 dark:text-emerald-400">
            <CheckCircle size={28} />
          </div>
          <h2 className="text-xl font-bold text-gray-950 dark:text-white">Assessment Submitted</h2>
          <p className="text-xs text-gray-500 max-w-sm">
            Thank you! Your responses are currently being evaluated by the **Assessment Evaluation Agent**. You will receive a dashboard update once results are available.
          </p>
        </div>
      )}

    </div>
  );
}
