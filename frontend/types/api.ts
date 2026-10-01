/**
 * Types mirroring the SkillBridge API contract.
 *
 * Every successful response is `{ success: true, data: T }` and every list
 * response adds `meta` with pagination. Errors are always
 * `{ success: false, error: { code, message, details? } }`.
 */

export type UUID = string;

export interface Envelope<T> {
  success: true;
  data: T;
  meta?: Record<string, unknown>;
}

export interface PageMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface Paged<T> {
  success: true;
  data: T[];
  meta: PageMeta;
}

export interface ApiErrorBody {
  success: false;
  error: { code: string; message: string; details?: unknown };
}

// ------------------------------------------------------------------ auth --
export type RoleName =
  | "STUDENT"
  | "ACADEMICIAN"
  | "INDUSTRY_RECRUITER"
  | "INDUSTRY_ADMIN"
  | "INSTITUTION_ADMIN"
  | "SUPER_ADMIN";

export type UserStatus =
  | "PENDING_VERIFICATION"
  | "ACTIVE"
  | "SUSPENDED"
  | "DEACTIVATED";

export interface Role {
  name: RoleName;
  label: string;
  description: string;
}

export interface User {
  id: UUID;
  email: string;
  full_name: string;
  phone?: string | null;
  avatar_url?: string | null;
  status: UserStatus;
  is_email_verified: boolean;
  locale: string;
  timezone_name: string;
  institution_id?: UUID | null;
  company_id?: UUID | null;
  roles: Role[];
  created_at: string;
  last_login_at?: string | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  expires_at: string;
}

export interface SessionPayload {
  user: User;
  roles: RoleName[];
  permissions: string[];
  home_route: string;
  profile_id?: UUID | null;
  profile_completion: number;
  requires_onboarding: boolean;
  csrf_token?: string | null;
}

export interface AuthResponse {
  tokens: TokenPair;
  session: SessionPayload;
}

// ---------------------------------------------------------------- skills --
export type ProficiencyLevel =
  | "NONE"
  | "BEGINNER"
  | "INTERMEDIATE"
  | "ADVANCED"
  | "EXPERT";

export type SkillImportance = "REQUIRED" | "PREFERRED" | "OPTIONAL";

export type SkillSource =
  | "SELF_REPORTED"
  | "ASSESSMENT"
  | "CERTIFICATION"
  | "PROJECT"
  | "RESUME"
  | "ENDORSEMENT"
  | "WORK_EXPERIENCE";

export interface SkillBrief {
  id: UUID;
  name: string;
  slug: string;
  demand_score: number;
}

export interface SkillCategory {
  id: UUID;
  name: string;
  slug: string;
  icon?: string | null;
  color?: string | null;
  is_soft_skill: boolean;
}

export interface Skill extends SkillBrief {
  category_id: UUID;
  description: string;
  aliases: string[];
  is_soft_skill: boolean;
  is_trending: boolean;
  learning_resources: unknown[];
  category?: SkillCategory | null;
}

export interface TaxonomyNode {
  id: UUID;
  name: string;
  slug: string;
  icon?: string | null;
  color?: string | null;
  is_soft_skill: boolean;
  skill_count: number;
  skills: SkillBrief[];
}

export interface RoleSkill {
  skill_id: UUID;
  skill?: SkillBrief | null;
  required_level: ProficiencyLevel;
  importance: SkillImportance;
  weight: number;
}

export interface JobRole {
  id: UUID;
  title: string;
  slug: string;
  family: string;
  description: string;
  responsibilities: string[];
  typical_qualifications: string[];
  seniority: string;
  avg_salary_min?: number | null;
  avg_salary_max?: number | null;
  demand_index: number;
  required_skills: RoleSkill[];
}

export interface StudentSkill {
  id: UUID;
  skill_id: UUID;
  skill?: SkillBrief | null;
  level: ProficiencyLevel;
  score: number;
  confidence: number;
  source: SkillSource;
  years_of_experience?: number | null;
  last_assessed_at?: string | null;
  endorsement_count: number;
  is_verified: boolean;
  evidence: Record<string, unknown>;
}

export type GapStatus = "MISSING" | "WEAK" | "STRONG";

