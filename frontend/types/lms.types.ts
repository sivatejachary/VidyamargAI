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

/** Career growth path (featured wide card) */
export interface CareerPath {
  title: string;
  courseCount: number;
  totalHours: number;
  skills: string[];
  gradient: string;
}

/** Learning roadmap with step sequence */
export interface LearningRoadmap {
  name: string;
  steps: string[];
  totalCourses: number;
  totalHours: number;
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
};

export const DEFAULT_GRADIENT = "from-violet-500 to-purple-700";

/** Skill filter chip definitions */
export const SKILL_CHIPS = [
  "All", "React", "Next.js", "Python", "AI/ML", "SQL", "AWS",
  "TypeScript", "Node.js", "Docker", "System Design", "DSA"
] as const;

export type SkillChip = (typeof SKILL_CHIPS)[number];

/** Carousel variant determines spacing and sizing */
export type CarouselVariant = "course" | "career" | "roadmap";

/** Predefined career growth paths */
export const CAREER_PATHS: CareerPath[] = [
  {
    title: "Become a Frontend Developer",
    courseCount: 12,
    totalHours: 48,
    skills: ["React", "Next.js", "TypeScript"],
    gradient: "from-blue-500 to-indigo-600",
  },
  {
    title: "Become a Data Analyst",
    courseCount: 10,
    totalHours: 40,
    skills: ["Python", "SQL", "Pandas"],
    gradient: "from-green-500 to-teal-600",
  },
  {
    title: "Become an AI/ML Engineer",
    courseCount: 14,
    totalHours: 56,
    skills: ["Python", "TensorFlow", "LLMs"],
    gradient: "from-purple-500 to-pink-600",
  },
  {
    title: "Become a Full Stack Developer",
    courseCount: 16,
    totalHours: 64,
    skills: ["React", "Node.js", "PostgreSQL"],
    gradient: "from-orange-500 to-amber-600",
  },
  {
    title: "Become a Cloud Engineer",
    courseCount: 12,
    totalHours: 50,
    skills: ["AWS", "Docker", "Kubernetes"],
    gradient: "from-slate-600 to-slate-800",
  },
];

/** Predefined learning roadmaps */
export const LEARNING_ROADMAPS: LearningRoadmap[] = [
  {
    name: "Frontend Engineer",
    steps: ["HTML", "CSS", "JavaScript", "React", "Next.js"],
    totalCourses: 5,
    totalHours: 42,
  },
  {
    name: "Data Science",
    steps: ["Python", "Statistics", "Pandas", "ML Basics", "Deep Learning"],
    totalCourses: 6,
    totalHours: 58,
  },
  {
    name: "AI Engineer",
    steps: ["Python", "NLP", "LangChain", "LLMs", "MLOps"],
    totalCourses: 5,
    totalHours: 50,
  },
  {
    name: "Cloud Engineer",
    steps: ["Linux", "Networking", "AWS Core", "Terraform", "Kubernetes"],
    totalCourses: 6,
    totalHours: 54,
  },
];
