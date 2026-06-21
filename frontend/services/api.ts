import { useAuthStore } from "@/store/authStore";

// Simple in-memory cache for GET requests to achieve instant page loads (<10ms)
const getCache = new Map<string, { response: Response; timestamp: number }>();
const CACHE_TTL = 30000; // 30 seconds TTL

const customFetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
  const url = typeof input === "string" ? input : (input as URL).toString();
  const method = init?.method || "GET";

  // Only cache GET requests
  if (method.toUpperCase() === "GET") {
    const cached = getCache.get(url);
    const now = Date.now();
    if (cached && now - cached.timestamp < CACHE_TTL) {
      return cached.response.clone();
    }
  } else {
    // For non-GET requests (POST, PUT, DELETE, etc.), clear cache to prevent stale data
    getCache.clear();
  }

  const res = await fetch(input, init);
  if (res.status === 401) {
    const urlString = typeof input === "string" ? input : input.toString();
    const isAuthRoute = urlString.includes("/auth/");
    
    if (!isAuthRoute && typeof window !== "undefined") {
      getCache.clear(); // Clear cache on logout/auth expiry
      useAuthStore.getState().logout();
      if (window.location.pathname !== "/") {
        window.location.href = "/";
      }
    }
  }

  // Cache successful GET responses
  if (method.toUpperCase() === "GET" && res.ok) {
    getCache.set(url, {
      response: res.clone(),
      timestamp: Date.now(),
    });
  }

  return res;
};

export const getBaseUrl = () => {
  // Use deployed backend URL if available
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  return "https://vidyamargai-production.up.railway.app/api/v1";
};

export const getBackendBaseUrl = () => {
  const baseUrl = getBaseUrl();
  return baseUrl.replace(/\/api\/v1\/?$/, "");
};

export const getWsUrl = () => {
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL;
  }
  const backendBase = getBackendBaseUrl();
  const wsProto = backendBase.startsWith("https://") ? "wss://" : "ws://";
  const domain = backendBase.replace(/^https?:\/\//, "");
  return `${wsProto}${domain}/ws`;
};

