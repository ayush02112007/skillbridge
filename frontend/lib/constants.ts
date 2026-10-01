import type { ApplicationStatus, ProficiencyLevel, RoleName } from "@/types/api";

export const APP_NAME = "SkillBridge";
export const APP_TAGLINE = "Bridge the gap between education and industry.";
export const APP_SUBTITLE =
  "Academia–Industry Collaboration & Employability Platform";

export const ROLE_LABELS: Record<RoleName, string> = {
  STUDENT: "Student",
  ACADEMICIAN: "Academician",
  INDUSTRY_RECRUITER: "Recruiter",
  INDUSTRY_ADMIN: "Industry Admin",
  INSTITUTION_ADMIN: "Institution Admin",
  SUPER_ADMIN: "Platform Admin",
};

export const ROLE_HOME: Record<RoleName, string> = {
  STUDENT: "/student/dashboard",
  ACADEMICIAN: "/academician/dashboard",
  INDUSTRY_RECRUITER: "/industry/dashboard",
  INDUSTRY_ADMIN: "/industry/dashboard",
  INSTITUTION_ADMIN: "/institution/dashboard",
  SUPER_ADMIN: "/admin/dashboard",
};

export const PROFICIENCY_ORDER: ProficiencyLevel[] = [
  "NONE", "BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT",
];

export const PROFICIENCY_LABELS: Record<ProficiencyLevel, string> = {
  NONE: "Not started",
  BEGINNER: "Beginner",
  INTERMEDIATE: "Intermediate",
  ADVANCED: "Advanced",
  EXPERT: "Expert",
};

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  APPLIED: "Applied",
  UNDER_REVIEW: "Under review",
  SHORTLISTED: "Shortlisted",
  INTERVIEW: "Interview",
  OFFERED: "Offer",
  SELECTED: "Selected",
  REJECTED: "Not selected",
  WITHDRAWN: "Withdrawn",
};

export const APPLICATION_STATUS_TONE: Record<
  ApplicationStatus,
  "neutral" | "brand" | "success" | "warning" | "danger"
> = {
  APPLIED: "neutral",
  UNDER_REVIEW: "brand",
  SHORTLISTED: "brand",
  INTERVIEW: "warning",
  OFFERED: "success",
  SELECTED: "success",
  REJECTED: "danger",
  WITHDRAWN: "neutral",
};

/** The order a recruiter may move an application through. */
export const NEXT_STATUSES: Record<ApplicationStatus, ApplicationStatus[]> = {
  APPLIED: ["UNDER_REVIEW", "SHORTLISTED", "REJECTED"],
  UNDER_REVIEW: ["SHORTLISTED", "REJECTED"],
  SHORTLISTED: ["INTERVIEW", "OFFERED", "REJECTED"],
  INTERVIEW: ["OFFERED", "REJECTED"],
  OFFERED: ["SELECTED", "REJECTED"],
  SELECTED: [],
  REJECTED: [],
  WITHDRAWN: [],
};

/** Human labels for the matching engine's factors. */
export const MATCH_FACTOR_LABELS: Record<string, string> = {
  skills: "Skill compatibility",
  education: "Education fit",
  interest: "Career interest",
  experience: "Relevant experience",
  location: "Location & work mode",
  certification: "Certifications",
  project: "Project relevance",
};

export const WORK_MODE_LABELS: Record<string, string> = {
  ONSITE: "On-site",
  REMOTE: "Remote",
  HYBRID: "Hybrid",
};

export const DEMO_ACCOUNTS = [
  { email: "student@demo.com", label: "Student", route: "/student/dashboard" },
  { email: "industry-admin@demo.com", label: "Industry", route: "/industry/dashboard" },
  { email: "faculty@demo.com", label: "Academician", route: "/academician/dashboard" },
  { email: "institution@demo.com", label: "Institution", route: "/institution/dashboard" },
  { email: "admin@demo.com", label: "Platform admin", route: "/admin/dashboard" },
];

export const DEMO_PASSWORD = "DemoPass!2024";
