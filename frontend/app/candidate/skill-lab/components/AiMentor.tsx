"use client";

import React, { useState, useEffect, useRef } from "react";
import { GraduationCap, X, ArrowRight, Play, CheckSquare, Info, Plus, Mic, ArrowUp, FileText, List } from "lucide-react";
import { apiService } from "@/services/api";

interface Session {
  id: string;
  name: string;
  roadmapsCount: number;
  progress: number;
  evalsPending: number;
  skills: string[];
  subTopics: { id: string; name: string; isDone: boolean }[];
}

interface AiMentorProps {
  email: string | null;
  fullName: string | null;
  profile: any;
  loadData: () => Promise<void>;
  setXp: React.Dispatch<React.SetStateAction<number>>;
  enrollments: any[];
  courses: any[];
}

export default function AiMentor({
  email,
  fullName,
  profile,
  loadData,
  setXp,
  enrollments,
  courses
}: AiMentorProps) {
  const firstName = fullName ? fullName.split(" ")[0] : "Anusha";

  // Mentor Chat States
  const [mentorMessages, setMentorMessages] = useState<{ sender: "user" | "tush"; text: string }[]>([]);
  const [mentorQuery, setMentorQuery] = useState("");
  const [mentorLoading, setMentorLoading] = useState(false);

  // Study Sessions (Roadmaps) States
  const [sessions, setSessions] = useState<Session[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedSessionDetails, setSelectedSessionDetails] = useState<Session | null>(null);
  const [sessionName, setSessionName] = useState("");
  const [selectedSkill, setSelectedSkill] = useState("Python Backend, FastAPI, SQL");

  // Sidebar toggle state
  const [showSidebar, setShowSidebar] = useState(false);

  // Auto-resize refs & effects
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [mentorQuery]);

  // Scroll to bottom on new messages
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [mentorMessages, mentorLoading]);

  // Speech to Text (STT) state & handlers
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  const startListening = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser. Please try Chrome or Safari.");
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const rec = new SpeechRecognition();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = "en-US";

    rec.onstart = () => {
      setIsListening(true);
    };

    rec.onresult = (event: any) => {
      let finalTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        }
      }
      if (finalTranscript) {
        setMentorQuery((prev) => prev + (prev.endsWith(" ") || prev === "" ? "" : " ") + finalTranscript);
      }
    };

    rec.onerror = (e: any) => {
      console.error("Speech recognition error:", e);
      setIsListening(false);
    };

    rec.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = rec;
    rec.start();
  };

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  // File Upload states and handlers
  const [attachments, setAttachments] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handlePlusClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      setAttachments((prev) => [...prev, ...selectedFiles]);
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, idx) => idx !== index));
  };

  // Load study sessions dynamically from enrollments & custom sessions
  useEffect(() => {
    if (email && enrollments && courses) {
      const enrollSessions: Session[] = enrollments.map((enroll: any) => {
        const courseObj = courses.find(c => c.id === enroll.course_id) || enroll.course;
        const name = courseObj?.title || `Course ${enroll.course_id}`;
        
        const storedProgress = localStorage.getItem(`skill_progress_${name}`);
        const progressVal = storedProgress ? parseInt(storedProgress, 10) : Math.round(enroll.progress || 0);
        
        return {
          id: String(enroll.course_id),
          name: name,
          roadmapsCount: 4,
          progress: progressVal,
          evalsPending: progressVal >= 100 ? 0 : 1,
          skills: [name, "System Design", "Best Practices"],
          subTopics: [
            { id: "st1", name: `Master core fundamentals of ${name}`, isDone: progressVal >= 25 },
            { id: "st2", name: `Apply ${name} to real-world projects`, isDone: progressVal >= 50 },
            { id: "st3", name: `Write automated tests for ${name} code`, isDone: progressVal >= 75 },
            { id: "st4", name: `Implement security guidelines and review`, isDone: progressVal >= 100 }
          ]
        };
      });

      const registeredStr = localStorage.getItem(`registered_courses_${email}`);
      const registeredList = registeredStr ? JSON.parse(registeredStr) : [];
      
      const customSessions: Session[] = registeredList.map((skill: string) => {
        const storedProgress = localStorage.getItem(`skill_progress_${skill}`);
        const progressVal = storedProgress ? parseInt(storedProgress, 10) : 0;
        return {
          id: skill,
          name: skill,
          roadmapsCount: 4,
          progress: progressVal,
          evalsPending: progressVal >= 100 ? 0 : 1,
          skills: [skill, "System Design", "Best Practices"],
          subTopics: [
            { id: "st1", name: `Master core fundamentals of ${skill}`, isDone: progressVal >= 25 },
            { id: "st2", name: `Apply ${skill} to real-world projects`, isDone: progressVal >= 50 },
            { id: "st3", name: `Write automated tests for ${skill} code`, isDone: progressVal >= 75 },
            { id: "st4", name: `Implement security guidelines and review`, isDone: progressVal >= 100 }
          ]
        };
      });

      const allSessions = [...enrollSessions];
      customSessions.forEach(cs => {
        if (!allSessions.some(as => as.name.toLowerCase() === cs.name.toLowerCase())) {
          allSessions.push(cs);
        }
      });

      setSessions(allSessions);
    }
  }, [email, enrollments, courses]);

  const handleSendMentorMessage = async () => {
    let finalQuery = mentorQuery;
    let messageText = mentorQuery;

    if (attachments.length > 0) {
      const fileNames = attachments.map(f => f.name).join(", ");
      const attachmentText = `\n\n[Attached: ${fileNames}]`;
      messageText = mentorQuery ? `${mentorQuery}${attachmentText}` : `[Attached: ${fileNames}]`;
      finalQuery = mentorQuery ? `${mentorQuery} (with files: ${fileNames})` : `Processing files: ${fileNames}`;
    }

    if (!messageText.trim() || mentorLoading) return;

    const userMsg = { sender: "user" as const, text: messageText };
    const updated = [...mentorMessages, userMsg];
    setMentorMessages(updated);
    setMentorQuery("");
    setAttachments([]);
    setMentorLoading(true);
    
    try {
      const history = updated.slice(0, -1).map(m => ({
        role: m.sender === "user" ? "user" : "assistant",
        content: m.text
      }));
      const res = await apiService.chatCopilot(finalQuery, history);
      setMentorMessages(prev => [...prev, { sender: "tush", text: res.response }]);
    } catch (err) {
      console.error(err);
      setMentorMessages(prev => [...prev, { sender: "tush", text: "I'm sorry, I encountered an error connecting to the career advisor server." }]);
    } finally {
      setMentorLoading(false);
    }
  };

  const handleSendWithSuggestion = async (suggestion: string) => {
    if (mentorLoading) return;
    const userMsg = { sender: "user" as const, text: suggestion };
    const updated = [...mentorMessages, userMsg];
    setMentorMessages(updated);
    setMentorLoading(true);
    
    try {
      const history = updated.slice(0, -1).map(m => ({
        role: m.sender === "user" ? "user" : "assistant",
        content: m.text
      }));
      const res = await apiService.chatCopilot(suggestion, history);
      setMentorMessages(prev => [...prev, { sender: "tush", text: res.response }]);
    } catch (err) {
      console.error(err);
      setMentorMessages(prev => [...prev, { sender: "tush", text: "I'm sorry, I encountered an error connecting to the career advisor server." }]);
    } finally {
      setMentorLoading(false);
    }
  };

  const handleCreateSession = async () => {
    if (!sessionName.trim() || !email) return;
    
    try {
      const registeredStr = localStorage.getItem(`registered_courses_${email}`);
      const registeredList = registeredStr ? JSON.parse(registeredStr) : [];
      if (!registeredList.includes(sessionName)) {
        const updatedList = [...registeredList, sessionName];
        localStorage.setItem(`registered_courses_${email}`, JSON.stringify(updatedList));
      }

      const currentSkills = profile?.skills || "";
      const newSkillList = currentSkills 
        ? `${currentSkills}, ${sessionName}` 
        : sessionName;
      
      await apiService.updateProfile({
        ...profile,
        skills: newSkillList
      });
      
      await loadData();
      
      // Reload sessions list
      const updatedSessions = [...sessions, {
        id: sessionName,
        name: sessionName,
        roadmapsCount: 4,
        progress: 0,
        evalsPending: 1,
        skills: [sessionName, "System Design", "Best Practices"],
        subTopics: [
          { id: "st1", name: `Master core fundamentals of ${sessionName}`, isDone: false },
          { id: "st2", name: `Apply ${sessionName} to real-world projects`, isDone: false },
          { id: "st3", name: `Write automated tests for ${sessionName} code`, isDone: false },
          { id: "st4", name: `Implement security guidelines and review`, isDone: false }
        ]
      }];
      setSessions(updatedSessions);

      setSessionName("");
      setShowCreateModal(false);
      setXp(prev => prev + 100); 
    } catch (err) {
      console.error(err);
    }
  };

  const handleStudyIncrement = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setSessions(prev => prev.map(s => {
      if (s.id === id) {
        const nextProgress = Math.min(s.progress + 10, 100);
        const skillKey = s.name.replace(" Development Roadmap", "");
        localStorage.setItem(`skill_progress_${skillKey}`, nextProgress.toString());

        const countToMark = Math.floor((nextProgress / 100) * s.subTopics.length);
        const updatedSubtopics = s.subTopics.map((st, idx) => ({
          ...st,
          isDone: idx < countToMark
        }));

        const updated = { ...s, progress: nextProgress, subTopics: updatedSubtopics };
        if (selectedSessionDetails && selectedSessionDetails.id === id) {
          setSelectedSessionDetails(updated);
        }
        setXp(prev => prev + 25); 
        return updated;
      }
      return s;
    }));
  };

  const handleToggleSubtopic = (sessionId: string, topicId: string) => {
    setSessions(prev => prev.map(s => {
      if (s.id === sessionId) {
        const updatedSubTopics = s.subTopics.map(st => 
          st.id === topicId ? { ...st, isDone: !st.isDone } : st
        );
        const completedCount = updatedSubTopics.filter(st => st.isDone).length;
        const nextProgress = Math.round((completedCount / updatedSubTopics.length) * 100);
        
        const skillKey = s.name.replace(" Development Roadmap", "");
        localStorage.setItem(`skill_progress_${skillKey}`, nextProgress.toString());

        const updated = { ...s, subTopics: updatedSubTopics, progress: nextProgress };
        if (selectedSessionDetails && selectedSessionDetails.id === sessionId) {
          setSelectedSessionDetails(updated);
        }
        return updated;
      }
      return s;
    }));
  };

  return (
    <div className="bg-transparent border-none p-0 shadow-none flex flex-col gap-3.5 w-full h-full min-h-0 overflow-hidden relative">
      
      {/* Top action row */}
      <div className="flex justify-end gap-2 shrink-0">
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-3 py-1.5 bg-indigo-50 dark:bg-indigo-950/20 hover:bg-indigo-100 dark:hover:bg-indigo-900/30 dark:bg-card text-indigo-600 dark:text-indigo-400 dark:text-blue-500 border border-indigo-200 dark:border-border hover:dark:bg-muted hover:dark:border-primary rounded-xl text-10 font-bold cursor-pointer transition-all flex items-center gap-1"
        >
          <span>+ New Roadmap</span>
        </button>
        <button
          onClick={() => setShowSidebar(true)}
          className="px-3 py-1.5 bg-muted hover:bg-slate-200/50 dark:bg-card dark:hover:bg-muted text-muted-foreground dark:text-muted-foreground border border-border dark:border-border rounded-xl text-10 font-bold cursor-pointer transition-all flex items-center gap-1"
          title="Open Roadmaps"
        >
          <List size={11} />
          <span>Active Roadmaps ({sessions.length})</span>
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden justify-center items-stretch relative min-h-0 w-full">
        {/* Chat Pane */}
        <div className="w-full max-w-full lg:max-w-70-pct md:max-w-80-pct flex flex-col h-full overflow-hidden relative min-h-0">
          
          {/* Scrollable message thread */}
          <div className="flex-1 overflow-y-auto mb-4 p-4 bg-muted dark:bg-black/30 border border-border rounded-2xl flex flex-col gap-4 scrollbar-thin">
            {mentorMessages.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center px-4 py-4 max-w-md mx-auto w-full text-center my-auto animate-fade-in gap-2.5">
                
                <div>
                  <h2 className="text-base font-black text-gray-900 dark:text-foreground leading-tight">
                    Hi {firstName} 👋
                  </h2>
                  <p className="text-xs text-muted-foreground dark:text-muted-foreground font-bold mt-1">
                    I'm <span className="text-blue-500 font-extrabold">Tush AI</span>, your learning mentor.
                  </p>
                </div>

                {/* Suggestions chips */}
                <div className="flex flex-wrap gap-2 justify-center w-full mt-1.5">
                  {[
                    { label: "Create Roadmap", query: "Create Learning Roadmap" },
                    { label: "Recommend Courses", query: "Recommend Courses" },
                    { label: "Review Skills", query: "Review My Skills" },
                    { label: "Interview Prep", query: "Prepare for Interviews" }
                  ].map((chip) => (
                    <button
                      key={chip.label}
                      onClick={() => handleSendWithSuggestion(chip.query)}
                      className="px-3 py-1.5 text-10 font-bold text-foreground dark:text-foreground bg-card border border-border hover:border-blue-500/50 dark:hover:border-blue-500 hover:bg-slate-50 dark:hover:bg-muted rounded-full hover:shadow-sm transition-all duration-200 cursor-pointer"
                    >
                      {chip.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              mentorMessages.map((msg, idx) => (
                <div 
                  key={idx} 
                  className={`flex flex-col gap-1 max-w-85-pct ${
                    msg.sender === "user" ? "self-end items-end" : "self-start items-start"
                  }`}
                >
                  <span className={`text-9 font-black uppercase tracking-wider ${
                    msg.sender === "user" ? "text-muted-foreground dark:text-muted-foreground" : "text-blue-500"
                  }`}>
                    {msg.sender === "user" ? "You" : "Tush AI"}
                  </span>
                  <div 
                    className={`rounded-2xl p-3.5 text-xs leading-relaxed border ${
                      msg.sender === "user" 
                        ? "bg-blue-50 dark:bg-blue-950/30 text-slate-900 dark:text-foreground border-blue-100 dark:border-blue-900/30 rounded-tr-sm shadow-sm" 
                        : "bg-card border-border text-foreground dark:text-foreground rounded-tl-sm shadow-sm"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.text}</p>
                  </div>
                </div>
              ))
            )}
            {mentorLoading && (
              <div className="bg-card border border-border text-foreground dark:text-foreground self-start rounded-2xl rounded-tl-sm p-3.5 flex items-center gap-2 max-w-xs shadow-sm">
                <div className="flex gap-1 shrink-0">
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce [animation-delay:-0.3s]" />
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce [animation-delay:-0.15s]" />
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" />
                </div>
                <span className="text-10 font-bold text-muted-foreground dark:text-muted-foreground">Tush AI is typing...</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Redesigned pill-shaped floating input box */}
          <div className="w-full shrink-0">
            <div className="flex flex-col flex flex-col bg-card border border-border rounded-32 p-2 pl-4 pr-3 shadow-custom-glass hover:border-border-hover dark:hover:border-border-hover focus-within:border-primary/50 dark:focus-within:border-primary focus-within:shadow-[0_8px_30px_rgba(59,130,246,0.08)] transition-all duration-300 w-full">
              
              {/* Attachment Preview Chips */}
              {attachments.length > 0 && (
                <div className="flex flex-wrap gap-2 px-1 pt-2 pb-1.5 border-b border-gray-100 dark:border-border mb-2 w-full">
                  {attachments.map((file, idx) => {
                    const isImage = file.type.startsWith("image/");
                    return (
                      <div 
                        key={idx} 
                        className="flex items-center gap-1.5 pl-2 pr-1.5 py-1 rounded-lg bg-gray-50 dark:bg-background border border-border dark:border-border text-xs text-gray-700 dark:text-foreground"
                      >
                        {isImage ? (
                          <span className="w-4.5 h-4.5 rounded overflow-hidden shrink-0 border border-gray-300 dark:border-zinc-600">
                            <img 
                              src={URL.createObjectURL(file)} 
                              alt={file.name} 
                              className="w-full h-full object-cover"
                            />
                          </span>
                        ) : (
                          <FileText size={14} className="text-blue-500" />
                        )}
                        <span className="max-w-120 truncate font-medium">{file.name}</span>
                        <button 
                          onClick={() => removeAttachment(idx)}
                          className="w-4 h-4 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-655 dark:hover:text-zinc-200 hover:bg-gray-200 dark:hover:bg-zinc-700 transition-colors cursor-pointer"
                          title="Remove file"
                        >
                          &times;
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Main Pill Controls row */}
              <div className="flex items-end gap-2 w-full min-h-10">
                {/* Left Side: Plus icon */}
                <button 
                  onClick={handlePlusClick}
                  className="flex items-center justify-center w-9 h-9 rounded-full text-gray-400 hover:text-gray-655 dark:text-muted-foreground dark:hover:text-foreground hover:bg-gray-100 dark:hover:bg-background transition-colors shrink-0 mb-0.5" 
                  title="Add attachment"
                >
                  <Plus size={20} />
                </button>
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileChange} 
                  multiple 
                  accept="image/*,.pdf,.doc,.docx,.txt"
                  className="hidden" 
                />

                {/* Center: Textarea that expands naturally */}
                <div className="flex-1 min-w-0 py-1.5 self-center">
                  <textarea
                    ref={textareaRef}
                    rows={1}
                    value={mentorQuery}
                    onChange={(e) => setMentorQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMentorMessage();
                      }
                    }}
                    placeholder="Ask Tush AI anything..."
                    className="chat-input-textarea w-full bg-transparent resize-none border-none outline-none focus:ring-0 text-sm text-foreground placeholder-muted-foreground py-1 max-h-200 h-6"
                  />
                </div>

                {/* Right Side: Microphone and Send buttons */}
                <div className="flex items-center gap-1.5 shrink-0 self-center">
                  {/* Microphone Icon */}
                  <button 
                    onClick={startListening}
                    className={`flex items-center justify-center w-9 h-9 rounded-full transition-all duration-300 ${
                      isListening 
                        ? "bg-red-500 text-white animate-pulse shadow-[0_0_12px_rgba(239,68,68,0.5)]" 
                        : "text-gray-400 hover:text-gray-655 dark:text-muted-foreground dark:hover:text-foreground hover:bg-gray-100 dark:hover:bg-background"
                    }`} 
                    title={isListening ? "Stop listening" : "Voice input"}
                  >
                    <Mic size={18} />
                  </button>

                  {/* Send button (always visible) */}
                  <button
                    onClick={handleSendMentorMessage}
                    disabled={!mentorQuery.trim() && attachments.length === 0}
                    className={`flex items-center justify-center w-9 h-9 rounded-full transition-all duration-200 shrink-0 ${
                      mentorQuery.trim() || attachments.length > 0
                        ? "bg-blue-500 hover:bg-blue-600 text-white shadow-sm hover:scale-105 active:scale-95 cursor-pointer"
                        : "bg-slate-100 dark:bg-background text-slate-400 dark:text-muted-foreground cursor-not-allowed"
                    }`}
                    title="Send message"
                  >
                    <ArrowUp size={16} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Backdrop for mobile/desktop drawer click-away */}
        {showSidebar && (
          <div 
            className="absolute inset-0 bg-slate-950/40 backdrop-blur-xs z-30 transition-opacity duration-300 rounded-2xl"
            onClick={() => setShowSidebar(false)}
          />
        )}

        {/* Collapsible Slide-over Drawer for Active Roadmaps */}
        <div className={`absolute top-0 right-0 h-full w-80 bg-white dark:bg-background border border-border dark:border-border shadow-2xl z-40 flex flex-col transition-transform duration-300 rounded-2xl ${
          showSidebar ? "translate-x-0" : "translate-x-full"
        }`}>
          {/* Drawer Header */}
          <div className="flex justify-between items-center p-4 border-b border-slate-100 dark:border-border shrink-0">
            <div>
              <h4 className="text-xs font-black text-foreground dark:text-foreground uppercase tracking-wider">Active Roadmaps</h4>
              <p className="text-10 text-muted-foreground dark:text-muted-foreground mt-0.5 font-medium">Explore custom study check-lists</p>
            </div>
            <button 
              onClick={() => setShowSidebar(false)}
              className="p-1.5 hover:bg-slate-100 dark:hover:bg-muted rounded-xl text-muted-foreground dark:text-muted-foreground transition-colors cursor-pointer"
            >
              <X size={16} />
            </button>
          </div>

          {/* Drawer Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-2.5 scrollbar-thin">
            {sessions.map((s) => (
              <div 
                key={s.id}
                onClick={() => setSelectedSessionDetails(s)}
                className="p-2.5 bg-muted dark:bg-card border border-border dark:border-border rounded-2xl hover:border-indigo-500/30 dark:hover:border-blue-500 transition-all cursor-pointer flex flex-col gap-1.5 relative group"
              >
                <div className="flex justify-between items-start">
                  <h4 className="text-11 font-bold text-foreground dark:text-foreground leading-snug truncate pr-2 flex-1">{s.name}</h4>
                  <span className="text-10 font-black text-emerald-500 shrink-0">{s.progress}%</span>
                </div>
                
                <div className="flex justify-between items-center text-8 font-bold text-muted-foreground dark:text-muted-foreground uppercase tracking-wider pt-1.5 border-t border-border/10 dark:border-border">
                  <span>Simulated study path</span>
                  <span className="text-indigo-600 dark:text-indigo-400 dark:text-blue-500 group-hover:translate-x-0.5 transition-transform flex items-center gap-0.5">Checklist →</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Create Session Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/65 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-background border border-slate-250 dark:border-border rounded-3xl p-6 w-full max-w-md shadow-2xl flex flex-col gap-4">
            <div className="flex justify-between items-center border-b border-slate-100 dark:border-border pb-3">
              <h3 className="text-sm font-bold text-foreground dark:text-foreground flex items-center gap-1.5">
                <GraduationCap size={16} className="text-blue-500" />
                <span>Create New Study Session</span>
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-655 dark:text-muted-foreground dark:hover:text-foreground cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            <div className="space-y-4 py-2">
              <div className="flex flex-col gap-1.5">
                <label className="text-10 font-bold uppercase tracking-wider text-slate-400 dark:text-muted-foreground">Roadmap Subject Name</label>
                <input
                  type="text"
                  placeholder="e.g. AI Prompt Engineering"
                  value={sessionName}
                  onChange={(e) => setSessionName(e.target.value)}
                  className="bg-slate-50 dark:bg-black border border-border dark:border-border rounded-xl p-2.5 text-xs text-foreground dark:text-foreground focus:outline-none focus:border-indigo-500 dark:focus:border-primary"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-10 font-bold uppercase tracking-wider text-slate-400 dark:text-muted-foreground">Target Stack Category</label>
                <select
                  value={selectedSkill}
                  onChange={(e) => setSelectedSkill(e.target.value)}
                  className="bg-slate-50 dark:bg-black border border-border dark:border-border rounded-xl p-2.5 text-xs text-foreground dark:text-foreground focus:outline-none focus:border-indigo-500 dark:focus:border-primary cursor-pointer font-medium"
                >
                  <option value="Python Backend, FastAPI, SQL">Python Backend (FastAPI/SQL)</option>
                  <option value="NextJS Frontend, React, TypeScript">NextJS Frontend (React/TS)</option>
                  <option value="AI Agents, LLMs, LangChain">AI Agent Specialist (LLMs/RAG)</option>
                  <option value="System Design, AWS, Docker">System Design & Cloud Systems</option>
                </select>
              </div>
            </div>

            <button
              onClick={handleCreateSession}
              disabled={!sessionName.trim()}
              className="w-full py-2.5 bg-blue-500 hover:bg-blue-600 dark:disabled:bg-muted dark:disabled:text-muted-foreground text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-md"
            >
              <span>Create Session (+100 XP)</span>
              <ArrowRight size={13} />
            </button>
          </div>
        </div>
      )}

      {/* Curriculum Checklist details Modal */}
      {selectedSessionDetails && (
        <div className="fixed inset-0 z-50 bg-black/65 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-background border border-slate-250 dark:border-border rounded-3xl p-6 w-full max-w-lg shadow-2xl flex flex-col gap-4 max-h-[85vh] overflow-y-auto">
            
            <div className="flex justify-between items-start border-b border-slate-100 dark:border-border pb-3">
              <div>
                <h3 className="text-sm font-bold text-foreground dark:text-foreground leading-tight">{selectedSessionDetails.name}</h3>
                <span className="text-10 text-slate-400 dark:text-muted-foreground mt-1 block">Curriculum details and modules checklist</span>
              </div>
              <button
                onClick={() => setSelectedSessionDetails(null)}
                className="text-slate-400 hover:text-slate-655 dark:text-muted-foreground dark:hover:text-foreground p-1 hover:bg-slate-50 dark:hover:bg-slate-950 rounded-lg cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            {/* Total progress statistics */}
            <div className="bg-slate-50 dark:bg-black border border-border dark:border-border p-4 rounded-2xl flex justify-between items-center">
              <div>
                <span className="text-9 uppercase font-bold text-slate-400 dark:text-muted-foreground">Current Progress</span>
                <span className="text-base font-extrabold text-emerald-500 block mt-0.5">{selectedSessionDetails.progress}% Complete</span>
              </div>

              <button
                onClick={(e) => handleStudyIncrement(selectedSessionDetails.id, e)}
                className="flex items-center gap-1.5 px-4.5 py-2.5 rounded-xl bg-blue-500 hover:bg-blue-600 text-xs font-bold text-white transition-all cursor-pointer shadow-sm"
              >
                <Play size={12} fill="white" />
                <span>Simulate Study (+10%)</span>
              </button>
            </div>

            {/* Subtopics checklist */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-foreground dark:text-foreground flex items-center gap-1.5">
                <CheckSquare size={14} className="text-blue-500" />
                <span>Roadmap Modules Checklist</span>
              </h4>

              <div className="divide-y divide-slate-100 dark:divide-[#374151] border border-border dark:border-border rounded-2xl bg-white dark:bg-card overflow-hidden">
                {selectedSessionDetails.subTopics.map((st) => (
                  <label
                    key={st.id}
                    className="flex items-center justify-between p-3.5 hover:bg-slate-50 dark:hover:bg-background/50 transition-colors cursor-pointer text-xs font-semibold text-foreground dark:text-foreground"
                  >
                    <div className="flex items-center gap-2.5">
                      <input
                        type="checkbox"
                        checked={st.isDone}
                        onChange={() => handleToggleSubtopic(selectedSessionDetails.id, st.id)}
                        className="rounded text-blue-500 focus:ring-blue-500 border-border dark:border-border bg-white dark:bg-black"
                      />
                      <span className={st.isDone ? "line-through text-slate-400" : ""}>{st.name}</span>
                    </div>
                    {st.isDone && (
                      <span className="text-9 font-bold text-emerald-500 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded">
                        Completed
                      </span>
                    )}
                  </label>
                ))}
              </div>
            </div>

            <div className="p-3 bg-indigo-50/10 border border-indigo-200/50 dark:bg-card/50 dark:border-border rounded-2xl text-10 text-slate-500 dark:text-muted-foreground flex items-start gap-2 mt-1 font-semibold leading-normal">
              <Info size={14} className="text-blue-500 shrink-0 mt-0.5" />
              <p>
                Checking off subtopics dynamically updates your roadmap progress statistics and increases earned XP! Complete all topics to earn your platform certificate.
              </p>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
