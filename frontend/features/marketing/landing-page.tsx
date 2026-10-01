"use client";

import { motion, useReducedMotion } from "framer-motion";
import {
  ArrowRight, BarChart3, BookOpen, Braces, Briefcase, Building2, CheckCircle2,
  ClipboardCheck, Compass, FlaskConical, GraduationCap, LineChart, Menu, Quote,
  Search, ShieldCheck, Sparkles, Target, TrendingUp, Users, X,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { Card } from "@/components/ui/card";
import { Progress, ScoreRing } from "@/components/ui/progress";
import { APP_NAME, APP_TAGLINE } from "@/lib/constants";
import { cn } from "@/lib/utils";

import { PlatformStats } from "./platform-stats";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

const NAV_LINKS = [
  { href: "#how-it-works", label: "How it works" },
  { href: "#audiences", label: "Who it's for" },
  { href: "#matching", label: "AI matching" },
  { href: "#faq", label: "FAQ" },
];

/** Motion presets; every one is disabled when the user prefers reduced motion. */
const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  visible: { opacity: 1, y: 0 },
};

function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      variants={fadeUp}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

function Header() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 border-b border-ink-200/70 bg-surface/85 backdrop-blur-md">
      <div className="container flex h-16 items-center justify-between gap-6">
        <Link href="/" className="flex items-center gap-2.5" aria-label={`${APP_NAME} home`}>
          <span className="flex size-8 items-center justify-center rounded-lg bg-brand-700 text-white">
            <Compass className="size-4" aria-hidden />
          </span>
          <span className="text-[17px] font-semibold tracking-tight text-ink-950">
            {APP_NAME}
          </span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="rounded-lg px-3 py-2 text-sm font-medium text-ink-600 transition-colors hover:bg-ink-100 hover:text-ink-900"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          <ThemeToggle size="sm" />
          <Link href="/login">
            <Button variant="ghost" size="sm">Sign in</Button>
          </Link>
          <Link href="/register">
            <Button size="sm">Get started</Button>
          </Link>
        </div>

        <div className="md:hidden">
          <ThemeToggle size="sm" />
        </div>

        <button
          type="button"
          className="rounded-lg p-2 text-ink-700 md:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </div>

      {open && (
        <div className="border-t border-ink-200 bg-surface md:hidden">
          <nav className="container flex flex-col py-2" aria-label="Mobile">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setOpen(false)}
                className="rounded-lg px-3 py-2.5 text-sm font-medium text-ink-700 hover:bg-ink-100"
              >
                {link.label}
              </a>
            ))}
            <div className="mt-2 flex gap-2 border-t border-ink-100 pt-3">
              <Link href="/login" className="flex-1">
                <Button variant="secondary" block>Sign in</Button>
              </Link>
              <Link href="/register" className="flex-1">
                <Button block>Get started</Button>
              </Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}