export interface GapItem {
  skill_id: UUID;
  skill_name: string;
  skill_slug: string;
  category: string;
  current_level: string;
  required_level: string;
  status: GapStatus;
  gap_size: number;
  importance: string;
  weight: number;
  coverage: number;
  priority: number;
  recommendation: string;
}

export interface SkillGap {
  job_role_id: UUID;
  job_role_title: string;
  readiness_score: number;
  gap_percentage: number;
  matched_count: number;
  total_required: number;
  summary: string;
  computed_at?: string | null;
  generated_by: string;
  items: GapItem[];
  missing_skills: GapItem[];
  weak_skills: GapItem[];
  strong_skills: GapItem[];
  priority_skills: GapItem[];
}

export interface RoleReadiness {
  job_role_id: UUID;
  title: string;
  family: string;
  readiness_score: number;
  gap_percentage: number;
  matched_count: number;
  total_required: number;
  top_missing: string[];
  demand_index: number;
}

// --------------------------------------------------------------- student --
export interface StudentProfile {
  id: UUID;
  user_id: UUID;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  avatar_url?: string | null;
  headline?: string | null;
  bio: string;
  date_of_birth?: string | null;
  gender?: string | null;
  city?: string | null;
  state?: string | null;
  country: string;
  institution_id?: UUID | null;
  institution_name?: string | null;
  department_id?: UUID | null;
  department_name?: string | null;
  enrollment_number?: string | null;
  degree: string;
  program_name?: string | null;
  current_year?: number | null;
  current_semester?: number | null;
  cgpa?: number | null;
  graduation_year?: number | null;
  backlogs: number;
  career_interests: string[];
  preferred_roles: string[];
  preferred_industries: string[];
  preferred_locations: string[];
  preferred_work_mode?: string | null;
  open_to_relocate: boolean;
  expected_stipend_min?: number | null;
  expected_salary_min?: number | null;
  target_job_role_id?: UUID | null;
  target_job_role_title?: string | null;
  portfolio_slug?: string | null;
  portfolio_visibility: Visibility;
  profile_completion: number;
  skill_readiness_score: number;
  readiness_computed_at?: string | null;
  is_open_to_work: boolean;
  is_placed: boolean;
  github_url?: string | null;
  linkedin_url?: string | null;
  portfolio_url?: string | null;
  is_demo: boolean;
}

export type Visibility = "PUBLIC" | "INSTITUTION_ONLY" | "PRIVATE";

export interface CompletionSection {
  key: string;
  label: string;
  weight: number;
  earned: number;
  percentage: number;
  is_complete: boolean;
}

export interface ProfileCompletion {
  percentage: number;
  sections: CompletionSection[];
  suggestions: { action: string; impact: number; url: string }[];
  counts: Record<string, number>;
}

export interface StudentDashboard {
  profile_completion: ProfileCompletion;
  skill_readiness_score: number;
  readiness_computed_at?: string | null;
  target_role?: { id: UUID; title: string } | null;
  top_skills: {
    skill_id: UUID;
    name: string;
    level: ProficiencyLevel;
    score: number;
    confidence: number;
    source: SkillSource;
  }[];
  skill_gap?: {
    job_role_id: UUID;
    job_role_title: string;
    readiness_score: number;
    gap_percentage: number;
    matched_count: number;
    total_required: number;
    summary: string;
    priority_skills: {
      skill_id: UUID;
      skill_name: string;
      status: GapStatus;
      current_level: string;
      required_level: string;
      priority: number;
    }[];
  } | null;
  applications: {
    total: number;
    by_status: Record<string, number>;
    interviews_scheduled: number;
    recent: {
      id: UUID;
      status: ApplicationStatus;
      match_score: number;
      submitted_at: string;
      opportunity_id: UUID;
      opportunity_title: string;
      company_name: string;
    }[];
  };
  upcoming_deadlines: {
    id: UUID;
    title: string;
    company_name: string;
    type: string;
    deadline: string;
  }[];
  learning: {
    active_enrollments: number;
    completed: number;
    certifications: number;
    recent: {
      id: UUID;
      program_id: UUID;
      title: string;
      progress: number;
      status: string;
    }[];
  };
  assessments: {
    completed: number;
    recent: {
      id: UUID;
      assessment_id: UUID;
      title: string;
      percentage: number;
      is_passed: boolean;
      submitted_at?: string | null;
    }[];
  };
  badges: { code: string; name: string; icon: string; awarded_at: string }[];
  portfolio: { slug?: string | null; visibility: Visibility; is_published: boolean };
}