export const getAgentWsUrl = (runId: number | string) => {
  const backendBase = getBackendBaseUrl();
  const wsProto = backendBase.startsWith("https://") ? "wss://" : "ws://";
  const domain = backendBase.replace(/^https?:\/\//, "");
  return `${wsProto}${domain}/api/v1/ws/agent/${runId}`;
};
const getHeaders = () => {
  const headers: Record<string, string> = {};
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return headers;
};

export const apiService = {
  // Auth
  async signup(data: any) {
    const res = await customFetch(`${getBaseUrl()}/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Signup failed");
    return res.json();
  },

  async login(formData: URLSearchParams) {
    const res = await customFetch(`${getBaseUrl()}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString(),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Login failed");
    return res.json();
  },

  async getMe() {
    const res = await customFetch(`${getBaseUrl()}/auth/me`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch session");
    return res.json();
  },

  async forgotPassword(email: string) {
    const res = await customFetch(`${getBaseUrl()}/auth/forgot-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Failed to request reset code");
    return res.json();
  },

  async resetPassword(data: { email: string; new_password: string; code: string }) {
    const res = await customFetch(`${getBaseUrl()}/auth/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Failed to reset password");
    return res.json();
  },


  // Jobs
  async getJobs(search?: string) {
    const url = search ? `${getBaseUrl()}/jobs?search=${encodeURIComponent(search)}` : `${getBaseUrl()}/jobs`;
    const res = await customFetch(url, { headers: getHeaders() });
    if (!res.ok) throw new Error("Failed to fetch jobs");
    return res.json();
  },

  async createJob(data: any) {
    const res = await customFetch(`${getBaseUrl()}/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to create job");
    return res.json();
  },

  async deleteJob(id: number) {
    const res = await customFetch(`${getBaseUrl()}/jobs/${id}`, {
      method: "DELETE",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to delete job");
    return res.json();
  },

  async getSavedJobs() {
    const res = await customFetch(`${getBaseUrl()}/candidate/jobs/saved`, { headers: getHeaders() });
    if (!res.ok) throw new Error("Failed to fetch saved jobs");
    return res.json();
  },

  async saveJob(jobId: number | string) {
    const res = await customFetch(`${getBaseUrl()}/candidate/jobs/${jobId}/save`, {
      method: "POST",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to save job");
    return res.json();
  },

  async unsaveJob(jobId: number | string) {
    const res = await customFetch(`${getBaseUrl()}/candidate/jobs/${jobId}/save`, {
      method: "DELETE",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to unsave job");
    return res.json();
  },

  async refreshJobs() {
    const res = await customFetch(`${getBaseUrl()}/candidate/jobs/refresh`, {
      method: "POST",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to refresh jobs");
    return res.json();
  },

  async getSearchHistory() {
    const res = await customFetch(`${getBaseUrl()}/candidate/jobs/search-history`, { headers: getHeaders() });
    if (!res.ok) throw new Error("Failed to fetch search history");
    return res.json();
  },

  async getCandidateJobsDashboard() {
    const res = await customFetch(`${getBaseUrl()}/candidate/jobs/dashboard`, { headers: getHeaders() });
    if (!res.ok) throw new Error("Failed to fetch candidate jobs dashboard");
    return res.json();
  },

  // Profile
  async getProfile() {
    const res = await customFetch(`${getBaseUrl()}/candidates/profile`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to get profile");
    return res.json();
  },

  async updateProfile(data: any) {
    const res = await customFetch(`${getBaseUrl()}/candidates/profile`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to update profile");
    return res.json();
  },

  async uploadResume(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await customFetch(`${getBaseUrl()}/candidates/resume`, {
      method: "POST",
      headers: getHeaders(),
      body: formData,
    });
    if (!res.ok) throw new Error("Failed to upload resume");
    return res.json();
  },

  async getResumeUrl() {
    const res = await customFetch(`${getBaseUrl()}/candidates/resume`, {
      headers: getHeaders(),
    });
    if (!res.ok) return null;
    return res.json();
  },

  async getResumes() {
    const res = await customFetch(`${getBaseUrl()}/candidates/resumes`, {
      headers: getHeaders(),
    });
    if (!res.ok) return [];
    return res.json();
  },

  async deleteResumeVersion(id: number) {
    const res = await customFetch(`${getBaseUrl()}/candidates/resume/${id}`, {
      method: "DELETE",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to delete resume");
    return res.json();
  },

  async analyzeResume() {
    const res = await customFetch(`${getBaseUrl()}/candidates/resume/analyze`, {
      method: "POST",
      headers: getHeaders(),
    });
    if (!res.ok) return null;
    return res.json();
  },

  async analyzeResumeATS(jobId?: number, jobDescription?: string) {
    const body: any = {};
    if (jobId) body.job_id = jobId;
    if (jobDescription) body.job_description = jobDescription;
    const res = await customFetch(`${getBaseUrl()}/candidates/resume/ats`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(body),
    });
    if (!res.ok) return null;
    return res.json();
  },

  // Applications
  async applyJob(jobId: number) {
    const res = await customFetch(`${getBaseUrl()}/applications?job_id=${jobId}`, {
      method: "POST",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Apply failed");
    return res.json();
  },

  async getApplications() {
    const res = await customFetch(`${getBaseUrl()}/applications`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to get applications");
    return res.json();
  },

  // Assessments
  async getAssessment(appId: number) {
    const res = await customFetch(`${getBaseUrl()}/assessments/attempt/${appId}`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch assessment details");
    return res.json();
  },

  async submitAssessment(appId: number, answers: any) {
    const res = await customFetch(`${getBaseUrl()}/assessments/attempt/${appId}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ answers: JSON.stringify(answers) }),
    });
    if (!res.ok) throw new Error("Failed to submit assessment");
    return res.json();
  },

  async logProctorEvent(appId: number, eventType: string, details: string) {
    const res = await customFetch(`${getBaseUrl()}/assessments/proctor/log/${appId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ event_type: eventType, details }),
    });
    return res.ok;
  },

  // Interviews
  async getInterview(appId: number) {
    const res = await customFetch(`${getBaseUrl()}/interviews/${appId}`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch interview session");
    return res.json();
  },

  async answerInterviewQuestion(interviewId: number, answer: string) {
    const res = await customFetch(`${getBaseUrl()}/interviews/${interviewId}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ answer }),
    });
    if (!res.ok) throw new Error("Failed to send reply");
    return res.json();
  },

  async getInterviewAnalysis(interviewId: number) {
    const res = await customFetch(`${getBaseUrl()}/interviews/${interviewId}/analysis`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch interview analysis");
    return res.json();
  },

  // Offers
  async getOffer(appId: number) {
    const res = await customFetch(`${getBaseUrl()}/offers/${appId}`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch offer");
    return res.json();
  },

  async respondOffer(offerId: number, accept: boolean) {
    const res = await customFetch(`${getBaseUrl()}/offers/${offerId}/respond?accept=${accept}`, {
      method: "POST",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to record text reply");
    return res.json();
  },

  // Admin Dashboard & Rankings
  async getAdminMetrics() {
    const res = await customFetch(`${getBaseUrl()}/admin/dashboard`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch metrics");
    return res.json();
  },

  async getRankings() {
    const res = await customFetch(`${getBaseUrl()}/admin/rankings`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch rankings");
    return res.json();
  },

  // Notifications
  async getNotifications() {
    const res = await customFetch(`${getBaseUrl()}/notifications`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch notifications");
    return res.json();
  },

  async readNotification(id: number) {
    const res = await customFetch(`${getBaseUrl()}/notifications/${id}/read`, {
      method: "PUT",
      headers: getHeaders(),
    });
    return res.ok;
  },

  // Emails
  async getCandidateEmails() {
    const res = await customFetch(`${getBaseUrl()}/candidates/emails`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch emails");
    return res.json();
  },

  async readCandidateEmail(id: number) {
    const res = await customFetch(`${getBaseUrl()}/candidates/emails/${id}/read`, {
      method: "PUT",
      headers: getHeaders(),
    });
    return res.ok;
  },

  async chatCopilot(message: string, history: any[]) {
    const res = await customFetch(`${getBaseUrl()}/chat/copilot`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ message, history }),
    });
    if (!res.ok) throw new Error("Failed to get response from Baelyx");
    return res.json();
  },

  async getCourses() {
    const res = await customFetch(`${getBaseUrl()}/courses`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch courses");
    return res.json();
  },

  async generateCourse(role: string, level: string, duration: string, goal: string, description?: string) {
    const res = await customFetch(`${getBaseUrl()}/courses/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ topic: role, role, level, duration, goal, description }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to generate course" }));
      let detailMsg = "Failed to generate course";
      if (err.detail) {
        if (typeof err.detail === "string") {
          detailMsg = err.detail;
        } else if (Array.isArray(err.detail)) {
          detailMsg = err.detail.map((e: any) => e.msg || JSON.stringify(e)).join(", ");
        } else {
          detailMsg = typeof err.detail === "object" ? JSON.stringify(err.detail) : String(err.detail);
        }
      }
      throw new Error(detailMsg);
    }
    return res.json();
  },

  async createCourse(title: string, instructor: string, category: string, level: string, description: string, duration: string) {
    const res = await customFetch(`${getBaseUrl()}/courses/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ title, instructor, category, level, description, duration }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to create course" }));
      throw new Error(err.detail || "Failed to create course");
    }
    return res.json();
  },

  async getCourseCurriculum(courseId: string | number) {
    const res = await customFetch(`${getBaseUrl()}/courses/${courseId}/curriculum`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch course curriculum");
    return res.json();
  },

  async enrollCourse(courseId: string | number) {
    const res = await customFetch(`${getBaseUrl()}/courses/${courseId}/enroll`, {
      method: "POST",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to enroll in course");
    return res.json();
  },

  async completeLesson(lessonId: string | number) {
    const res = await customFetch(`${getBaseUrl()}/lessons/${lessonId}/complete`, {
      method: "POST",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to mark lesson complete");
    return res.json();
  },

  async completePdf(pdfId: string | number) {
    const res = await customFetch(`${getBaseUrl()}/pdfs/${pdfId}/complete`, {
      method: "POST",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to mark PDF complete");
    return res.json();
  },

  async getEnrollments() {
    const res = await customFetch(`${getBaseUrl()}/enrollments`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch enrollments");
    return res.json();
  },

  async getCertificates() {
    const res = await customFetch(`${getBaseUrl()}/certificates`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch certificates");
    return res.json();
  },

  async submitQuiz(quizId: string | number, answers: any) {
    const res = await customFetch(`${getBaseUrl()}/quiz/${quizId}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ answers: JSON.stringify(answers) }),
    });
    if (!res.ok) throw new Error("Failed to submit quiz");
    return res.json();
  },

  async submitWrittenAssessment(writtenId: string | number, answers: any) {
    const res = await customFetch(`${getBaseUrl()}/written/${writtenId}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ answers: JSON.stringify(answers) }),
    });
    if (!res.ok) throw new Error("Failed to submit written assessment");
    return res.json();
  },

  async submitModuleInterview(interviewId: string | number, answers: any) {
    const res = await customFetch(`${getBaseUrl()}/interview/${interviewId}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ answers: JSON.stringify(answers) }),
    });
    if (!res.ok) throw new Error("Failed to submit interview");
    return res.json();
  },

  async getCareerReadiness() {
    const res = await customFetch(`${getBaseUrl()}/career-readiness`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch career readiness");
    return res.json();
  },

  async getMessages() {
    const res = await customFetch(`${getBaseUrl()}/messages`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch messages");
    return res.json();
  },

  async sendMessage(chatId: string, text: string) {
    const res = await customFetch(`${getBaseUrl()}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ chat_id: chatId, text }),
    });
    if (!res.ok) throw new Error("Failed to send message");
    return res.json();
  },

  async saveHackathonAssignment(candidateId: number, data: any) {
    const res = await customFetch(`${getBaseUrl()}/candidates/${candidateId}/hackathon`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to save hackathon assignment");
    return res.json();
  },

  async sendAdminMessage(candidateId: number, chatId: string, sender: string, senderName: string, text: string) {
    const res = await customFetch(`${getBaseUrl()}/admin/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ candidate_id: candidateId, chat_id: chatId, sender, sender_name: senderName, text }),
    });
    if (!res.ok) throw new Error("Failed to send admin message");
    return res.json();
  },

  async getAdminCandidateMessages(candidateId: number) {
    const res = await customFetch(`${getBaseUrl()}/admin/candidates/${candidateId}/messages`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch candidate messages");
    return res.json();
  },

  async getCandidateFiles(candidateId: number) {
    const res = await customFetch(`${getBaseUrl()}/admin/candidates/${candidateId}/files`, {
      headers: getHeaders(),
    });
    if (!res.ok) return [];
    return res.json();
  },


  async startAgentRun(maxJobAgeDays?: number) {
    const query = maxJobAgeDays ? `?max_job_age_days=${maxJobAgeDays}` : "";
    const res = await customFetch(`${getBaseUrl()}/candidate/agent/run${query}`, {
      method: "POST",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to start agent run");
    return res.json();
  },

  async getLatestAgentRun() {
    const res = await customFetch(`${getBaseUrl()}/candidate/agent/run/latest`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch latest agent run");
    return res.json();
  },

  async getAgentRunResult() {
    const res = await customFetch(`${getBaseUrl()}/candidate/agent/result`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch agent run result");
    return res.json();
  },

  async getTelegramSources() {
    const res = await customFetch(`${getBaseUrl()}/admin/telegram-sources`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch Telegram sources");
    return res.json();
  },

  async createTelegramSource(channelName: string, active: boolean = true) {
    const res = await customFetch(`${getBaseUrl()}/admin/telegram-sources`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ channel_name: channelName, active }),
    });
    if (!res.ok) throw new Error("Failed to create Telegram source");
    return res.json();
  },

  async updateTelegramSource(id: number, channelName: string, active: boolean) {
    const res = await customFetch(`${getBaseUrl()}/admin/telegram-sources/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ channel_name: channelName, active }),
    });
    if (!res.ok) throw new Error("Failed to update Telegram source");
    return res.json();
  },

  async deleteTelegramSource(id: number) {
    const res = await customFetch(`${getBaseUrl()}/admin/telegram-sources/${id}`, {
      method: "DELETE",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to delete Telegram source");
    return res.json();
  },

  async getPreferences() {
    const res = await customFetch(`${getBaseUrl()}/users/me/preferences`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch preferences");
    return res.json();
  },

  async updatePreferences(theme: string) {
    const res = await customFetch(`${getBaseUrl()}/users/me/preferences`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ theme }),
    });
    if (!res.ok) throw new Error("Failed to update preferences");
    return res.json();
  },

  async saveResumeLearning(data: { courseId: string | number, lessonId: string, playbackPosition: number, watchedSegments: number[], completion: number }) {
    const res = await customFetch(`${getBaseUrl()}/resume-learning`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to save resume learning");
    return res.json();
  },

  async getResumeLearning(courseId: string | number) {
    const res = await customFetch(`${getBaseUrl()}/resume-learning/${courseId}`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to get resume learning");
    return res.json();
  },

  async getContinueLearning() {
    const res = await customFetch(`${getBaseUrl()}/continue-learning`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to get continue learning");
    return res.json();
  },

  async saveVideoAnalytics(data: { lessonId: string, loadTime: number, bufferCount: number, bufferDuration: number, playbackFailures: number, device?: string, browser?: string }) {
    const res = await customFetch(`${getBaseUrl()}/video-analytics`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to save video analytics");
    return res.json();
  },

  async saveLearningEvent(data: { eventType: string, lessonId: string, metadata?: any }) {
    const res = await customFetch(`${getBaseUrl()}/learning-events`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to save learning event");
    return res.json();
  },

  async getUserStats() {
    const res = await customFetch(`${getBaseUrl()}/user-stats`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to get user stats");
    return res.json();
  },

  // AI Mentor Endpoints
  async getAIMentorProfile() {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/profile`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to get AI mentor profile");
    return res.json();
  },

  async getAIMentorRiskAnalysis() {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/risk-analysis`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to get AI mentor risk analysis");
    return res.json();
  },

  async getAIMentorAnalytics() {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/analytics`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to get AI mentor analytics");
    return res.json();
  },

  async getAIMentorSessions() {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/sessions`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to get AI mentor sessions");
    return res.json();
  },

  async createAIMentorSession(title: string) {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ title }),
    });
    if (!res.ok) throw new Error("Failed to create AI mentor session");
    return res.json();
  },

  async renameAIMentorSession(sessionId: string, title: string) {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/sessions/${sessionId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ title }),
    });
    if (!res.ok) throw new Error("Failed to rename AI mentor session");
    return res.json();
  },

  async deleteAIMentorSession(sessionId: string) {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/sessions/${sessionId}`, {
      method: "DELETE",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to delete AI mentor session");
    return res.json();
  },

  async getAIMentorMessages(sessionId: string) {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/sessions/${sessionId}/messages`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to get AI mentor messages");
    return res.json();
  },

  async sendAIMentorChat(sessionId: string, message: string, mode: string = "tutor") {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/sessions/${sessionId}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ message, mode }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Failed to send chat message");
    return res.json();
  },

  async generateAIMentorStudyPlan(duration: string, title?: string) {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/study-plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ duration, title }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Failed to generate study plan");
    return res.json();
  },

  async getAIMentorStudyPlans() {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/study-plans`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to get AI mentor study plans");
    return res.json();
  },

  async getAIMentorArtifacts() {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/artifacts`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to get AI mentor artifacts");
    return res.json();
  },

  async createAIMentorArtifact(data: { artifact_type: string; title: string; content: string; metadata_json?: any }) {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/artifacts`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to create AI mentor artifact");
    return res.json();
  },

  async getAIMentorConfig() {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/config`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to get AI mentor configuration");
    return res.json();
  },

  async searchAIMentor(q: string, type: string = "all", page: number = 1, pageSize: number = 50) {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/search?q=${encodeURIComponent(q)}&type=${encodeURIComponent(type)}&page=${page}&page_size=${pageSize}`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to search AI mentor records");
    return res.json();
  },

  async updateCareerGoal(career_goal: string, target_role: string = "Frontend Developer", target_level: string = "Mid-Level") {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/goal`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ career_goal, target_role, target_level }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Failed to update career goal");
    return res.json();
  },

  async runSupervisorAgent() {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/agent/run`, {
      method: "POST",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to trigger supervisor agent");
    return res.json();
  },

  async getAgentActivityFeed() {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/agent/activity-feed`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to get agent activity feed");
    return res.json();
  },

  async mcpChat(message: string, mode: 'resume' | 'skill-lab' | 'job-agent' | 'general', history: any[], contextHint?: string, sessionId?: string) {
    const res = await customFetch(`${getBaseUrl()}/mcp/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ message, mode, history, context_hint: contextHint, session_id: sessionId }),
    });
    if (!res.ok) throw new Error("Failed to send MCP chat message");
    return res.json();
  },

  async mcpChatStream(message: string, mode: 'resume' | 'skill-lab' | 'job-agent' | 'general', history: any[], contextHint?: string, sessionId?: string): Promise<Response> {
    const res = await customFetch(`${getBaseUrl()}/mcp/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ message, mode, history, context_hint: contextHint, session_id: sessionId }),
    });
    if (!res.ok) throw new Error("Failed to start MCP chat stream");
    return res;
  },

  async getMcpSessions(page = 1, limit = 20, search?: string) {
    let url = `${getBaseUrl()}/mcp/sessions?page=${page}&limit=${limit}`;
    if (search) {
      url += `&search=${encodeURIComponent(search)}`;
    }
    const res = await customFetch(url, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch past chat sessions");
    return res.json();
  },

  async getMcpSessionMessages(sessionId: string) {
    const res = await customFetch(`${getBaseUrl()}/mcp/sessions/${sessionId}/messages`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch session messages");
    return res.json();
  },

  async renameMcpSession(sessionId: string, title: string) {
    const res = await customFetch(`${getBaseUrl()}/mcp/sessions/${sessionId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ title }),
    });
    if (!res.ok) throw new Error("Failed to rename session");
    return res.json();
  },

  async pinMcpSession(sessionId: string, isPinned: boolean) {
    const res = await customFetch(`${getBaseUrl()}/mcp/sessions/${sessionId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ is_pinned: isPinned }),
    });
    if (!res.ok) throw new Error("Failed to update session pin status");
    return res.json();
  },

  async archiveMcpSession(sessionId: string, isArchived: boolean) {
    const res = await customFetch(`${getBaseUrl()}/mcp/sessions/${sessionId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ is_archived: isArchived }),
    });
    if (!res.ok) throw new Error("Failed to archive session");
    return res.json();
  },

  async deleteMcpSession(sessionId: string) {
    const res = await customFetch(`${getBaseUrl()}/mcp/sessions/${sessionId}`, {
      method: "DELETE",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to delete session");
    return res.json();
  },

  async getAgentActivity(limit = 20) {
    const res = await customFetch(`${getBaseUrl()}/agent/activity?limit=${limit}`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch agent activity feed");
    return res.json();
  },

  async getCareerPaths() {
    const res = await customFetch(`${getBaseUrl()}/ai-mentor/career-paths`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to get career paths");
    return res.json();
  },

  async getMCPServers() {
    const res = await customFetch(`${getBaseUrl()}/mcp-gateway/servers`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch MCP servers");
    return res.json();
  },

  async callMCPTool(server: string, tool: string, args: Record<string, any> = {}) {
    const res = await customFetch(`${getBaseUrl()}/mcp-gateway/call`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ server, tool, arguments: args }),
    });
    if (!res.ok) throw new Error("MCP Tool call failed");
    return res.json();
  },

  async getUserConsents() {
    const res = await customFetch(`${getBaseUrl()}/mcp-gateway/consents`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to fetch user consents");
    return res.json();
  },

  async updateUserConsent(consentType: string, granted: boolean) {
    const res = await customFetch(`${getBaseUrl()}/mcp-gateway/consents`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ consent_type: consentType, granted }),
    });
    if (!res.ok) throw new Error("Failed to update user consent");
    return res.json();
  },

  // ── Human Action Queue (HAQ) ─────────────────────────────────────────────
  async getHAQPending() {
    const res = await customFetch(`${getBaseUrl()}/haq/pending`, {
      headers: getHeaders(),
    });
    if (!res.ok) return [];
    return res.json();
  },

  async completeHAQItem(callbackKey: string, data: Record<string, unknown> = {}) {
    const res = await customFetch(`${getBaseUrl()}/haq/${callbackKey}/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to complete HAQ item");
    return res.json();
  },

  async dismissHAQItem(callbackKey: string) {
    const res = await customFetch(`${getBaseUrl()}/haq/${callbackKey}/dismiss`, {
      method: "POST",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to dismiss HAQ item");
    return res.json();
  },

  // ── Job Pool (pre-collected, < 100ms) ────────────────────────────────────
  async getJobPool(params: {
    minScore?: number;
    source?: string;
    workMode?: string;
    limit?: number;
    offset?: number;
  } = {}) {
    const query = new URLSearchParams();
    if (params.minScore !== undefined) query.set("min_score", String(params.minScore));
    if (params.source) query.set("source", params.source);
    if (params.workMode) query.set("work_mode", params.workMode);
    if (params.limit !== undefined) query.set("limit", String(params.limit));
    if (params.offset !== undefined) query.set("offset", String(params.offset));
    const res = await customFetch(`${getBaseUrl()}/candidate/jobs/pool?${query}`, {
      headers: getHeaders(),
    });
    if (!res.ok) return [];
    return res.json();
  },

  // ── Auto Apply ────────────────────────────────────────────────────────────
  async autoApplyJob(jobId: string) {
    const res = await customFetch(`${getBaseUrl()}/candidate/agent/auto-apply/${jobId}`, {
      method: "POST",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to queue auto-apply");
    return res.json();
  },

  async getAutoApplyStatus(jobId: string) {
    const res = await customFetch(
      `${getBaseUrl()}/candidate/agent/auto-apply/status/${jobId}`,
      { headers: getHeaders() }
    );
    if (!res.ok) return { status: "unknown" };
    return res.json();
  },

  /** Trigger a new Auto Apply All run — queues all matched jobs. */
  async triggerAutoApplyRun() {
    const res = await customFetch(`${getBaseUrl()}/auto-apply/run`, {
      method: "POST",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to start Auto Apply run");
    return res.json(); // { run_id, status }
  },

  /** Poll the latest Auto Apply run: returns tasks[] + metrics. */
  async getAutoApplyRuns() {
    const res = await customFetch(`${getBaseUrl()}/auto-apply/runs`, {
      headers: getHeaders(),
    });
    if (!res.ok) return { tasks: [], metrics: {} };
    return res.json(); // { run_id, tasks: ApplicationTask[], metrics: ApplyAllMetrics }
  },

  /** Perform an action on a specific task: approve | reject | resume | cancel */
  async autoApplyTaskAction(taskId: number, action: "approve" | "reject" | "resume" | "cancel") {
    const res = await customFetch(`${getBaseUrl()}/auto-apply/tasks/${taskId}/${action}`, {
      method: "POST",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error(`Failed to ${action} task`);
    return res.json();
  },

  // ── Autonomous Tasks ──────────────────────────────────────────────────────
  async getAutonomousTasks() {
    const res = await customFetch(`${getBaseUrl()}/autonomous/tasks`, {
      headers: getHeaders(),
    });
    if (!res.ok) return [];
    return res.json();
  },

  async createAutonomousTask(task: Record<string, unknown>) {
    const res = await customFetch(`${getBaseUrl()}/autonomous/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(task),
    });
    if (!res.ok) throw new Error("Failed to create task");
    return res.json();
  },

  async runAutonomousTaskNow(taskId: number) {
    const res = await customFetch(
      `${getBaseUrl()}/autonomous/tasks/${taskId}/run`,
      { method: "POST", headers: getHeaders() }
    );
    if (!res.ok) throw new Error("Failed to run task");
    return res.json();
  },

  // ── Career Health ─────────────────────────────────────────────────────────
  async getCareerHealth() {
    const res = await customFetch(`${getBaseUrl()}/candidate/career-health`, {
      headers: getHeaders(),
    });
    if (!res.ok) return null;
    return res.json();
  },
};

