"use client";

import { Download, FileSpreadsheet, FileText } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { downloadFile } from "@/lib/api";

const REPORTS = [
  {
    key: "placement",
    title: "Placement report",
    description:
      "Every job application from your students, with status, match score and decision dates.",
  },
  {
    key: "internship",
    title: "Internship report",
    description:
      "Internship applications and outcomes, for participation and conversion reporting.",
  },
  {
    key: "skills",
    title: "Skills report",
    description:
      "Skills your students hold, the most common gaps, and industry demand against supply.",
  },
  {
    key: "student-readiness",
    title: "Student readiness",
    description:
      "Per-student readiness, profile completion and placement status, plus the cohort distribution.",
  },
  {
    key: "industry-demand",
    title: "Industry demand",
    description:
      "What employers on the platform are asking for, and which companies engage with you most.",
  },
];

export function InstitutionReports() {
  const [pending, setPending] = useState<string | null>(null);

  const run = async (report: string, format: "csv" | "pdf") => {
    setPending(`${report}-${format}`);
    try {
      await downloadFile(
        `/analytics/reports/${report}`,
        `skillbridge-${report}.${format}`,
        { format },
      );
      toast.success("Report downloaded");
    } catch {
      toast.error("Could not generate the report");
    } finally {
      setPending(null);
    }
  };

  return (
    <>
      <PageHeader
        title="Reports"
        description="Export your institution's data for accreditation, reviews and planning. Every export is recorded in the audit trail."
      />

      <div className="grid gap-4 md:grid-cols-2">
        {REPORTS.map((report) => (
          <Card key={report.key}>
            <CardHeader>
              <CardTitle>{report.title}</CardTitle>
              <p className="text-sm leading-relaxed text-ink-500">{report.description}</p>
            </CardHeader>
            <CardContent className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                leftIcon={<FileSpreadsheet />}
                isLoading={pending === `${report.key}-csv`}
                onClick={() => void run(report.key, "csv")}
              >
                CSV
              </Button>
              <Button
                variant="secondary"
                size="sm"
                leftIcon={<FileText />}
                isLoading={pending === `${report.key}-pdf`}
                onClick={() => void run(report.key, "pdf")}
              >
                PDF
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