// --------------------------------------------------------- opportunities --
export type OpportunityType =
  | "INTERNSHIP"
  | "JOB"
  | "LIVE_PROJECT"
  | "FACULTY_OPPORTUNITY";

export type OpportunityStatus =
  | "DRAFT"
  | "PUBLISHED"
  | "PAUSED"
  | "CLOSED"
  | "ARCHIVED";

export type WorkMode = "ONSITE" | "REMOTE" | "HYBRID";

export interface CompanyBrief {
  id: UUID;
  name: string;
  slug: string;
  logo_url?: string | null;
  industry_sector: string;
  headquarters_city?: string | null;
  verification_status?: string | null;
}

export interface OpportunitySkill {
  skill_id: UUID;
  skill?: SkillBrief | null;
  required_level: ProficiencyLevel;
  importance: SkillImportance;
  weight: number;
}

export interface Opportunity {
  id: UUID;
  opportunity_type: OpportunityType;
  title: string;
  slug: string;
  company?: CompanyBrief | null;
  status: OpportunityStatus;
  work_mode: WorkMode;
  location_city?: string | null;
  positions: number;
  application_deadline?: string | null;
  published_at?: string | null;
  applications_count: number;
  views_count: number;
  job_role_title?: string | null;
  skills: OpportunitySkill[];
  is_open: boolean;
  is_demo: boolean;
  match_score?: number | null;
  matching_skills?: string[] | null;
  missing_skills?: string[] | null;
  has_applied: boolean;
  is_saved: boolean;
  stipend_min?: number | null;
  stipend_max?: number | null;
  duration_weeks?: number | null;
  salary_min?: number | null;
  salary_max?: number | null;
  employment_type?: string | null;
  experience_min_years?: number | null;
}

export interface MatchExplanation {
  match_score: number;
  breakdown: Record<string, number>;
  contributions: Record<string, number>;
  matching_skills: string[];
  missing_skills: string[];
  reasons: string[];
  reason_summary: string;
  next_steps: string[];
  is_eligible: boolean;
  ineligibility_reasons: string[];
}

export interface OpportunityDetail extends Opportunity {
  description: string;
  responsibilities: string[];
  eligibility_text: string;
  location_country: string;
  min_cgpa?: number | null;
  max_backlogs?: number | null;
  eligible_degrees: string[];
  eligible_graduation_years: number[];
  eligible_departments: string[];
  starts_on?: string | null;
  perks: string[];
  extracted_requirements: Record<string, unknown>;
  created_at?: string | null;
  details: Record<string, unknown>;
  match?: MatchExplanation | null;
}

// ---------------------------------------------------------- applications --
export type ApplicationStatus =
  | "APPLIED"
  | "UNDER_REVIEW"
  | "SHORTLISTED"
  | "INTERVIEW"
  | "OFFERED"
  | "SELECTED"
  | "REJECTED"
  | "WITHDRAWN";

export interface TimelineStep {
  status: string;
  label: string;
  state: "complete" | "current" | "upcoming" | "stopped" | "terminal";
  reached_at?: string | null;
}

export interface Interview {
  id: UUID;
  round_number: number;
  round_name: string;
  mode: string;
  scheduled_at: string;
  duration_minutes: number;
  location_or_link?: string | null;
  interviewer_name?: string | null;
  status: string;
  instructions: string;
  feedback: string;
  rating?: number | null;
}

export interface ApplicantBrief {
  student_id?: UUID | null;
  user_id?: UUID | null;
  full_name: string;
  email?: string | null;
  avatar_url?: string | null;
  headline?: string | null;
  city?: string | null;
  institution_name?: string | null;
  degree?: string | null;
  graduation_year?: number | null;
  cgpa?: number | null;
  portfolio_slug?: string | null;
  skill_readiness_score: number;
}

export interface OpportunityBrief {
  id: UUID;
  title: string;
  opportunity_type: OpportunityType;
  location_city?: string | null;
  work_mode?: string | null;
  application_deadline?: string | null;
  company?: CompanyBrief | null;
}

