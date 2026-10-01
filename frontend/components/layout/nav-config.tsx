import {
  Award, BarChart3, Bell, BookOpen, Briefcase, Building2, Calendar,
  ClipboardCheck, Compass, FileText, FlaskConical, Folder, GraduationCap,
  LayoutDashboard, LineChart, MessageSquare, Settings, Shield,
  Sparkles, Target, TrendingUp, UserCircle, Users, Wrench,
} from "lucide-react";

import type { RoleName } from "@/types/api";

export interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
  /** Shown on mobile bottom navigation. */
  primary?: boolean;
}

export interface NavSection {
  title?: string;
  items: NavItem[];
}

export const NAV_BY_ROLE: Record<RoleName, NavSection[]> = {
  STUDENT: [
    {
      items: [
        { href: "/student/dashboard", label: "Dashboard", icon: <LayoutDashboard />, primary: true },
        { href: "/student/profile", label: "My Profile", icon: <UserCircle /> },
      ],
    },
    {
      title: "Skills",
      items: [
        { href: "/student/assessment", label: "Skill Assessment", icon: <ClipboardCheck />, primary: true },
        { href: "/student/skills", label: "My Skills", icon: <Sparkles /> },
        { href: "/student/skill-gap", label: "Skill Gap", icon: <Target />, primary: true },
        { href: "/student/careers", label: "Career Recommendations", icon: <Compass /> },
      ],
    },
    {
      title: "Opportunities",
      items: [
        { href: "/student/internships", label: "Internships", icon: <Briefcase />, primary: true },
        { href: "/student/jobs", label: "Jobs", icon: <Building2 /> },
        { href: "/student/projects", label: "Live Projects", icon: <Folder /> },
        { href: "/student/applications", label: "Applications", icon: <FileText /> },
      ],
    },
    {
      title: "Grow",
      items: [
        { href: "/student/learning", label: "Learning Programs", icon: <BookOpen /> },
        { href: "/student/certifications", label: "Certifications", icon: <Award /> },
        { href: "/student/mentorship", label: "Mentorship", icon: <Users /> },
        { href: "/student/workshops", label: "Workshops & Events", icon: <Calendar /> },
        { href: "/student/interview-prep", label: "Interview Prep", icon: <MessageSquare /> },
      ],
    },
    {
      title: "Showcase",
      items: [
        { href: "/student/portfolio", label: "Digital Portfolio", icon: <GraduationCap /> },
        { href: "/student/documents", label: "Documents", icon: <FileText /> },
      ],
    },
    {
      items: [
        { href: "/student/notifications", label: "Notifications", icon: <Bell /> },
        { href: "/student/settings", label: "Settings", icon: <Settings /> },
      ],
    },
  ],

  ACADEMICIAN: [
    {
      items: [
        { href: "/academician/dashboard", label: "Dashboard", icon: <LayoutDashboard />, primary: true },
        { href: "/academician/profile", label: "My Profile", icon: <UserCircle /> },
      ],
    },
    {
      title: "Industry engagement",
      items: [
        { href: "/academician/opportunities", label: "Faculty Programmes", icon: <Briefcase />, primary: true },
        { href: "/academician/research", label: "Research & Consultancy", icon: <FlaskConical />, primary: true },
        { href: "/academician/mentorship", label: "Mentorship", icon: <Users />, primary: true },
        { href: "/academician/events", label: "Workshops & Events", icon: <Calendar /> },
      ],
    },
    {
      items: [
        { href: "/academician/notifications", label: "Notifications", icon: <Bell /> },
        { href: "/academician/settings", label: "Settings", icon: <Settings /> },
      ],
    },
  ],

  INDUSTRY_RECRUITER: [
    {
      items: [
        { href: "/industry/dashboard", label: "Overview", icon: <LayoutDashboard />, primary: true },
        { href: "/industry/company", label: "Company Profile", icon: <Building2 /> },
      ],
    },
    {
      title: "Hiring",
      items: [
        { href: "/industry/jobs", label: "Jobs", icon: <Briefcase />, primary: true },
        { href: "/industry/internships", label: "Internships", icon: <GraduationCap />, primary: true },
        { href: "/industry/applicants", label: "Applicants", icon: <Users />, primary: true },
        { href: "/industry/analytics", label: "Analytics", icon: <LineChart /> },
      ],
    },
    {
      title: "Programmes",
      items: [
        { href: "/industry/programs", label: "Learning Programmes", icon: <BookOpen /> },
        { href: "/industry/projects", label: "Live Projects", icon: <Folder /> },
        { href: "/industry/events", label: "Events", icon: <Calendar /> },
        { href: "/industry/research", label: "Research", icon: <FlaskConical /> },
      ],
    },
    {
      items: [
        { href: "/industry/notifications", label: "Notifications", icon: <Bell /> },
        { href: "/industry/settings", label: "Settings", icon: <Settings /> },
      ],
    },
  ],

  INDUSTRY_ADMIN: [], // populated below — identical to recruiter

  INSTITUTION_ADMIN: [
    {
      items: [
        { href: "/institution/dashboard", label: "Dashboard", icon: <LayoutDashboard />, primary: true },
        { href: "/institution/students", label: "Students", icon: <Users />, primary: true },
      ],
    },
    {
      title: "Insight",
      items: [
        { href: "/institution/analytics", label: "Analytics", icon: <BarChart3 />, primary: true },
        { href: "/institution/placements", label: "Placements", icon: <TrendingUp />, primary: true },
        { href: "/institution/internships", label: "Internships", icon: <Briefcase /> },
        { href: "/institution/reports", label: "Reports", icon: <FileText /> },
      ],
    },
    {
      title: "Administration",
      items: [
        { href: "/institution/departments", label: "Departments", icon: <Building2 /> },
        { href: "/institution/partnerships", label: "Industry Partners", icon: <Users /> },
        { href: "/institution/settings", label: "Settings", icon: <Settings /> },
      ],
    },
  ],

  SUPER_ADMIN: [
    {
      items: [
        { href: "/admin/dashboard", label: "Dashboard", icon: <LayoutDashboard />, primary: true },
        { href: "/admin/analytics", label: "Platform Analytics", icon: <BarChart3 />, primary: true },
      ],
    },
    {
      title: "Management",
      items: [
        { href: "/admin/users", label: "Users", icon: <Users />, primary: true },
        { href: "/admin/organisations", label: "Organisations", icon: <Building2 /> },
        { href: "/admin/skills", label: "Skills & Roles", icon: <Sparkles />, primary: true },
        { href: "/admin/assessments", label: "Assessments", icon: <ClipboardCheck /> },
        { href: "/admin/opportunities", label: "Moderation", icon: <Shield /> },
      ],
    },
    {
      title: "System",
      items: [
        { href: "/admin/audit", label: "Audit Log", icon: <FileText /> },
        { href: "/admin/system", label: "System Health", icon: <Wrench /> },
      ],
    },
  ],
};

NAV_BY_ROLE.INDUSTRY_ADMIN = NAV_BY_ROLE.INDUSTRY_RECRUITER;

/** Pick the navigation for the highest-privilege role a user holds. */
export function navForRoles(roles: RoleName[]): NavSection[] {
  const order: RoleName[] = [
    "SUPER_ADMIN", "INSTITUTION_ADMIN", "INDUSTRY_ADMIN", "INDUSTRY_RECRUITER",
    "ACADEMICIAN", "STUDENT",
  ];
  const match = order.find((role) => roles.includes(role));
  return match ? NAV_BY_ROLE[match] : [];
}
