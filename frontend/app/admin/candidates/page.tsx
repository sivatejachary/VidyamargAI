"use client";

import { useEffect, useState } from "react";
import { apiService } from "@/services/api";
import { Award, FileText, X, MessageSquare, Folder, Download } from "lucide-react";
import { useWebSockets } from "@/hooks/useWebSockets";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";

export default function AdminCandidates() {
  const [rankings, setRankings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRank, setSelectedRank] = useState<any>(null);
  const [selectedApplication, setSelectedApplication] = useState<any>(null);
  
  const [screening, setScreening] = useState<any>(null);
  const [attempt, setAttempt] = useState<any>(null);
  const [interview, setInterview] = useState<any>(null);
  const [offer, setOffer] = useState<any>(null);
  const [candidateFiles, setCandidateFiles] = useState<any[]>([]);

  // Hackathon Assignment state
  const [assignTeamName, setAssignTeamName] = useState("");
  const [assignMentorName, setAssignMentorName] = useState("");
  const [assignProblemId, setAssignProblemId] = useState("q1");
  const [assignMembers, setAssignMembers] = useState("");
  const [assignSuccess, setAssignSuccess] = useState(false);
  const [currentCandidateEmail, setCurrentCandidateEmail] = useState("");
  const [currentCandidateId, setCurrentCandidateId] = useState<number | null>(null);

  // Live Candidate Chat state
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  const [activeChatTab, setActiveChatTab] = useState<string>("support");
  const [adminReplyText, setAdminReplyText] = useState<string>("");
  const [sendingMessage, setSendingMessage] = useState<boolean>(false);

  const fetchRankings = async () => {
    try {
      const data = await apiService.getRankings();
      setRankings(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRankings();
  }, []);

  // Set up WebSocket for live candidate messages
  const { addMessageListener } = useWebSockets("admin_portal");

  useEffect(() => {
    const unsubscribe = addMessageListener((event) => {
      if (event.type === "admin_chat_message" && selectedRank) {
        if (currentCandidateId === event.candidate_id) {
          setChatMessages((prev) => {
            if (prev.some((m) => m.id === event.message.id)) {
              return prev;
            }
            return [...prev, event.message];
          });
        }
      }
    });
    return () => unsubscribe();
  }, [addMessageListener, selectedRank, currentCandidateId]);

  const selectCandidate = async (rank: any) => {
    setSelectedRank(rank);
    setScreening(null);
    setAttempt(null);
    setInterview(null);
    setOffer(null);
    setCandidateFiles([]);
    setAssignSuccess(false);
    setChatMessages([]);
    setAdminReplyText("");
    setSelectedApplication(null);

    const appId = rank.application_id;
    try {
      // Lazy load related details
      const apps = await apiService.getApplications();
      const thisApp = apps.find((a: any) => a.id === appId);
      
      if (thisApp && thisApp.candidate) {
        setSelectedApplication(thisApp);
        const email = thisApp.candidate.user.email;
        setCurrentCandidateEmail(email);
        setCurrentCandidateId(thisApp.candidate.id);

        // Fetch candidate folder files list
        try {
          const files = await apiService.getCandidateFiles(thisApp.candidate.id);
          setCandidateFiles(files || []);
        } catch (filesErr) {
          console.error("Failed to load candidate files:", filesErr);
        }
        
        // Load existing assignment from database candidate profile
        if (thisApp.candidate.hackathon_team) {
          setAssignTeamName(thisApp.candidate.hackathon_team);
          setAssignMentorName(thisApp.candidate.assigned_mentor || "");
          setAssignProblemId(thisApp.candidate.hackathon_problem || "q1");
          setAssignMembers(thisApp.candidate.hackathon_members || "");
        } else {
          // Defaults if not set in DB, check localStorage
          const existing = localStorage.getItem(`hackathon_assignment_${email}`);
          if (existing) {
            try {
              const data = JSON.parse(existing);
              setAssignTeamName(data.teamName || "");
              setAssignMentorName(data.mentorName || "");
              setAssignProblemId(data.problemId || "q1");
              setAssignMembers(data.membersStr || "");
            } catch (e) {
              console.error(e);
            }
          } else {
            setAssignTeamName("");
            setAssignMentorName("");
            setAssignProblemId("q1");
            setAssignMembers("");
          }
        }

        // Fetch candidate live messages history
        try {
          const msgs = await apiService.getAdminCandidateMessages(thisApp.candidate.id);
          setChatMessages(msgs || []);
        } catch (msgErr) {
          console.error("Failed to load candidate messages:", msgErr);
        }
      }

      // Load screening reasoning
      if (thisApp && thisApp.screening_results?.length > 0) {
        setScreening(thisApp.screening_results[0]);
      } else {
        // Mock fallback if nested array is empty
        setScreening({
          raw_reasoning: "Candidate matches core skills. Shortlisted."
        });
      }

      // Load Assessment attempt
      if (thisApp && thisApp.assessment_attempts?.length > 0) {
        setAttempt(thisApp.assessment_attempts[0]);
      }

      // Load Interview Session
      if (thisApp && thisApp.interviews?.length > 0) {
        setInterview(thisApp.interviews[0]);
      }

      // Load Offer
      if (thisApp && thisApp.offers?.length > 0) {
        setOffer(thisApp.offers[0]);
      }
    } catch (err) {
      console.error("Failed to load candidate detailed metrics:", err);
    }
  };

  const handleSaveHackathonAssignment = async () => {
    if (!currentCandidateEmail || !currentCandidateId) return;
    
    // Parse members string into Member objects
    const membersArr = assignMembers
      .split(",")
      .map(name => name.trim())
      .filter(Boolean)
      .map((name, idx) => {
        const initials = name
          .split(" ")
          .map((n: string) => n[0])
          .join("")
          .toUpperCase()
          .slice(0, 2);
        return {
          initials,
          name,
          role: (idx === 0 ? "Team lead" : "Member") as "Team lead" | "Member"
        };
      });
      
    const assignment = {
      teamName: assignTeamName,
      mentorName: assignMentorName,
      problemId: assignProblemId,
      membersStr: assignMembers,
      members: membersArr
    };
    
    // Save to backend DB
    const assignData = {
      hackathon_team: assignTeamName,
      assigned_mentor: assignMentorName,
      hackathon_problem: assignProblemId,
      hackathon_members: assignMembers
    };
    
    try {
      await apiService.saveHackathonAssignment(currentCandidateId, assignData);
      localStorage.setItem(`hackathon_assignment_${currentCandidateEmail}`, JSON.stringify(assignment));
      setAssignSuccess(true);
      setTimeout(() => setAssignSuccess(false), 3000);
    } catch (err) {
      console.error("Failed to save hackathon assignment to database:", err);
    }
  };

  const handleSendAdminReply = async () => {
    if (!adminReplyText.trim() || !currentCandidateId || !selectedRank) return;
    
    setSendingMessage(true);
    try {
      const appId = selectedRank.application_id;
      const mentorNameClean = assignMentorName.replace(/\s+/g, "_").toLowerCase();
      
      let chatId = "support";
      let sender = "support";
      let senderName = "Vidyamarg Support";
      
      if (activeChatTab === "recruiter") {
        chatId = `hiring_team_${appId}`;
        sender = "recruiter";
        senderName = `${selectedRank.application?.job_title || "Company"} Hiring Team`;
      } else if (activeChatTab === "mentor") {
        chatId = `mentor_${mentorNameClean}`;
        sender = "mentor";
        senderName = `Mentor: ${assignMentorName || "Mentor"}`;
      }
      
      const savedMsg = await apiService.sendAdminMessage(
        currentCandidateId,
        chatId,
        sender,
        senderName,
        adminReplyText
      );
      
      if (savedMsg) {
        setChatMessages((prev) => {
          if (prev.some((m) => m.id === savedMsg.id)) {
            return prev;
          }
          return [...prev, savedMsg];
        });
        setAdminReplyText("");
      }
    } catch (err) {
      console.error("Failed to send admin reply:", err);
    } finally {
      setSendingMessage(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const s = status.toLowerCase();
    let variant: "primary" | "secondary" | "success" | "warning" | "destructive" | "outline" = "secondary";
    let text = status;

    if (s === "applied") { variant = "primary"; text = "Applied"; }
    else if (s === "screening") { variant = "warning"; text = "Screening"; }
    else if (s === "assessment") { variant = "warning"; text = "Assessment"; }
    else if (s === "interview") { variant = "primary"; text = "Interview"; }
    else if (s === "ranking") { variant = "warning"; text = "Ranking"; }
    else if (s === "recommendation") { variant = "success"; text = "Hiring Report"; }
    else if (s === "offer") { variant = "success"; text = "Offer Active"; }
    else if (s === "onboarding") { variant = "success"; text = "Onboarded"; }
    else if (s === "rejected") { variant = "destructive"; text = "Rejected"; }

    return <Badge variant={variant}>{text}</Badge>;
  };

  return (
    <div className="p-8 md:p-12 max-w-7xl mx-auto flex flex-col gap-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">Recruitment Pipeline Scoreboard</h1>
        <p className="text-sm text-gray-400 mt-1">
          Detailed breakdown of candidate final composite rankings, assessment evaluations, and proctor details.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Candidates Table List */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <Card className="overflow-hidden p-0 bg-[#0c0d14]/40">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-gray-400 border-collapse">
                <thead className="bg-[#0f1019] text-gray-300 font-bold border-b border-gray-800 text-[10px] uppercase tracking-wider">
                  <tr>
                    <th className="p-4">Rank</th>
                    <th className="p-4">Name</th>
                    <th className="p-4">Job Role</th>
                    <th className="p-4 text-center">Resume</th>
                    <th className="p-4 text-center">Test</th>
                    <th className="p-4 text-center">Interview</th>
                    <th className="p-4 text-center text-red-400">Proctor</th>
                    <th className="p-4 text-right">Composite</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60 font-medium">
                  {loading ? (
                    <tr>
                      <td colSpan={8} className="p-8 text-center text-gray-500">Loading scoreboard details...</td>
                    </tr>
                  ) : rankings.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="p-8 text-center text-gray-500">No candidate ranks calculated yet.</td>
                    </tr>
                  ) : (
                    rankings.map((r) => (
                      <tr 
                        key={r.id} 
                        onClick={() => selectCandidate(r)}
                        className={`hover:bg-gray-800/20 cursor-pointer transition-colors ${
                          selectedRank?.id === r.id ? "bg-purple-900/10 text-purple-300 border-l-2 border-purple-500" : ""
                        }`}
                      >
                        <td className="p-4 font-mono font-bold text-gray-500">#{r.rank}</td>
                        <td className="p-4 font-semibold text-white truncate max-w-[120px]">
                          {r.application?.candidate_name}
                        </td>
                        <td className="p-4 truncate max-w-[120px]">{r.application?.job_title}</td>
                        <td className="p-4 text-center">{r.resume_score.toFixed(0)}</td>
                        <td className="p-4 text-center">{r.assessment_score.toFixed(0)}</td>
                        <td className="p-4 text-center">{r.interview_score.toFixed(0)}</td>
                        <td className="p-4 text-center text-red-400">{r.fraud_penalty.toFixed(0)}</td>
                        <td className="p-4 text-right font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-400">
                          {r.final_score.toFixed(1)}%
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* Detailed scorecard panel */}
        <div className="flex flex-col gap-6">
          {selectedRank ? (
            <Card className="flex flex-col gap-6 max-h-[85vh] overflow-y-auto bg-[#0d0e15]/40">
              
              <div className="flex justify-between items-start border-b border-gray-800 pb-4">
                <div>
                  <h2 className="text-base font-extrabold text-white">
                    {selectedRank.application?.candidate_name}
                  </h2>
                  <p className="text-xs text-purple-400 mt-1">
                    Applied: {selectedRank.application?.job_title}
                  </p>
                </div>
                <button 
                  onClick={() => {
                    setSelectedRank(null);
                    setSelectedApplication(null);
                  }}
                  className="p-1 rounded-lg hover:bg-gray-800 text-gray-500 hover:text-white transition-colors"
                >
                  <X size={16} />
                </button>
              </div>

              {/* Status */}
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-400">Recruitment Status:</span>
                {getStatusBadge(selectedRank.application?.status || "")}
              </div>

              {/* Score breakdown */}
              <div className="flex flex-col gap-3 border-b border-gray-850 pb-4">
                <h3 className="text-xs font-bold text-white flex items-center gap-2">
                  <Award size={14} className="text-purple-400" />
                  <span>Metrics scorecard</span>
                </h3>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-3 bg-[#0c0d14]/40 border border-gray-800/40 rounded-xl">
                    <span className="text-[10px] text-gray-500 block">Resume Screen</span>
                    <span className="text-sm font-bold text-white mt-1 block">{selectedRank.resume_score.toFixed(0)}%</span>
                  </div>
                  <div className="p-3 bg-[#0c0d14]/40 border border-gray-800/40 rounded-xl">
                    <span className="text-[10px] text-gray-500 block">AI Test score</span>
                    <span className="text-sm font-bold text-white mt-1 block">{selectedRank.assessment_score.toFixed(0)}%</span>
                  </div>
                  <div className="p-3 bg-[#0c0d14]/40 border border-gray-800/40 rounded-xl">
                    <span className="text-[10px] text-gray-500 block">Tara Interview</span>
                    <span className="text-sm font-bold text-white mt-1 block">{selectedRank.interview_score.toFixed(0)}%</span>
                  </div>
                  <div className="p-3 bg-red-950/5 border border-red-900/10 rounded-xl">
                    <span className="text-[10px] text-red-500/70 block">Proctor Flags</span>
                    <span className="text-sm font-bold text-red-400 mt-1 block">{selectedRank.fraud_penalty.toFixed(0)} flags</span>
                  </div>
                </div>
              </div>

              {/* Screening summary */}
              {screening && (
                <div className="flex flex-col gap-2 border-b border-gray-850 pb-4 text-xs">
                  <h3 className="text-xs font-bold text-white flex items-center gap-2">
                    <FileText size={14} className="text-blue-400" />
                    <span>Screening Alignment Notes</span>
                  </h3>
                  <p className="text-gray-400 leading-relaxed bg-[#0c0d14]/40 p-3 rounded-xl border border-gray-800/40 italic">
                    "{screening.raw_reasoning}"
                  </p>
                </div>
              )}

              {/* Live transcript details */}
              {interview && (
                <div className="flex flex-col gap-2.5 border-b border-gray-850 pb-4 text-xs">
                  <h3 className="text-xs font-bold text-white flex items-center gap-2">
                    <MessageSquare size={14} className="text-indigo-400" />
                    <span>Conversation Dialogues</span>
                  </h3>
                  <div className="max-h-40 overflow-y-auto bg-[#08090e] border border-gray-800 rounded-xl p-3 font-mono text-[10px] flex flex-col gap-2">
                    {JSON.parse(interview.transcript || "[]").map((dia: any, idx: number) => (
                      <div key={idx} className="leading-relaxed">
                        <span className="text-purple-400 font-bold">{dia.role}: </span>
                        <span className="text-gray-400">{dia.text}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Resume & Profile Details */}
              <div className="flex flex-col gap-3 text-xs border-b border-gray-850 pb-4">
                <h3 className="text-xs font-bold text-white flex items-center gap-2">
                  <FileText size={14} className="text-blue-400" />
                  <span>Resume & Profile</span>
                </h3>

                {selectedApplication?.resume && (
                  <div className="flex items-center justify-between bg-[#0c0d14]/40 border border-gray-800/40 rounded-xl p-3">
                    <div className="flex items-center gap-2">
                      <FileText size={14} className="text-red-400" />
                      <div>
                        <span className="text-[10px] text-gray-500 block">Uploaded Resume</span>
                        <span className="text-xs font-semibold text-white truncate max-w-[150px] block">
                          {selectedApplication.resume.resume_url.split("/").pop()}
                        </span>
                      </div>
                    </div>
                    <a 
                      href={`${typeof window !== "undefined" && window.location.hostname === "localhost" ? "http://127.0.0.1:8000" : `http://${window.location.hostname}:8000`}${selectedApplication.resume.resume_url}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs font-bold text-white transition-colors flex items-center gap-1.5"
                    >
                      <span>Download</span>
                    </a>
                  </div>
                )}

                {selectedApplication?.candidate?.summary && (
                  <div className="bg-[#0c0d14]/40 border border-gray-800/40 rounded-xl p-3 text-xs">
                    <span className="text-[9px] text-gray-500 uppercase font-bold tracking-wider block mb-1">Professional Summary</span>
                    <p className="text-gray-300 leading-relaxed font-semibold">{selectedApplication.candidate.summary}</p>
                  </div>
                )}

                {selectedApplication?.candidate?.skills && (
                  <div className="bg-[#0c0d14]/40 border border-gray-800/40 rounded-xl p-3 text-xs">
                    <span className="text-[9px] text-gray-500 uppercase font-bold tracking-wider block mb-2">Skills (Tag Cloud)</span>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedApplication.candidate.skills.split(",").map((s: string, idx: number) => {
                        const clean = s.trim();
                        if (!clean) return null;
                        return (
                          <span key={idx} className="px-2 py-0.5 rounded bg-gray-800 text-[10px] font-bold text-gray-300">
                            {clean}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}

                {(() => {
                  const expListStr = selectedApplication?.candidate?.experience;
                  if (!expListStr || expListStr === "[]") return null;
                  try {
                    const list = JSON.parse(expListStr);
                    if (list.length === 0) return null;
                    return (
                      <div className="bg-[#0c0d14]/40 border border-gray-800/40 rounded-xl p-3 text-xs">
                        <span className="text-[9px] text-gray-500 uppercase font-bold tracking-wider block mb-2">Extracted Experience</span>
                        <div className="space-y-2.5">
                          {list.map((exp: any, idx: number) => (
                            <div key={idx} className="border-l border-purple-500 pl-2.5 py-0.5 space-y-0.5">
                              <div className="flex justify-between items-start">
                                <span className="font-bold text-white text-[11px]">{exp.role}</span>
                                <span className="text-[9px] text-gray-505">{exp.years}</span>
                              </div>
                              <div className="text-[10px] text-purple-400 font-semibold">{exp.company}</div>
                              {exp.description && (
                                <p className="text-[10px] text-gray-400 leading-normal mt-1">{exp.description}</p>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  } catch (e) {
                    return null;
                  }
                })()}

                {(() => {
                  const eduListStr = selectedApplication?.candidate?.education;
                  if (!eduListStr || eduListStr === "[]") return null;
                  try {
                    const list = JSON.parse(eduListStr);
                    if (list.length === 0) return null;
                    return (
                      <div className="bg-[#0c0d14]/40 border border-gray-800/40 rounded-xl p-3 text-xs">
                        <span className="text-[9px] text-gray-500 uppercase font-bold tracking-wider block mb-2">Extracted Education</span>
                        <div className="space-y-2">
                          {list.map((edu: any, idx: number) => (
                            <div key={idx} className="border-l border-blue-500 pl-2.5 py-0.5">
                              <div className="flex justify-between items-start">
                                <span className="font-bold text-white text-[11px]">{edu.degree}</span>
                                <span className="text-[9px] text-gray-505">{edu.year}</span>
                              </div>
                              <div className="text-[10px] text-blue-400 font-semibold">{edu.school}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  } catch (e) {
                    return null;
                  }
                })()}

                {(() => {
                  const projListStr = selectedApplication?.candidate?.projects;
                  if (!projListStr || projListStr === "[]") return null;
                  try {
                    const list = JSON.parse(projListStr);
                    if (list.length === 0) return null;
                    return (
                      <div className="bg-[#0c0d14]/40 border border-gray-800/40 rounded-xl p-3 text-xs">
                        <span className="text-[9px] text-gray-500 uppercase font-bold tracking-wider block mb-2">Extracted Projects</span>
                        <div className="space-y-2.5">
                          {list.map((proj: any, idx: number) => (
                            <div key={idx} className="border-l border-emerald-500 pl-2.5 py-0.5 space-y-0.5">
                              <span className="font-bold text-white text-[11px] block">{proj.name}</span>
                              {proj.description && (
                                <p className="text-[10px] text-gray-400 leading-normal">{proj.description}</p>
                              )}
                              {proj.technologies && (
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {proj.technologies.split(",").map((tech: string, tIdx: number) => (
                                    <span key={tIdx} className="px-1.5 py-0.5 rounded bg-emerald-955/40 border border-emerald-900/30 text-[9px] text-emerald-400">
                                      {tech.trim()}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  } catch (e) {
                    return null;
                  }
                })()}

                {selectedApplication?.candidate?.certifications && (
                  <div className="bg-[#0c0d14]/40 border border-gray-800/40 rounded-xl p-3 text-xs">
                    <span className="text-[9px] text-gray-500 uppercase font-bold tracking-wider block mb-2">Certifications</span>
                    <div className="flex flex-wrap gap-1">
                      {selectedApplication.candidate.certifications.split(",").map((cert: string, idx: number) => {
                        const clean = cert.trim();
                        if (!clean) return null;
                        return (
                          <span key={idx} className="px-2 py-0.5 rounded bg-gray-800 text-[10px] font-bold text-gray-300">
                            {clean}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              {/* Candidate Storage Assets */}
              <div className="flex flex-col gap-3 text-xs border-b border-gray-850 pb-4">
                <h3 className="text-xs font-bold text-white flex items-center gap-2">
                  <Folder size={14} className="text-amber-400" />
                  <span>Candidate Storage Assets</span>
                </h3>
                {candidateFiles.length > 0 ? (
                  <div className="space-y-2">
                    {candidateFiles.map((file, idx) => (
                      <div key={idx} className="flex items-center justify-between bg-[#0c0d14]/40 border border-gray-800/40 rounded-xl p-3">
                        <div className="flex items-center gap-2 min-w-0">
                          <FileText size={14} className="text-amber-505 shrink-0" />
                          <div className="min-w-0">
                            <span className="text-[10px] text-gray-500 block uppercase font-bold tracking-wider">{file.category}</span>
                            <span className="text-xs font-semibold text-white truncate block" title={file.name}>
                              {file.name}
                            </span>
                          </div>
                        </div>
                        <a 
                          href={`${typeof window !== "undefined" && window.location.hostname === "localhost" ? "http://127.0.0.1:8000" : `http://${window.location.hostname}:8000`}${file.url}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs font-bold text-white transition-colors flex items-center gap-1.5 shrink-0"
                        >
                          <span>Open</span>
                        </a>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4 text-xs text-gray-500 italic bg-[#0c0d14]/20 border border-dashed border-gray-800 rounded-xl font-semibold">
                    No storage files found for this candidate yet.
                  </div>
                )}
              </div>

              {/* Hackathon Team & Mentor Assignment */}
              <div className="flex flex-col gap-3 text-xs">
                <h3 className="text-xs font-bold text-white flex items-center gap-2">
                  <Award size={14} className="text-purple-400" />
                  <span>Hackathon Assignment</span>
                </h3>
                
                <div className="flex flex-col gap-3 bg-[#0c0d14]/40 p-4 rounded-xl border border-gray-800/40">
                  <div>
                    <label className="text-[9px] text-gray-500 uppercase font-bold tracking-wider block mb-1">Team Name</label>
                    <Input 
                      type="text" 
                      placeholder="e.g. Team Alpha"
                      value={assignTeamName}
                      onChange={(e) => setAssignTeamName(e.target.value)}
                    />
                  </div>

                  <div>
                    <label className="text-[9px] text-gray-500 uppercase font-bold tracking-wider block mb-1">Mentor Name</label>
                    <Input 
                      type="text" 
                      placeholder="e.g. Dr. Amit Sharma"
                      value={assignMentorName}
                      onChange={(e) => setAssignMentorName(e.target.value)}
                    />
                  </div>

                  <div>
                    <label className="text-[9px] text-gray-500 uppercase font-bold tracking-wider block mb-1">Assigned Problem</label>
                    <Select
                      value={assignProblemId}
                      onChange={(e) => setAssignProblemId(e.target.value)}
                    >
                      <option value="q1">Q1. AI Safety Guardrail System</option>
                      <option value="q2">Q2. Self-Improving Code Gen Agent</option>
                      <option value="q3">Q3. Log Generation & CVE Scanning</option>
                      <option value="q4">Q4. PDF-Aware Smart Chatbot (RAG)</option>
                      <option value="q5">Q5. Intelligent Web Crawler</option>
                    </Select>
                  </div>

                  <div>
                    <label className="text-[9px] text-gray-500 uppercase font-bold tracking-wider block mb-1">Team Members (comma separated)</label>
                    <Textarea 
                      placeholder="e.g. Jane Doe, John Smith"
                      value={assignMembers}
                      onChange={(e) => setAssignMembers(e.target.value)}
                      className="min-h-[50px]"
                    />
                  </div>

                  <Button
                    onClick={handleSaveHackathonAssignment}
                    className="w-full mt-2"
                  >
                    Save Hackathon Assignment
                  </Button>

                  {assignSuccess && (
                    <Alert variant="success" className="mt-1">
                      Assignment saved successfully!
                    </Alert>
                  )}
                </div>
              </div>

              {/* Live Chat with Candidate Section */}
              <div className="flex flex-col gap-3 text-xs border-t border-gray-850 pt-5 mt-2">
                <h3 className="text-xs font-bold text-white flex items-center gap-2">
                  <MessageSquare size={14} className="text-purple-400" />
                  <span>Live Chat with Candidate</span>
                </h3>
                
                <div className="flex flex-col gap-2 bg-[#0c0d14]/40 p-4 rounded-xl border border-gray-800/40">
                  {/* Chat Sender selector tabs */}
                  <div className="flex bg-[#08090e] p-1 rounded-lg border border-gray-800">
                    {[
                      { id: "support", label: "Support" },
                      { id: "recruiter", label: "Hiring Team" },
                      { id: "mentor", label: "Mentor" }
                    ].map((tab) => (
                      <button
                        key={tab.id}
                        type="button"
                        onClick={() => setActiveChatTab(tab.id)}
                        className={`flex-1 py-1 rounded text-[9px] font-bold transition-all cursor-pointer ${
                          activeChatTab === tab.id 
                            ? "bg-purple-600 text-white" 
                            : "text-gray-400 hover:text-white"
                        }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>

                  {/* Messages list for selected tab */}
                  <div className="h-40 overflow-y-auto bg-[#08090e] border border-gray-800 rounded-lg p-3 flex flex-col gap-2.5">
                    {(() => {
                      const appId = selectedRank.application_id;
                      const mentorNameClean = assignMentorName.replace(/\s+/g, "_").toLowerCase();
                      
                      let activeChatId = "support";
                      if (activeChatTab === "recruiter") {
                        activeChatId = `hiring_team_${appId}`;
                      } else if (activeChatTab === "mentor") {
                        activeChatId = `mentor_${mentorNameClean}`;
                      }
                      
                      const filtered = chatMessages.filter((m) => m.chat_id === activeChatId);
                      if (filtered.length === 0) {
                        return (
                          <div className="h-full flex items-center justify-center text-[10px] text-gray-500 italic">
                            No messages in this chat.
                          </div>
                        );
                      }
                      
                      return filtered.map((m) => {
                        const isCandidate = m.sender === "user";
                        return (
                          <div key={m.id} className={`flex flex-col max-w-[85%] ${isCandidate ? "mr-auto" : "ml-auto"}`}>
                            <span className="text-[8px] text-gray-500 font-bold mb-0.5">
                              {isCandidate ? selectedRank.application?.candidate_name : m.sender_name}
                            </span>
                            <div className={`p-2 rounded-lg text-[10px] leading-relaxed border ${
                              isCandidate 
                                ? "bg-gray-800 text-white border-transparent"
                                : "bg-purple-900/20 text-purple-300 border-purple-800/40"
                            }`}>
                              <p className="whitespace-pre-wrap">{m.text}</p>
                              <span className="text-[7px] text-gray-500 block text-right mt-1">
                                {new Date(m.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </span>
                            </div>
                          </div>
                        );
                      });
                    })()}
                  </div>

                  {/* Reply Input */}
                  <div className="flex gap-2 items-center mt-1">
                    <Input 
                      type="text" 
                      placeholder="Type a reply..."
                      value={adminReplyText}
                      onChange={(e) => setAdminReplyText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") handleSendAdminReply();
                      }}
                    />
                    <Button
                      onClick={handleSendAdminReply}
                      disabled={sendingMessage || !adminReplyText.trim()}
                      size="sm"
                    >
                      Send
                    </Button>
                  </div>

                </div>
              </div>
            </Card>
          ) : (
            <Card className="text-center text-gray-500 h-64 flex items-center justify-center bg-[#0d0e15]/40">
              Select a candidate from the ranking list to load their full diagnostic report files.
            </Card>
          )}
        </div>

      </div>
    </div>
  );
}