export interface Application {
  id: UUID;
  status: ApplicationStatus;
  match_score: number;
  match_breakdown: Record<string, number>;
  matching_skills: string[];
  missing_skills: string[];
  cover_letter: string;
  resume_document_id?: UUID | null;
  submitted_at: string;
  last_status_change_at?: string | null;
  decided_at?: string | null;
  rejection_reason?: string | null;
  recruiter_rating?: number | null;
  recruiter_notes?: string | null;
  opportunity?: OpportunityBrief | null;
  applicant?: ApplicantBrief | null;
  timeline: TimelineStep[];
  history: {
    from_status?: ApplicationStatus | null;
    to_status: ApplicationStatus;
    note: string;
    created_at: string;
  }[];
  interviews: Interview[];
}

export interface ApplicationListItem {
  id: UUID;
  status: ApplicationStatus;
  match_score: number;
  matching_skills: string[];
  missing_skills: string[];
  submitted_at: string;
  last_status_change_at?: string | null;
  opportunity?: OpportunityBrief | null;
  applicant?: ApplicantBrief | null;
  next_interview_at?: string | null;
  recruiter_rating?: number | null;
}

// -------------------------------------------------------- recommendations --
export interface RecommendationBase {
  match_score: number;
  breakdown: Record<string, number>;
  matching_skills: string[];
  missing_skills: string[];
  reasons: string[];
  reason_summary: string;
  next_steps: string[];
  generated_by: string;
}

export interface OpportunityRecommendation extends RecommendationBase {
  target_id: UUID;
  target_title: string;
  opportunity_type: string;
  company_id?: UUID | null;
  company_name: string;
  location_city?: string | null;
  work_mode?: string | null;
  application_deadline?: string | null;
  contributions: Record<string, number>;
}

export interface CareerRoleRecommendation extends RecommendationBase {
  target_id: UUID;
  target_title: string;
  family: string;
  readiness_score: number;
  demand_index: number;
  salary_range: (number | null)[];
}

export interface LearningRecommendation extends RecommendationBase {
  target_id: UUID;
  target_title: string;
  program_type: string;
  provider: string;
  duration_hours: number;
  is_free: boolean;
  difficulty: string;
}

export interface MentorRecommendation extends RecommendationBase {
  target_id: UUID;
  target_title: string;
  headline: string;
  designation?: string | null;
  industry?: string | null;
  experience_years: number;
  rating: number;
}

export interface SkillRecommendation {
  skill_id: UUID;
  skill_name: string;
  category: string;
  demand_score: number;
  open_postings: number;
  gap_priority?: number | null;
  already_held: boolean;
  score: number;
  reasons: string[];
}

export interface LearningPathStep {
  order: number;
  skill_id: UUID;
  skill_name: string;
  current_level: string;
  target_level: string;
  status: GapStatus;
  why: string;
  estimated_hours: number;
  programs: {
    id: string;
    title: string;
    provider: string;
    duration_hours: number;
    is_free: boolean;
    program_type: string;
  }[];
  prerequisites: string[];
}

export interface LearningPath {
  job_role_id: UUID;
  job_role_title: string;
  title: string;
  summary: string;
  readiness_score: number;
  gap_percentage: number;
  estimated_weeks: number;
  total_hours: number;
  steps: LearningPathStep[];
  generated_by: string;
}

// ------------------------------------------------------------ assessment --
export interface AssessmentListItem {
  id: UUID;
  title: string;
  slug: string;
  description: string;
  assessment_type: string;
  domain?: string | null;
  duration_minutes: number;
  passing_score: number;
  question_count: number;
  job_role_title?: string | null;
  attempts_used: number;
  max_attempts: number;
  best_percentage?: number | null;
  can_attempt: boolean;
}

export interface AttemptQuestion {
  id: UUID;
  prompt: string;
  code_snippet?: string | null;
  question_type: string;
  difficulty: string;
  skill_id: UUID;
  skill_name: string;
  subskill?: string | null;
  weight: number;
  display_order: number;
  options: { id: UUID; label: string; display_order: number }[];
}

export interface AttemptStart {
  attempt_id: UUID;
  assessment_id: UUID;
  assessment_title: string;
  attempt_number: number;
  status: string;
  started_at: string;
  expires_at?: string | null;
  duration_minutes: number;
  total_questions: number;
  questions: AttemptQuestion[];
}

