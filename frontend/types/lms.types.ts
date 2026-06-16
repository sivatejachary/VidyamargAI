/* ═══════════════════════════════════════════════════════════
   LMS Explorer — Type Definitions
   ═══════════════════════════════════════════════════════════ */

/** Course object returned by the backend */
export interface LMSCourse {
  id: string | number;
  title: string;
  instructor?: string;
  category?: string;
  tag?: string;
  rating?: number;
  duration?: string;
  totalModules?: number;
  modules?: number;
  description?: string;
  thumbnailUrl?: string;
  published_at?: string;
  enrollment_count?: number;
  skills?: string[];
}

/** Enrollment record for a user + course */
export interface LMSEnrollment {
  id?: string | number;
  course_id: string | number;
  progress: number;
  course?: LMSCourse;
  last_accessed?: string;
  completed_lessons?: number;
  total_lessons?: number;
}

/** Career path — the primary navigation entity */
export interface CareerPath {
  id: string;
  title: string;
  subtitle: string;
  courseCount: number;
  totalHours: number;
  skills: string[];
  gradient: string;
  icon: string;
  steps: string[];
  badge?: "recommended" | "trending" | "beginner" | "job-ready";
}

/** Category → gradient mapping for course thumbnails */
export const CATEGORY_GRADIENTS: Record<string, string> = {
  "Frontend":       "from-blue-500 to-indigo-600",
  "Web Development":"from-blue-500 to-indigo-600",
  "AI/ML":          "from-purple-500 to-pink-600",
  "Machine Learning":"from-purple-500 to-pink-600",
  "Data":           "from-green-500 to-teal-600",
  "Data Science":   "from-green-500 to-teal-600",
  "Cloud":          "from-orange-500 to-red-600",
  "Cloud Computing":"from-orange-500 to-red-600",
  "Backend":        "from-slate-600 to-slate-800",
  "System Design":  "from-slate-600 to-slate-800",
  "Programming":    "from-violet-500 to-purple-700",
  "Database":       "from-emerald-500 to-teal-700",
  "Mobile Development": "from-pink-500 to-rose-600",
  "DevOps":         "from-cyan-500 to-blue-600",
  "Cybersecurity":  "from-red-500 to-rose-700",
};

export const DEFAULT_GRADIENT = "from-violet-500 to-purple-700";

/** Learning roadmap — kept for backward compatibility with RoadmapCard */
export interface LearningRoadmap {
  name: string;
  steps: string[];
  totalCourses: number;
  totalHours: number;
}

/** Carousel variant determines spacing and sizing */
export type CarouselVariant = "course" | "career" | "roadmap";

/** All career paths — the primary navigation structure */
export const CAREER_PATHS: CareerPath[] = [
  {
    id: "frontend",
    title: "Frontend Developer",
    subtitle: "Build beautiful, interactive web experiences",
    courseCount: 12,
    totalHours: 48,
    skills: ["React", "Next.js", "TypeScript", "CSS", "Testing"],
    gradient: "from-blue-500 to-indigo-600",
    icon: "🎨",
    steps: ["HTML & CSS", "JavaScript", "TypeScript", "React", "Next.js"],
    badge: "recommended",
  },
  {
    id: "backend",
    title: "Backend Developer",
    subtitle: "Design scalable APIs and server architectures",
    courseCount: 11,
    totalHours: 44,
    skills: ["Node.js", "Python", "PostgreSQL", "REST", "GraphQL"],
    gradient: "from-slate-600 to-slate-800",
    icon: "⚙️",
    steps: ["Python Basics", "Node.js", "Databases", "APIs", "Authentication"],
    badge: "trending",
  },
  {
    id: "fullstack",
    title: "Full Stack Developer",
    subtitle: "Master both frontend and backend development",
    courseCount: 16,
    totalHours: 64,
    skills: ["React", "Node.js", "PostgreSQL", "Docker", "CI/CD"],
    gradient: "from-orange-500 to-amber-600",
    icon: "🚀",
    steps: ["HTML/CSS/JS", "React", "Node.js", "Databases", "Deployment"],
    badge: "job-ready",
  },
  {
    id: "data-analyst",
    title: "Data Analyst",
    subtitle: "Turn raw data into actionable business insights",
    courseCount: 10,
    totalHours: 40,
    skills: ["Python", "SQL", "Pandas", "Tableau", "Statistics"],
    gradient: "from-green-500 to-teal-600",
    icon: "📊",
    steps: ["Excel & SQL", "Python", "Statistics", "Pandas", "Visualization"],
    badge: "beginner",
  },
  {
    id: "ai-ml",
    title: "AI/ML Engineer",
    subtitle: "Build intelligent systems with machine learning",
    courseCount: 14,
    totalHours: 56,
    skills: ["Python", "TensorFlow", "PyTorch", "NLP", "LLMs"],
    gradient: "from-purple-500 to-pink-600",
    icon: "🧠",
    steps: ["Python", "Math & Stats", "ML Fundamentals", "Deep Learning", "LLMs & NLP"],
    badge: "trending",
  },
  {
    id: "devops",
    title: "DevOps Engineer",
    subtitle: "Automate deployments and infrastructure at scale",
    courseCount: 12,
    totalHours: 50,
    skills: ["Docker", "Kubernetes", "Terraform", "CI/CD", "Linux"],
    gradient: "from-cyan-500 to-blue-600",
    icon: "🔄",
    steps: ["Linux", "Docker", "CI/CD", "Kubernetes", "Monitoring"],
    badge: "job-ready",
  },
  {
    id: "cloud",
    title: "Cloud Engineer",
    subtitle: "Architect and manage cloud infrastructure",
    courseCount: 12,
    totalHours: 50,
    skills: ["AWS", "Azure", "Terraform", "Networking", "Security"],
    gradient: "from-sky-500 to-indigo-600",
    icon: "☁️",
    steps: ["Networking", "AWS Core", "IAM & Security", "Terraform", "Architecture"],
  },
  {
    id: "cybersecurity",
    title: "Cybersecurity Engineer",
    subtitle: "Protect systems, networks, and data from threats",
    courseCount: 10,
    totalHours: 42,
    skills: ["Networks", "Cryptography", "Pentesting", "SIEM", "Compliance"],
    gradient: "from-red-500 to-rose-700",
    icon: "🛡️",
    steps: ["Networking", "Cryptography", "Ethical Hacking", "SIEM", "Compliance"],
    badge: "beginner",
  },
];

/** Badge display config */
export const PATH_BADGES: Record<string, { label: string; variant: "primary" | "success" | "warning" | "secondary" }> = {
  recommended: { label: "⭐ Recommended", variant: "primary" },
  trending:    { label: "🔥 Trending",    variant: "warning" },
  beginner:    { label: "🌱 Beginner Friendly", variant: "success" },
  "job-ready": { label: "💼 Job Ready",   variant: "secondary" },
};
