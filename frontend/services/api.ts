import { useAuthStore } from "@/store/authStore";

const customFetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
  const res = await fetch(input, init);
  if (res.status === 401) {
    if (typeof window !== "undefined") {
      useAuthStore.getState().logout();
      if (window.location.pathname !== "/") {
        window.location.href = "/";
      }
    }
  }
  return res;
};

const getBaseUrl = () => {
  // Use deployed backend URL if available
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }

  // Fallback for local development
  if (typeof window !== "undefined") {
    let host = window.location.hostname;

    if (host === "localhost") {
      host = "127.0.0.1";
    }

    return `http://${host}:8000/api/v1`;
  }

  return "https://vidyamargai-production.up.railway.app/api/v1";
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


  async startAgentRun() {
    const res = await customFetch(`${getBaseUrl()}/candidate/agent/run`, {
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
  }
};