export interface AttemptResult {
  attempt_id: UUID;
  assessment_id: UUID;
  assessment_title: string;
  status: string;
  attempt_number: number;
  raw_score: number;
  max_score: number;
  percentage: number;
  confidence: number;
  is_passed: boolean;
  duration_seconds?: number | null;
  submitted_at?: string | null;
  feedback: string;
  skill_scores: {
    skill_id: UUID;
    skill_name: string;
    score: number;
    max_score: number;
    percentage: number;
    questions_count: number;
    correct_count: number;
    confidence: number;
    level: ProficiencyLevel;
  }[];
  answers: {
    question_id: UUID;
    prompt: string;
    skill_name: string;
    difficulty: string;
    is_correct: boolean;
    awarded_score: number;
    max_score: number;
    selected_option_ids: string[];
    correct_option_ids: string[];
    explanation: string;
  }[];
}

// -------------------------------------------------------------- learning --
export interface LearningProgram {
  id: UUID;
  title: string;
  slug: string;
  summary: string;
  program_type: string;
  provider_name?: string | null;
  company?: CompanyBrief | null;
  difficulty: string;
  duration_hours: number;
  mode: WorkMode;
  is_free: boolean;
  price_amount: number;
  currency: string;
  grants_certificate: boolean;
  rating: number;
  enrollment_count: number;
  skills: { skill_id: UUID; skill?: SkillBrief | null; target_level: string }[];
  is_enrolled: boolean;
  is_demo: boolean;
}

export interface Enrollment {
  id: UUID;
  program_id: UUID;
  program?: LearningProgram | null;
  status: string;
  progress_percentage: number;
  enrolled_at: string;
  completed_at?: string | null;
  final_score?: number | null;
}

// ---------------------------------------------------------------- shared --
export interface NotificationItem {
  id: UUID;
  category: string;
  title: string;
  body: string;
  action_url?: string | null;
  action_label?: string | null;
  icon?: string | null;
  resource_type?: string | null;
  resource_id?: UUID | null;
  read_at?: string | null;
  created_at: string;
}

export interface SearchHit {
  id: UUID;
  type: string;
  title: string;
  subtitle: string;
  url: string;
  icon: string;
  score: number;
}

export interface SearchGroup {
  type: string;
  label: string;
  total: number;
  results: SearchHit[];
}

export interface GlobalSearch {
  query: string;
  total: number;
  groups: SearchGroup[];
}

export interface Institution {
  id: UUID;
  name: string;
  slug: string;
  short_name?: string | null;
  institution_type: string;
  city?: string | null;
  state?: string | null;
  country: string;
  verification_status: string;
  student_count: number;
}

export interface Mentor {
  id: UUID;
  user_id: UUID;
  full_name: string;
  avatar_url?: string | null;
  headline: string;
  bio: string;
  designation?: string | null;
  experience_years: number;
  industry?: string | null;
  expertise_skills: string[];
  topics: string[];
  capacity_per_month: number;
  session_duration_minutes: number;
  is_accepting_requests: boolean;
  rating: number;
  sessions_completed: number;
}

export interface EventItem {
  id: UUID;
  title: string;
  slug: string;
  description: string;
  event_type: string;
  company?: CompanyBrief | null;
  speaker_name?: string | null;
  speaker_designation?: string | null;
  mode: WorkMode;
  venue?: string | null;
  meeting_link?: string | null;
  starts_at: string;
  ends_at: string;
  capacity?: number | null;
  registered_count: number;
  skill_tags: string[];
  grants_certificate: boolean;
  is_registered: boolean;
  has_capacity: boolean;
}

export interface PublicPortfolio {
  slug: string;
  full_name: string;
  headline: string;
  about: string;
  theme: string;
  avatar_url?: string | null;
  city?: string | null;
  institution_name?: string | null;
  program_name?: string | null;
  graduation_year?: number | null;
  email?: string | null;
  phone?: string | null;
  github_url?: string | null;
  linkedin_url?: string | null;
  skills: {
    name: string;
    category: string;
    level: ProficiencyLevel;
    score: number;
    source: SkillSource;
    is_verified: boolean;
  }[];
  education: Record<string, unknown>[];
  experience: Record<string, unknown>[];
  projects: Record<string, unknown>[];
  certifications: Record<string, unknown>[];
  achievements: Record<string, unknown>[];
  badges: { code: string; name: string; icon: string }[];
  skill_readiness_score: number;
  verified_credential_count: number;
}
