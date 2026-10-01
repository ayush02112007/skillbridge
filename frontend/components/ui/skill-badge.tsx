import { BadgeCheck, ClipboardCheck, FileText, FolderGit2, GraduationCap, Sparkles, UserCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/tooltip";
import { PROFICIENCY_LABELS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { ProficiencyLevel, SkillSource } from "@/types/api";

const LEVEL_TONE: Record<ProficiencyLevel, "neutral" | "warning" | "brand" | "success"> = {
  NONE: "neutral",
  BEGINNER: "warning",
  INTERMEDIATE: "brand",
  ADVANCED: "success",
  EXPERT: "success",
};

const SOURCE_META: Record<
  SkillSource,
  { label: string; icon: React.ReactNode; explanation: string }
> = {
  ASSESSMENT: {
    label: "Assessed",
    icon: <ClipboardCheck />,
    explanation: "Measured by a SkillBridge assessment — the strongest evidence.",
  },
  CERTIFICATION: {
    label: "Certified",
    icon: <GraduationCap />,
    explanation: "Backed by a completed certification.",
  },
  WORK_EXPERIENCE: {
    label: "From work",
    icon: <BadgeCheck />,
    explanation: "Evidenced by verified work experience.",
  },
  PROJECT: {
    label: "From project",
    icon: <FolderGit2 />,
    explanation: "Evidenced by a project you built.",
  },
  ENDORSEMENT: {
    label: "Endorsed",
    icon: <UserCheck />,
    explanation: "Endorsed by another member of the platform.",
  },
  RESUME: {
    label: "From resume",
    icon: <FileText />,
    explanation: "Detected in your resume — worth confirming with an assessment.",
  },
  SELF_REPORTED: {
    label: "Self-reported",
    icon: <Sparkles />,
    explanation: "You told us this. Take an assessment to evidence it.",
  },
};

/**
 * A skill with its level and how it is evidenced.
 *
 * Showing the evidence source next to the level is a deliberate product
 * decision: a self-reported "Advanced" and a tested "Advanced" are not the
 * same claim, and the UI should never present them as if they were.
 */
export function SkillBadge({
  name,
  level,
  source,
  confidence,
  isVerified,
  className,
}: {
  name: string;
  level?: ProficiencyLevel;
  source?: SkillSource;
  confidence?: number;
  isVerified?: boolean;
  className?: string;
}) {
  const meta = source ? SOURCE_META[source] : undefined;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-ink-200 bg-surface py-1 pl-2.5 pr-1.5 text-xs",
        className,
      )}
    >
      <span className="font-medium text-ink-800">{name}</span>
      {level && level !== "NONE" && (
        <Badge tone={LEVEL_TONE[level]} size="sm">
          {PROFICIENCY_LABELS[level]}
        </Badge>
      )}
      {meta && (
        <Tooltip
          content={
            <span>
              {meta.explanation}
              {confidence !== undefined && (
                <span className="mt-0.5 block text-ink-300">
                  Confidence {Math.round(confidence * 100)}%
                </span>
              )}
            </span>
          }
        >
          <span
            className={cn(
              "flex size-5 items-center justify-center rounded-full [&_svg]:size-3",
              source === "ASSESSMENT"
                ? "bg-success-50 text-success-700"
                : source === "SELF_REPORTED"
                  ? "bg-ink-100 text-ink-500"
                  : "bg-brand-50 text-brand-700",
            )}
            aria-label={meta.label}
          >
            {meta.icon}
          </span>
        </Tooltip>
      )}
      {isVerified && (
        <Tooltip content="Verified by the student's institution">
          <BadgeCheck className="size-3.5 text-brand-600" aria-label="Verified" />
        </Tooltip>
      )}
    </span>
  );
}
