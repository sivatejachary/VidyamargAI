"use client";

import { useEffect, useState } from "react";
import { apiService, getBackendBaseUrl } from "@/services/api";
import { Award, FileText, X, MessageSquare, Folder, Download, Users } from "lucide-react";
import { useWebSockets } from "@/hooks/useWebSockets";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";

export default function AdminCandidates() {
  const [candidates, setCandidates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCandidate, setSelectedCandidate] = useState<any>(null);
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

  const fetchCandidates = async () => {
    try {
      const data = await apiService.getCandidates();
      setCandidates(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCandidates();
  }, []);

  // Set up WebSocket for live candidate messages
  const { addMessageListener } = useWebSockets("admin_portal");

  useEffect(() => {
    const unsubscribe = addMessageListener((event) => {
      if (event.type === "admin_chat_message" && selectedCandidate) {
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
  }, [addMessageListener, selectedCandidate, currentCandidateId]);

  const selectCandidate = async (candidate: any) => {
    setSelectedCandidate(candidate);
    setCandidateFiles([]);
    setAssignSuccess(false);
    setChatMessages([]);
    setAdminReplyText("");

    setCurrentCandidateEmail(candidate.email);
    setCurrentCandidateId(candidate.id);

    // Lazy load related details
    try {
      const files = await apiService.getCandidateFiles(candidate.id);
      setCandidateFiles(files || []);
    } catch (filesErr) {
      console.error("Failed to load candidate files:", filesErr);
    }
    
    // Load existing assignment from database candidate profile
    if (candidate.hackathon_team) {
      setAssignTeamName(candidate.hackathon_team);
      setAssignMentorName(candidate.assigned_mentor || "");
      setAssignProblemId(candidate.hackathon_problem || "q1");
      setAssignMembers(candidate.hackathon_members || "");
    } else {
      setAssignTeamName("");
      setAssignMentorName("");
      setAssignProblemId("q1");
      setAssignMembers("");
    }

    // Fetch candidate live messages history
    try {
      const msgs = await apiService.getAdminCandidateMessages(candidate.id);
      setChatMessages(msgs || []);
    } catch (msgErr) {
      console.error("Failed to load candidate messages:", msgErr);
    }
  };

  const handleSaveHackathonAssignment = async () => {
    if (!currentCandidateEmail || !currentCandidateId) return;
    
    const assignData = {
      teamName: assignTeamName,
      mentorName: assignMentorName,
      problemId: assignProblemId,
      membersStr: assignMembers
    };

    try {
      await apiService.saveHackathonAssignment(currentCandidateId, assignData);
      setAssignSuccess(true);
      // Refresh candidates list to update displayed team details
      fetchCandidates();
      
      // Update selectedCandidate object with newly saved data
      if (selectedCandidate) {
        setSelectedCandidate((prev: any) => ({
          ...prev,
          hackathon_team: assignTeamName,
          assigned_mentor: assignMentorName,
          hackathon_problem: assignProblemId,
          hackathon_members: assignMembers
        }));
      }
      
      setTimeout(() => setAssignSuccess(false), 3000);
    } catch (err) {
      console.error("Failed to save hackathon assignment:", err);
    }
  };

  const handleSendAdminReply = async () => {
    if (!adminReplyText.trim() || !currentCandidateId || !selectedCandidate) return;
    
    setSendingMessage(true);
    try {
      const mentorNameClean = assignMentorName.replace(/\s+/g, "_").toLowerCase();
      
      let chatId = "support";
      let sender = "support";
      let senderName = "Vidyamarg Support";
      
      if (activeChatTab === "mentor") {
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

  const getResumeStatusBadge = (status: string) => {
    const s = (status || "").toLowerCase();
    let variant: "primary" | "secondary" | "success" | "warning" | "destructive" | "outline" = "secondary";
    if (s === "completed" || s === "processed") variant = "success";
    else if (s === "pending" || s === "processing") variant = "warning";
    else if (s === "failed" || s === "error") variant = "destructive";
    return <Badge variant={variant}>{status || "Unuploaded"}</Badge>;
  };

  return (
    <div className="p-8 md:p-12 max-w-7xl mx-auto flex flex-col gap-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight flex items-center gap-2">
          <Users size={28} className="text-purple-400" />
          <span>Student Roster & Hackathon Center</span>
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Track registered candidates, active resumes, support chats, and assign hackathon/mentor details.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Candidates Table List */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          <Card className="overflow-hidden p-0 bg-card/40">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-muted-foreground border-collapse">
                <thead className="bg-muted text-muted-foreground font-bold border-b border-border text-10 uppercase tracking-wider">
                  <tr>
                    <th className="p-4">Name</th>
                    <th className="p-4">Email</th>
                    <th className="p-4">Resume Status</th>
                    <th className="p-4">Hackathon Team</th>
                    <th className="p-4">Assigned Mentor</th>
                    <th className="p-4 text-right">Registered</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800/60 font-medium">
                  {loading ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-muted-foreground">Loading student roster...</td>
                    </tr>
                  ) : candidates.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-muted-foreground">No students registered yet.</td>
                    </tr>
                  ) : (
                    candidates.map((c) => (
                      <tr 
                        key={c.id} 
                        onClick={() => selectCandidate(c)}
                        className={`hover:bg-muted/20 cursor-pointer transition-colors ${
                          selectedCandidate?.id === c.id ? "bg-purple-900/10 text-purple-300 border-l-2 border-purple-500" : ""
                        }`}
                      >
                        <td className="p-4 font-semibold text-white truncate max-w-120">
                          {c.full_name}
                        </td>
                        <td className="p-4 truncate max-w-120">{c.email}</td>
                        <td className="p-4">{getResumeStatusBadge(c.resume_status)}</td>
                        <td className="p-4 truncate max-w-120">{c.hackathon_team || <span className="text-gray-600 italic">Unassigned</span>}</td>
                        <td className="p-4 truncate max-w-120">{c.assigned_mentor || <span className="text-gray-600 italic">Unassigned</span>}</td>
                        <td className="p-4 text-right text-muted-foreground font-mono">
                          {c.created_at ? new Date(c.created_at).toLocaleDateString() : "-"}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        {/* Detailed profile panel */}
        <div className="flex flex-col gap-6">
          {selectedCandidate ? (
            <Card className="flex flex-col gap-6 max-h-85-vh overflow-y-auto bg-card/40">
              
              <div className="flex justify-between items-start border-b border-border pb-4">
                <div>
                  <h2 className="text-base font-extrabold text-white">
                    {selectedCandidate.full_name}
                  </h2>
                  <p className="text-xs text-purple-500 mt-1">
                    {selectedCandidate.email}
                  </p>
                </div>
                <button 
                  onClick={() => {
                    setSelectedCandidate(null);
                  }}
                  className="p-1 rounded-lg hover:bg-muted text-muted-foreground hover:text-white transition-colors"
                >
                  <X size={16} />
                </button>
              </div>

              {/* Status */}
              <div className="flex justify-between items-center text-xs">
                <span className="text-muted-foreground">Account Status:</span>
                <Badge variant="primary">{selectedCandidate.status || "Registered"}</Badge>
              </div>

              {/* Resume & Profile Details */}
              <div className="flex flex-col gap-3 text-xs border-b border-gray-855 pb-4">
                <h3 className="text-xs font-bold text-white flex items-center gap-2">
                  <FileText size={14} className="text-blue-500" />
                  <span>Resume & Profile</span>
                </h3>

                {selectedCandidate.resume && (
                  <div className="flex items-center justify-between bg-card/40 border border-border/40 rounded-xl p-3">
                    <div className="flex items-center gap-2">
                      <FileText size={14} className="text-red-400" />
                      <div>
                        <span className="text-10 text-muted-foreground block">Active Resume</span>
                        <span className="text-xs font-semibold text-white truncate max-w-150 block">
                          {selectedCandidate.resume.resume_url.split("/").pop()}
                        </span>
                      </div>
                    </div>
                    <a 
                      href={`${getBackendBaseUrl()}${selectedCandidate.resume.resume_url}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1.5 rounded-lg bg-muted hover:bg-gray-700 text-xs font-bold text-white transition-colors flex items-center gap-1.5"
                    >
                      <span>Download</span>
                    </a>
                  </div>
                )}

                {selectedCandidate.summary && (
                  <div className="bg-card/40 border border-border/40 rounded-xl p-3 text-xs">
                    <span className="text-9 text-muted-foreground uppercase font-bold tracking-wider block mb-1">Professional Summary</span>
                    <p className="text-muted-foreground leading-relaxed font-semibold">{selectedCandidate.summary}</p>
                  </div>
                )}

                {selectedCandidate.skills && (
                  <div className="bg-card/40 border border-border/40 rounded-xl p-3 text-xs">
                    <span className="text-9 text-muted-foreground uppercase font-bold tracking-wider block mb-2">Skills</span>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedCandidate.skills.split(",").map((s: string, idx: number) => {
                        const clean = s.trim();
                        if (!clean) return null;
                        return (
                          <span key={idx} className="px-2 py-0.5 rounded bg-muted text-10 font-bold text-muted-foreground">
                            {clean}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}

                {(() => {
                  const expListStr = selectedCandidate.experience;
                  if (!expListStr || expListStr === "[]") return null;
                  try {
                    const list = JSON.parse(expListStr);
                    if (list.length === 0) return null;
                    return (
                      <div className="bg-card/40 border border-border/40 rounded-xl p-3 text-xs">
                        <span className="text-9 text-muted-foreground uppercase font-bold tracking-wider block mb-2">Experience</span>
                        <div className="space-y-2.5">
                          {list.map((exp: any, idx: number) => (
                            <div key={idx} className="border-l border-purple-500 pl-2.5 py-0.5 space-y-0.5">
                              <div className="flex justify-between items-start">
                                <span className="font-bold text-white text-11">{exp.role}</span>
                                <span className="text-9 text-muted-foreground">{exp.years}</span>
                              </div>
                              <div className="text-10 text-purple-500 font-semibold">{exp.company}</div>
                              {exp.description && (
                                <p className="text-10 text-muted-foreground leading-normal mt-1">{exp.description}</p>
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
                  const eduListStr = selectedCandidate.education;
                  if (!eduListStr || eduListStr === "[]") return null;
                  try {
                    const list = JSON.parse(eduListStr);
                    if (list.length === 0) return null;
                    return (
                      <div className="bg-card/40 border border-border/40 rounded-xl p-3 text-xs">
                        <span className="text-9 text-muted-foreground uppercase font-bold tracking-wider block mb-2">Education</span>
                        <div className="space-y-2">
                          {list.map((edu: any, idx: number) => (
                            <div key={idx} className="border-l border-blue-500 pl-2.5 py-0.5">
                              <div className="flex justify-between items-start">
                                <span className="font-bold text-white text-11">{edu.degree}</span>
                                <span className="text-9 text-muted-foreground">{edu.year}</span>
                              </div>
                              <div className="text-10 text-blue-500 font-semibold">{edu.school}</div>
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
                  const projListStr = selectedCandidate.projects;
                  if (!projListStr || projListStr === "[]") return null;
                  try {
                    const list = JSON.parse(projListStr);
                    if (list.length === 0) return null;
                    return (
                      <div className="bg-card/40 border border-border/40 rounded-xl p-3 text-xs">
                        <span className="text-9 text-muted-foreground uppercase font-bold tracking-wider block mb-2">Projects</span>
                        <div className="space-y-2.5">
                          {list.map((proj: any, idx: number) => (
                            <div key={idx} className="border-l border-emerald-500 pl-2.5 py-0.5 space-y-0.5">
                              <span className="font-bold text-white text-11 block">{proj.name}</span>
                              {proj.description && (
                                <p className="text-10 text-muted-foreground leading-normal">{proj.description}</p>
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
              </div>

              {/* Candidate Storage Assets */}
              <div className="flex flex-col gap-3 text-xs border-b border-gray-855 pb-4">
                <h3 className="text-xs font-bold text-white flex items-center gap-2">
                  <Folder size={14} className="text-amber-400" />
                  <span>Candidate Storage Assets</span>
                </h3>
                {candidateFiles.length > 0 ? (
                  <div className="space-y-2">
                    {candidateFiles.map((file, idx) => (
                      <div key={idx} className="flex items-center justify-between bg-card/40 border border-border/40 rounded-xl p-3">
                        <div className="flex items-center gap-2 min-w-0">
                          <FileText size={14} className="text-amber-505 shrink-0" />
                          <div className="min-w-0">
                            <span className="text-10 text-muted-foreground block uppercase font-bold tracking-wider">{file.category}</span>
                            <span className="text-xs font-semibold text-white truncate block" title={file.name}>
                              {file.name}
                            </span>
                          </div>
                        </div>
                        <a 
                          href={`${getBackendBaseUrl()}${file.url}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-3 py-1.5 rounded-lg bg-muted hover:bg-gray-700 text-xs font-bold text-white transition-colors flex items-center gap-1.5 shrink-0"
                        >
                          <span>Open</span>
                        </a>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4 text-xs text-muted-foreground italic bg-card/20 border border-dashed border-border rounded-xl font-semibold">
                    No storage files found for this candidate yet.
                  </div>
                )}
              </div>

              {/* Hackathon Team & Mentor Assignment */}
              <div className="flex flex-col gap-3 text-xs">
                <h3 className="text-xs font-bold text-white flex items-center gap-2">
                  <Award size={14} className="text-purple-500" />
                  <span>Hackathon Assignment</span>
                </h3>
                
                <div className="flex flex-col gap-3 bg-card/40 p-4 rounded-xl border border-border/40">
                  <div>
                    <label className="text-9 text-muted-foreground uppercase font-bold tracking-wider block mb-1">Team Name</label>
                    <Input 
                      type="text" 
                      placeholder="e.g. Team Alpha"
                      value={assignTeamName}
                      onChange={(e) => setAssignTeamName(e.target.value)}
                    />
                  </div>

                  <div>
                    <label className="text-9 text-muted-foreground uppercase font-bold tracking-wider block mb-1">Mentor Name</label>
                    <Input 
                      type="text" 
                      placeholder="e.g. Dr. Amit Sharma"
                      value={assignMentorName}
                      onChange={(e) => setAssignMentorName(e.target.value)}
                    />
                  </div>

                  <div>
                    <label className="text-9 text-muted-foreground uppercase font-bold tracking-wider block mb-1">Assigned Problem</label>
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
                    <label className="text-9 text-muted-foreground uppercase font-bold tracking-wider block mb-1">Team Members (comma separated)</label>
                    <Textarea 
                      placeholder="e.g. Jane Doe, John Smith"
                      value={assignMembers}
                      onChange={(e) => setAssignMembers(e.target.value)}
                      className="min-h-50"
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
                  <MessageSquare size={14} className="text-purple-500" />
                  <span>Live Chat with Candidate</span>
                </h3>
                
                <div className="flex flex-col gap-2 bg-card/40 p-4 rounded-xl border border-border/40">
                  {/* Chat Sender selector tabs */}
                  <div className="flex bg-background p-1 rounded-lg border border-border">
                    {[
                      { id: "support", label: "Support" },
                      { id: "mentor", label: "Mentor" }
                    ].map((tab) => (
                      <button
                        key={tab.id}
                        type="button"
                        onClick={() => setActiveChatTab(tab.id)}
                        className={`flex-1 py-1 rounded text-9 font-bold transition-all cursor-pointer ${
                          activeChatTab === tab.id 
                            ? "bg-purple-600 text-white" 
                            : "text-muted-foreground hover:text-white"
                        }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>

                  {/* Messages list for selected tab */}
                  <div className="h-40 overflow-y-auto bg-background border border-border rounded-lg p-3 flex flex-col gap-2.5">
                    {(() => {
                      const mentorNameClean = assignMentorName.replace(/\s+/g, "_").toLowerCase();
                      
                      let activeChatId = "support";
                      if (activeChatTab === "mentor") {
                        activeChatId = `mentor_${mentorNameClean}`;
                      }
                      
                      const filtered = chatMessages.filter((m) => m.chat_id === activeChatId);
                      if (filtered.length === 0) {
                        return (
                          <div className="h-full flex items-center justify-center text-10 text-muted-foreground italic">
                            No messages in this chat.
                          </div>
                        );
                      }
                      
                      return filtered.map((m) => {
                        const isCandidate = m.sender === "user";
                        return (
                          <div key={m.id} className={`flex flex-col max-w-85-pct ${isCandidate ? "mr-auto" : "ml-auto"}`}>
                            <span className="text-8 text-muted-foreground font-bold mb-0.5">
                              {isCandidate ? selectedCandidate.full_name : m.sender_name}
                            </span>
                            <div className={`p-2 rounded-lg text-10 leading-relaxed border ${
                              isCandidate 
                                ? "bg-muted text-white border-transparent"
                                : "bg-purple-900/20 text-purple-300 border-purple-800/40"
                            }`}>
                              <p className="whitespace-pre-wrap">{m.text}</p>
                              <span className="text-7 text-muted-foreground block text-right mt-1">
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
            <Card className="text-center text-muted-foreground h-64 flex items-center justify-center bg-card/40">
              Select a student from the roster list to load their full profile and assignment controls.
            </Card>
          )}
        </div>

      </div>
    </div>
  );
}