function Hero() {
  const reduce = useReducedMotion();
  return (
    <section className="relative overflow-hidden border-b border-ink-200/70 bg-surface">
      <div className="hero-grid absolute inset-0" aria-hidden />
      <div className="container relative grid gap-12 py-16 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:py-24">
        <div>
          <Reveal>
            <Badge tone="brand" size="md" className="mb-5">
              <Sparkles className="size-3.5" aria-hidden />
              Industry-aware employability intelligence
            </Badge>
          </Reveal>

          <Reveal delay={0.05}>
            <h1 className="text-balance text-4xl font-semibold leading-[1.08] tracking-[-0.03em] text-ink-950 sm:text-5xl lg:text-[3.4rem]">
              {APP_TAGLINE}
            </h1>
          </Reveal>

          <Reveal delay={0.1}>
            <p className="mt-5 max-w-xl text-pretty text-base leading-relaxed text-ink-600 sm:text-lg">
              Students rarely know which skills industry actually asks for, or
              how far away they are. SkillBridge measures it, shows the gap
              precisely, and turns it into a plan that leads to real
              internships, jobs and verified experience.
            </p>
          </Reveal>

          <Reveal delay={0.15}>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="/register">
                <Button size="lg" rightIcon={<ArrowRight />}>Get started</Button>
              </Link>
              <Link href="/opportunities">
                <Button size="lg" variant="secondary" leftIcon={<Search />}>
                  Explore opportunities
                </Button>
              </Link>
            </div>
          </Reveal>

          <Reveal delay={0.2}>
            <ul className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-ink-500">
              {[
                "Free for students",
                "Explainable matching",
                "No CV black boxes",
              ].map((item) => (
                <li key={item} className="flex items-center gap-1.5">
                  <CheckCircle2 className="size-4 text-success-500" aria-hidden />
                  {item}
                </li>
              ))}
            </ul>
          </Reveal>
        </div>

        {/* A representative dashboard preview. Figures here are illustrative. */}
        <Reveal delay={0.1}>
          <motion.div
            initial={reduce ? undefined : { opacity: 0, scale: 0.97 }}
            animate={reduce ? undefined : { opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="relative"
          >
            <div className="surface-panel overflow-hidden">
              <div className="flex items-center gap-2 border-b border-ink-100 bg-surface-muted px-4 py-2.5">
                <span className="size-2.5 rounded-full bg-ink-200" aria-hidden />
                <span className="size-2.5 rounded-full bg-ink-200" aria-hidden />
                <span className="size-2.5 rounded-full bg-ink-200" aria-hidden />
                <span className="ml-2 text-2xs font-medium text-ink-400">
                  Student dashboard — illustrative preview
                </span>
              </div>

              <div className="grid gap-5 p-5 sm:grid-cols-[auto_1fr] sm:items-center">
                <div className="flex justify-center">
                  <ScoreRing value={62} size={120} label="Role readiness" sublabel="Backend Developer" />
                </div>
                <div className="space-y-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">
                    Your gap, in priority order
                  </p>
                  {[
                    { skill: "FastAPI", have: "Beginner", need: "Intermediate", value: 45 },
                    { skill: "Docker", have: "Beginner", need: "Intermediate", value: 40 },
                    { skill: "AWS", have: "Not started", need: "Intermediate", value: 12 },
                  ].map((row, index) => (
                    <div key={row.skill} className="space-y-1">
                      <div className="flex items-baseline justify-between gap-2 text-xs">
                        <span className="font-medium text-ink-800">
                          <span className="mr-1.5 text-ink-400">{index + 1}.</span>
                          {row.skill}
                        </span>
                        <span className="text-ink-500">
                          {row.have} → {row.need}
                        </span>
                      </div>
                      <Progress value={row.value} size="sm" />
                    </div>
                  ))}
                </div>
              </div>

              <div className="border-t border-ink-100 bg-surface-muted/70 px-5 py-4">
                <p className="text-2xs font-semibold uppercase tracking-wide text-ink-500">
                  Recommended because
                </p>
                <p className="mt-1.5 text-sm leading-relaxed text-ink-700">
                  &ldquo;You already meet the bar on Python, PostgreSQL and REST
                  API design. FastAPI is the one gap worth closing before you
                  apply.&rdquo;
                </p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {["Python", "PostgreSQL", "REST API Design"].map((skill) => (
                    <Badge key={skill} tone="success">{skill}</Badge>
                  ))}
                  <Badge tone="warning">FastAPI — gap</Badge>
                </div>
              </div>
            </div>
          </motion.div>
        </Reveal>
      </div>
    </section>
  );
}

function ProblemSolution() {
  return (
    <section className="border-b border-ink-200/70 bg-surface-muted py-16 lg:py-20">
      <div className="container">
        <Reveal className="mx-auto max-w-2xl text-center">
          <Badge tone="outline" className="mb-4">The problem</Badge>
          <h2 className="text-balance">
            Everyone is working with incomplete information
          </h2>
          <p className="mt-3 text-pretty text-base leading-relaxed text-ink-600">
            The gap between what is taught and what is hired for is not a
            mystery — it is simply unmeasured. SkillBridge measures it.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {[
            {
              icon: <GraduationCap />,
              title: "Students guess",
              problems: [
                "Which skills does industry actually want?",
                "Which of them do I already have?",
                "What should I learn next, in what order?",
              ],
            },
            {
              icon: <Building2 />,
              title: "Industry filters blindly",
              problems: [
                "CGPA and college name are weak proxies for skill",
                "Good candidates are missed because they present poorly",
                "Shortlists take weeks of manual screening",
              ],
            },
            {
              icon: <BarChart3 />,
              title: "Institutions fly blind",
              problems: [
                "No measured view of cohort readiness",
                "No signal on which skills are in demand",
                "Placement reporting assembled by hand",
              ],
            },
          ].map((column, index) => (
            <Reveal key={column.title} delay={index * 0.06}>
              <Card className="h-full p-6">
                <span className="mb-4 flex size-10 items-center justify-center rounded-xl bg-danger-50 text-danger-600 [&_svg]:size-5">
                  {column.icon}
                </span>
                <h3 className="mb-3">{column.title}</h3>
                <ul className="space-y-2">
                  {column.problems.map((problem) => (
                    <li key={problem} className="flex gap-2 text-sm leading-relaxed text-ink-600">
                      <span className="mt-1.5 size-1 shrink-0 rounded-full bg-ink-300" aria-hidden />
                      {problem}
                    </li>
                  ))}
                </ul>
              </Card>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

const FLOW_STEPS = [
  {
    icon: <ClipboardCheck />,
    title: "Assess",
    body: "Take a role-specific assessment. Every question is tied to a skill, so the result is a measured profile, not a self-rating.",
  },
  {
    icon: <Target />,
    title: "See the gap",
    body: "Pick a target role and see exactly which skills are missing, which are weak, and which already meet the bar — in priority order.",
  },
  {
    icon: <BookOpen />,
    title: "Follow the path",
    body: "Get an ordered learning plan that respects prerequisites, with real programmes attached to each step and honest time estimates.",
  },
  {
    icon: <Briefcase />,
    title: "Get matched",
    body: "Opportunities are ranked by fit against your evidenced skills, and every recommendation explains itself.",
  },
  {
    icon: <TrendingUp />,
    title: "Build verified experience",
    body: "A completed placement writes a verified experience record to your portfolio, which raises your readiness for the next one.",
  },
];

function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-20 border-b border-ink-200/70 bg-surface py-16 lg:py-20">
      <div className="container">
        <Reveal className="mx-auto max-w-2xl text-center">
          <Badge tone="brand" className="mb-4">How it works</Badge>
          <h2 className="text-balance">One loop, and it compounds</h2>
          <p className="mt-3 text-pretty text-base leading-relaxed text-ink-600">
            Each completed step makes the next recommendation sharper. Evidence
            accumulates; guesswork does not.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-4 md:grid-cols-3 lg:grid-cols-5">
          {FLOW_STEPS.map((step, index) => (
            <Reveal key={step.title} delay={index * 0.06}>
              <Card className="relative h-full p-5" interactive>
                <span className="absolute right-4 top-4 font-mono text-2xs text-ink-300">
                  0{index + 1}
                </span>
                <span className="mb-3 flex size-10 items-center justify-center rounded-xl bg-brand-50 text-brand-700 [&_svg]:size-5">
                  {step.icon}
                </span>
                <h3 className="mb-1.5 text-[15px]">{step.title}</h3>
                <p className="text-sm leading-relaxed text-ink-600">{step.body}</p>
              </Card>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

const AUDIENCES = [
  {
    key: "students",
    icon: <GraduationCap />,
    title: "For students",
    tagline: "Know where you stand, and what to do next.",
    points: [
      "Measured skill profile from real assessments",
      "Skill-gap analysis against any target role",
      "Ordered learning path with time estimates",
      "Matched internships and jobs with reasons",
      "A portfolio that marks verified credentials",
    ],
    cta: { href: "/register?role=STUDENT", label: "Create a student account" },
  },
  {
    key: "industry",
    icon: <Building2 />,
    title: "For industry",
    tagline: "Find people who can actually do the work.",
    points: [
      "Post roles and get structured skill requirements",
      "Candidates ranked by evidenced skill, not pedigree",
      "A shared view of what applicants are missing",
      "Run programmes, projects and mentorship",
      "Hiring funnel and time-to-hire analytics",
    ],
    cta: { href: "/register?role=INDUSTRY_ADMIN", label: "Register your company" },
  },
  {
    key: "academicians",
    icon: <FlaskConical />,
    title: "For academicians",
    tagline: "Stay connected to what industry is building.",
    points: [
      "Faculty internships, FDPs and industrial training",
      "Consultancy and sponsored research calls",
      "Mentor students in your area of expertise",
      "Co-host workshops and guest lectures",
      "Evidence of engagement for accreditation",
    ],
    cta: { href: "/register?role=ACADEMICIAN", label: "Join as an academician" },
  },
  {
    key: "institutions",
    icon: <BarChart3 />,
    title: "For institutions",
    tagline: "Replace anecdote with measurement.",
    points: [
      "Cohort readiness, by department and batch",
      "Demand vs supply against live industry postings",
      "Placement and internship pipelines in one view",
      "Verify student credentials at source",
      "Exportable reports for accreditation",
    ],
    cta: { href: "/login", label: "Institution sign in" },
  },
];

function Audiences() {
  const [active, setActive] = useState("students");
  const current = AUDIENCES.find((a) => a.key === active) ?? AUDIENCES[0];

  return (
    <section id="audiences" className="scroll-mt-20 border-b border-ink-200/70 bg-surface-muted py-16 lg:py-20">
      <div className="container">
        <Reveal className="mx-auto max-w-2xl text-center">
          <Badge tone="outline" className="mb-4">Who it&rsquo;s for</Badge>
          <h2 className="text-balance">Four participants, one shared source of truth</h2>
        </Reveal>

        <div className="mt-10 flex justify-center">
          <div
            role="tablist"
            aria-label="Audiences"
            className="no-scrollbar flex max-w-full gap-1 overflow-x-auto rounded-xl bg-surface p-1 shadow-card"
          >
            {AUDIENCES.map((audience) => (
              <button
                key={audience.key}
                role="tab"
                aria-selected={active === audience.key}
                onClick={() => setActive(audience.key)}
                className={cn(
                  "whitespace-nowrap rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                  active === audience.key
                    ? "bg-brand-700 text-white"
                    : "text-ink-600 hover:bg-ink-100 hover:text-ink-900",
                )}
              >
                {audience.title.replace("For ", "")}
              </button>
            ))}
          </div>
        </div>

        <Reveal key={current.key} className="mt-8">
          <Card className="mx-auto max-w-3xl p-7">
            <div className="flex flex-wrap items-start gap-4">
              <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700 [&_svg]:size-5">
                {current.icon}
              </span>
              <div className="min-w-0 flex-1">
                <h3 className="text-xl">{current.title}</h3>
                <p className="mt-1 text-sm text-ink-600">{current.tagline}</p>
              </div>
            </div>
            <ul className="mt-6 grid gap-2.5 sm:grid-cols-2">
              {current.points.map((point) => (
                <li key={point} className="flex gap-2 text-sm leading-relaxed text-ink-700">
                  <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-success-500" aria-hidden />
                  {point}
                </li>
              ))}
            </ul>
            <div className="mt-7">
              <Link href={current.cta.href}>
                <Button rightIcon={<ArrowRight />}>{current.cta.label}</Button>
              </Link>
            </div>
          </Card>
        </Reveal>
      </div>
    </section>
  );
}

function MatchingSection() {
  const factors = [
    { label: "Skill compatibility", weight: 50 },
    { label: "Education fit", weight: 15 },
    { label: "Career interest", weight: 10 },
    { label: "Relevant experience", weight: 10 },
    { label: "Location & work mode", weight: 5 },
    { label: "Certifications", weight: 5 },
    { label: "Project relevance", weight: 5 },
  ];

  return (
    <section id="matching" className="scroll-mt-20 border-b border-ink-200/70 bg-surface py-16 lg:py-20">
      <div className="container grid gap-12 lg:grid-cols-2 lg:items-center">
        <Reveal>
          <Badge tone="brand" className="mb-4">
            <Braces className="size-3.5" aria-hidden />
            Explainable by construction
          </Badge>
          <h2 className="text-balance">A match score you can actually interrogate</h2>
          <p className="mt-4 text-pretty leading-relaxed text-ink-600">
            The score is a weighted sum of factors we publish. There is no
            opaque model deciding who deserves an interview — the weights are
            configuration, every factor&rsquo;s contribution is returned with
            the result, and the reasoning is written in plain language.
          </p>

          <div className="mt-7 space-y-3">
            {factors.map((factor, index) => (
              <Reveal key={factor.label} delay={index * 0.04}>
                <div className="flex items-center gap-4">
                  <span className="w-44 shrink-0 text-sm text-ink-700">{factor.label}</span>
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-ink-100">
                    <div
                      className="h-full rounded-full bg-brand-600"
                      style={{ width: `${factor.weight * 2}%` }}
                    />
                  </div>
                  <span className="w-9 shrink-0 text-right text-sm font-semibold tabular-nums text-ink-800">
                    {factor.weight}%
                  </span>
                </div>
              </Reveal>
            ))}
          </div>

          <div className="mt-7 flex items-start gap-3 rounded-xl border border-brand-200 bg-brand-50/70 p-4">
            <ShieldCheck className="mt-0.5 size-5 shrink-0 text-brand-700" aria-hidden />
            <p className="text-sm leading-relaxed text-brand-900">
              <strong className="font-semibold">Decision support, not decisions.</strong>{" "}
              Protected characteristics never enter the calculation, a low score
              never blocks an application, and no shortlist is created
              automatically. Recruiters decide.
            </p>
          </div>
        </Reveal>

        <Reveal delay={0.1}>
          <Card className="overflow-hidden">
            <div className="border-b border-ink-100 bg-surface-muted px-5 py-3">
              <p className="text-2xs font-semibold uppercase tracking-wide text-ink-500">
                Example recommendation payload
              </p>
            </div>
            <pre className="overflow-x-auto p-5 font-mono text-xs leading-relaxed text-ink-700">
{`{
  "match_score": 78,
  "breakdown": {
    "skills": 0.71,
    "education": 1.00,
    "interest": 1.00,
    "experience": 0.85,
    "location": 1.00
  },
  "matching_skills": [
    "Python", "PostgreSQL", "REST APIs"
  ],
  "missing_skills": ["Docker", "AWS"],
  "reason_summary":
    "Your backend experience matches most
     technical requirements.",
  "next_steps": [
    "Build evidence in Docker",
    "Add a certification covering AWS"
  ]
}`}
            </pre>
          </Card>
        </Reveal>
      </div>
    </section>
  );
}

const TESTIMONIALS = [
  {
    quote:
      "The gap report was the first time anyone had told me specifically what to learn, and in what order. I stopped collecting tutorials and started closing gaps.",
    name: "Final-year CS student",
    context: "Illustrative — demo content",
  },
  {
    quote:
      "We see what applicants can evidence rather than where they studied. Our shortlists got smaller and better at the same time.",
    name: "Engineering hiring lead",
    context: "Illustrative — demo content",
  },
  {
    quote:
      "Being able to show demand-versus-supply for skills across departments changed how we plan the curriculum.",
    name: "Placement officer",
    context: "Illustrative — demo content",
  },
];

function Testimonials() {
  return (
    <section className="border-b border-ink-200/70 bg-surface-muted py-16 lg:py-20">
      <div className="container">
        <Reveal className="mx-auto max-w-2xl text-center">
          <Badge tone="outline" className="mb-4">Voices</Badge>
          <h2 className="text-balance">What the loop feels like in practice</h2>
          <p className="mt-3 text-sm text-ink-500">
            These quotations are illustrative demo content, written to show the
            kind of outcome the platform is built for — they are not real
            customer testimonials.
          </p>
        </Reveal>

        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {TESTIMONIALS.map((testimonial, index) => (
            <Reveal key={testimonial.name} delay={index * 0.06}>
              <Card className="flex h-full flex-col p-6">
                <Quote className="mb-3 size-5 text-brand-300" aria-hidden />
                <p className="flex-1 text-sm leading-relaxed text-ink-700">
                  {testimonial.quote}
                </p>
                <div className="mt-5 border-t border-ink-100 pt-4">
                  <p className="text-sm font-medium text-ink-900">{testimonial.name}</p>
                  <p className="text-2xs uppercase tracking-wide text-ink-400">
                    {testimonial.context}
                  </p>
                </div>
              </Card>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

const FAQS = [
  {
    q: "Is SkillBridge free for students?",
    a: "Yes. Assessments, skill-gap analysis, learning paths, recommendations and the digital portfolio are free for students. Institutions and companies pay for their own workspaces.",
  },
  {
    q: "How is the match score calculated?",
    a: "It is a weighted sum of seven factors — skill compatibility, education fit, stated career interest, relevant experience, location preference, certifications and project relevance. The weights are configuration, and every factor's contribution is returned with the score.",
  },
  {
    q: "Does AI decide who gets hired?",
    a: "No. The platform ranks and explains; people decide. A low score never blocks an application, no shortlist is created automatically, and protected characteristics are excluded from ranking entirely.",
  },
  {
    q: "What happens to my documents?",
    a: "Uploads are private by default and stored under opaque keys. Recruiters can only see a resume you attached to an application with their company. You control whether your portfolio is public, institution-only or private.",
  },
  {
    q: "Where do the skill requirements come from?",
    a: "From a curated taxonomy of skills and role profiles, kept current by a demand signal recomputed from live postings on the platform. Employers can also override requirements per posting.",
  },
  {
    q: "Can my institution verify my credentials?",
    a: "Yes. Institution administrators can verify education records and certifications, and verified items are badged on your portfolio so a viewer can tell a claim from a confirmed fact.",
  },
];

function Faq() {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <section id="faq" className="scroll-mt-20 border-b border-ink-200/70 bg-surface py-16 lg:py-20">
      <div className="container max-w-3xl">
        <Reveal className="text-center">
          <Badge tone="outline" className="mb-4">FAQ</Badge>
          <h2 className="text-balance">Questions worth asking</h2>
        </Reveal>

        <div className="mt-10 divide-y divide-ink-200 rounded-2xl border border-ink-200 bg-surface">
          {FAQS.map((faq, index) => (
            <div key={faq.q}>
              <h3>
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
                  aria-expanded={open === index}
                  aria-controls={`faq-panel-${index}`}
                  onClick={() => setOpen(open === index ? null : index)}
                >
                  <span className="text-[15px] font-medium text-ink-900">{faq.q}</span>
                  <span
                    className={cn(
                      "shrink-0 text-ink-400 transition-transform",
                      open === index && "rotate-45",
                    )}
                    aria-hidden
                  >
                    +
                  </span>
                </button>
              </h3>
              {open === index && (
                <div id={`faq-panel-${index}`} className="px-5 pb-5">
                  <p className="text-sm leading-relaxed text-ink-600">{faq.a}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CallToAction() {
  return (
    <section className="border-b border-ink-200/70 bg-canvas py-16 text-canvas-fg lg:py-20">
      <div className="container">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="text-balance text-3xl font-semibold text-white sm:text-4xl">
            Start with one honest measurement
          </h2>
          <p className="mt-4 text-pretty leading-relaxed text-ink-300">
            Take an assessment, choose a target role, and see the gap. Everything
            else the platform does follows from those two inputs.
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Link href="/register">
              <Button size="lg" rightIcon={<ArrowRight />}>Get started</Button>
            </Link>
            <Link href="/opportunities">
              <Button
                size="lg"
                variant="secondary"
                className="border-canvas-fg/25 bg-canvas-fg/10 text-canvas-fg hover:bg-canvas-fg/20"
              >
                Explore opportunities
              </Button>
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

function Footer() {
  const columns = [
    {
      title: "Platform",
      links: [
        { href: "/opportunities", label: "Opportunities" },
        { href: "#how-it-works", label: "How it works" },
        { href: "#matching", label: "AI matching" },
        { href: "#faq", label: "FAQ" },
      ],
    },
    {
      title: "Participants",
      links: [
        { href: "/register?role=STUDENT", label: "Students" },
        { href: "/register?role=INDUSTRY_ADMIN", label: "Industry" },
        { href: "/register?role=ACADEMICIAN", label: "Academicians" },
        { href: "/login", label: "Institutions" },
      ],
    },
    {
      title: "Developers",
      links: [
        { href: `${API_BASE}/docs`, label: "API reference" },
        { href: `${API_BASE}/redoc`, label: "ReDoc" },
        { href: `${API_BASE}/health`, label: "Service health" },
      ],
    },
  ];

  return (
    <footer className="bg-canvas pb-10 pt-12 text-canvas-muted">
      <div className="container">
        <div className="grid gap-10 md:grid-cols-[1.4fr_repeat(3,1fr)]">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="flex size-8 items-center justify-center rounded-lg bg-brand-600 text-white">
                <Compass className="size-4" aria-hidden />
              </span>
              <span className="text-[17px] font-semibold text-white">{APP_NAME}</span>
            </div>
            <p className="mt-3 max-w-xs text-sm leading-relaxed text-ink-400">
              An industry-aware employability platform connecting students,
              academicians, institutions and industry.
            </p>
          </div>

          {columns.map((column) => (
            <div key={column.title}>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-white">
                {column.title}
              </h3>
              <ul className="mt-3 space-y-2">
                {column.links.map((link) => (
                  <li key={link.label}>
                    {link.href.startsWith("http") ? (
                      <a
                        href={link.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-ink-400 transition-colors hover:text-white"
                      >
                        {link.label}
                      </a>
                    ) : (
                      <Link
                        href={link.href}
                        className="text-sm text-ink-400 transition-colors hover:text-white"
                      >
                        {link.label}
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-col gap-3 border-t border-canvas-fg/10 pt-6 text-xs text-canvas-muted sm:flex-row sm:items-center sm:justify-between">
          <p>
            © {new Date().getFullYear()} {APP_NAME}. A demonstration platform —
            organisations and people shown in seeded data are fictional.
          </p>
          <p className="flex items-center gap-1.5">
            <Users className="size-3.5" aria-hidden />
            Recommendations are decision support, never automated hiring.
          </p>
        </div>
      </div>
    </footer>
  );
}

export function LandingPage() {
  return (
    <div className="min-h-dvh bg-surface">
      <Header />
      <main id="main">
        <Hero />
        <PlatformStats />
        <ProblemSolution />
        <HowItWorks />
        <Audiences />
        <MatchingSection />
        <Testimonials />
        <Faq />
        <CallToAction />
      </main>
      <Footer />
    </div>
  );
}
