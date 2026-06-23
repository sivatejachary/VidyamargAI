/**
 * VidyaMarg AI — TypeScript types for the AI Job Agent system
 */

export interface AgentStatus {
  initialized: boolean;
  agent_id?: number;
  status?: string;
  total_jobs_discovered: number;
  total_jobs_matched: number;
  total_applications: number;
  last_discovery_at?: string;
  last_match_at?: string;
  next_scheduled_at?: string;
  unread_notifications: number;
  total_active_matches: number;
  last_run?: AgentRun;
}

export interface AgentRun {
  id?: number;
  status: string;
  run_type: string;
  trigger?: string;
  jobs_discovered?: number;
  jobs_matched?: number;
  execution_time_ms?: number;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

export interface CareerDNA {
  archetype?: string;
  core_strengths?: string[];
  value_proposition?: string;
  career_stage?: string;
  domain_expertise?: string;
  specialty?: string;
}

export interface SkillNode {
  level: string;
  years: number;
  demand: string;
  is_core: boolean;
}

export interface CareerRole {
  title: string;
  stage: string;
  timeline: string;
  match_score: number;
}

export interface CareerPath {
  path_name: string;
  path_type: string;
  roles: CareerRole[];
  required_skills_to_progress: string[];
  description: string;
}

export interface JobMatch {
  id: number;
  title: string;
  company_name: string;
  location?: string;
  city?: string;
  country?: string;
  is_remote: boolean;
  is_hybrid: boolean;
  role_category?: string;
  industry?: string;
  seniority?: string;
  employment_type?: string;
  required_skills: string[];
  preferred_skills: string[];
  salary_min?: number;
  salary_max?: number;
  salary_currency?: string;
  salary_raw?: string;
  experience_min_years?: number;
  experience_max_years?: number;
  description_summary?: string;
  description?: string;
  apply_url?: string;
  job_url?: string;
  quality_score?: number;
  trust_score?: number;
  posted_at?: string;
  discovered_at?: string;
  match?: MatchScore;
  application?: ApplicationSummary;
  has_interview_prep?: boolean;
}

export interface MatchScore {
  id: number;
  overall_score: number;
  skill_score: number;
  experience_score: number;
  location_score: number;
  match_reasons: string[];
  missing_skills: string[];
  skill_gap_severity: string;
  career_growth_score: number;
  status: string;
  is_saved: boolean;
  is_hidden: boolean;
  user_reaction?: string;
  created_at?: string;
}

export interface ApplicationSummary {
  id: number;
  status: string;
  applied_at?: string;
}

export interface Application {
  id: number;
  job_id: number;
  status: string;
  job_title: string;
  company_name: string;
  location?: string;
  is_remote?: boolean;
  apply_url?: string;
  applied_via?: string;
  notes?: string;
  interview_rounds?: number;
  offer_salary?: number;
  saved_at?: string;
  applied_at?: string;
  first_interview_at?: string;
  offer_received_at?: string;
  rejected_at?: string;
  created_at?: string;
  updated_at?: string;
}

export interface SkillGap {
  gap_available: boolean;
  message?: string;
  overall_gap_score?: number;
  current_skills?: string[];
  missing_skills?: string[];
  skill_scores?: Record<string, number>;
  learning_roadmap?: LearningRoadmapItem[];
  estimated_upskill_months?: number;
  updated_at?: string;
}

export interface LearningRoadmapItem {
  month?: number;
  focus?: string;
  goals?: string[];
  resources?: string[];
  skill?: string;
  priority?: string;
  career_impact?: string;
  estimated_learning_hours?: number;
}

export interface CareerInsight {
  id: number;
  category: string;
  title: string;
  content: string;
  is_positive?: boolean;
  confidence?: number;
  actionable_steps?: string[];
  created_at?: string;
}

export interface AgentNotification {
  id: number;
  type: string;
  title: string;
  body: string;
  priority: string;
  action_url?: string;
  is_read: boolean;
  read_at?: string;
  created_at?: string;
}

export interface DashboardData {
  agent: {
    id: number;
    status: string;
    career_dna: CareerDNA;
    skill_graph: Record<string, SkillNode>;
    career_graph: { paths: CareerPath[] };
    target_roles: string[];
    total_jobs_discovered: number;
    total_jobs_matched: number;
    total_applications: number;
    last_discovery_at?: string;
  };
  top_matches: JobMatch[];
  total_matches: number;
  new_matches: number;
  applications_summary: Record<string, number>;
  total_applications: number;
  skill_gap?: SkillGap;
  career_insights: CareerInsight[];
  notifications: AgentNotification[];
  last_run?: AgentRun;
}

export interface InterviewPrep {
  status: string;
  job_id: number;
  job_title: string;
  company_name: string;
  company_analysis?: {
    overview?: string;
    products?: string[];
    culture?: string;
    recent_news?: string[];
    interview_style?: string;
  };
  technical_questions?: InterviewQuestion[];
  hr_questions?: InterviewQuestion[];
  behavioral_questions?: BehavioralQuestion[];
  culture_fit_questions?: InterviewQuestion[];
  study_topics?: StudyTopic[];
  estimated_prep_hours?: number;
  difficulty_level?: string;
}

export interface InterviewQuestion {
  question: string;
  hint?: string;
  difficulty?: string;
  topic?: string;
  ideal_answer_structure?: string;
  what_they_look_for?: string;
}

export interface BehavioralQuestion {
  question: string;
  star_framework?: {
    situation: string;
    task: string;
    action: string;
    result: string;
  };
}

export interface StudyTopic {
  topic: string;
  importance: string;
  estimated_hours: number;
}
