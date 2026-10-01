"use client";

import {
  Bookmark, BookmarkCheck, Building2, Clock, MapPin, Users,
} from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tooltip } from "@/components/ui/tooltip";
import { WORK_MODE_LABELS } from "@/lib/constants";
import { cn, daysUntil, formatRange, relativeTime } from "@/lib/utils";
import type { Opportunity } from "@/types/api";

function MatchPill({ score }: { score: number }) {
  const tone = score >= 70 ? "success" : score >= 50 ? "brand" : score >= 30 ? "warning" : "neutral";
  return (
    <Tooltip content="Skill compatibility with your evidenced profile. This is a recommendation, not a guarantee of selection.">
      <Badge tone={tone} size="md" className="tabular-nums">
        {Math.round(score)}% match
      </Badge>
    </Tooltip>
  );
}

export function OpportunityCard({
  opportunity,
  onToggleSave,
  href,
}: {
  opportunity: Opportunity;
  onToggleSave?: (opportunity: Opportunity) => void;
  href?: string;
}) {
  const deadline = daysUntil(opportunity.application_deadline);
  const isInternship = opportunity.opportunity_type === "INTERNSHIP";
  const compensation = isInternship
    ? formatRange(opportunity.stipend_min, opportunity.stipend_max)
    : formatRange(opportunity.salary_min, opportunity.salary_max);

  return (
    <Card interactive className="flex flex-col p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge tone="outline">
              {opportunity.opportunity_type === "LIVE_PROJECT"
                ? "Live project"
                : isInternship
                  ? "Internship"
                  : "Job"}
            </Badge>
            {opportunity.is_demo && <Badge tone="neutral">Demo data</Badge>}
            {opportunity.company?.verification_status === "VERIFIED" && (
              <Badge tone="brand">Verified company</Badge>
            )}
          </div>

          <h2 className="mt-2 truncate text-[15px] font-semibold text-ink-900">
            <Link href={href ?? `/opportunities/${opportunity.id}`} className="hover:underline">
              {opportunity.title}
            </Link>
          </h2>

          <p className="mt-0.5 flex items-center gap-1.5 truncate text-sm text-ink-600">
            <Building2 className="size-3.5 shrink-0 text-ink-400" aria-hidden />
            {opportunity.company?.name ?? "—"}
          </p>
        </div>

        <div className="flex shrink-0 flex-col items-end gap-2">
          {opportunity.match_score !== null && opportunity.match_score !== undefined && (
            <MatchPill score={opportunity.match_score} />
          )}
          {onToggleSave && (
            <button
              type="button"
              onClick={() => onToggleSave(opportunity)}
              aria-label={opportunity.is_saved ? "Remove from saved" : "Save opportunity"}
              aria-pressed={opportunity.is_saved}
              className={cn(
                "rounded-lg p-1.5 transition-colors",
                opportunity.is_saved
                  ? "text-brand-700 hover:bg-brand-50"
                  : "text-ink-400 hover:bg-ink-100 hover:text-ink-700",
              )}
            >
              {opportunity.is_saved ? (
                <BookmarkCheck className="size-4" />
              ) : (
                <Bookmark className="size-4" />
              )}
            </button>
          )}
        </div>
      </div>

      <dl className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-ink-600">
        <div className="flex items-center gap-1.5">
          <MapPin className="size-3.5 text-ink-400" aria-hidden />
          <dt className="sr-only">Location</dt>
          <dd>
            {opportunity.location_city ?? "—"} · {WORK_MODE_LABELS[opportunity.work_mode]}
          </dd>
        </div>
        {isInternship && opportunity.duration_weeks && (
          <div className="flex items-center gap-1.5">
            <Clock className="size-3.5 text-ink-400" aria-hidden />
            <dt className="sr-only">Duration</dt>
            <dd>{opportunity.duration_weeks} weeks</dd>
          </div>
        )}
        <div className="flex items-center gap-1.5">
          <Users className="size-3.5 text-ink-400" aria-hidden />
          <dt className="sr-only">Applications</dt>
          <dd>{opportunity.applications_count} applied</dd>
        </div>
      </dl>

      {(opportunity.matching_skills?.length || opportunity.missing_skills?.length) && (
        <div className="mt-3 flex flex-wrap gap-1">
          {opportunity.matching_skills?.slice(0, 3).map((skill) => (
            <Badge key={skill} tone="success">{skill}</Badge>
          ))}
          {opportunity.missing_skills?.slice(0, 2).map((skill) => (
            <Badge key={skill} tone="warning">{skill} — gap</Badge>
          ))}
        </div>
      )}

      {!opportunity.matching_skills && opportunity.skills.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {opportunity.skills.slice(0, 4).map((skill) => (
            <Badge key={skill.skill_id} tone="neutral">
              {skill.skill?.name}
            </Badge>
          ))}
          {opportunity.skills.length > 4 && (
            <Badge tone="outline">+{opportunity.skills.length - 4}</Badge>
          )}
        </div>
      )}

      <div className="mt-auto flex items-center justify-between gap-3 border-t border-ink-100 pt-3.5 mt-4">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-ink-900">{compensation}</p>
          <p className="truncate text-2xs text-ink-500">
            {deadline !== null && deadline >= 0
              ? `Closes in ${deadline} day${deadline === 1 ? "" : "s"}`
              : opportunity.published_at
                ? `Posted ${relativeTime(opportunity.published_at)}`
                : "Open"}
          </p>
        </div>
        <Link href={href ?? `/opportunities/${opportunity.id}`}>
          <Button size="sm" variant={opportunity.has_applied ? "secondary" : "primary"}>
            {opportunity.has_applied ? "Applied" : "View"}
          </Button>
        </Link>
      </div>
    </Card>
  );
}
