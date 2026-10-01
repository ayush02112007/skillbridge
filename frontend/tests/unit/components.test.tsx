/**
 * Shared UI primitives.
 *
 * The assertions here are mostly about accessibility and about the state
 * machine of data views: a screen must never render blank, and a score must
 * always be announced, not only drawn.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox, Field, Input, Select, Textarea } from "@/components/ui/input";
import { Progress, ScoreRing } from "@/components/ui/progress";
import { SkillBadge } from "@/components/ui/skill-badge";
import { EmptyState, ErrorState, QueryState } from "@/components/ui/states";

describe("Progress", () => {
  it("exposes the value to assistive technology", () => {
    render(<Progress value={63} label="Role readiness" />);
    const bar = screen.getByRole("progressbar", { name: "Role readiness" });
    expect(bar).toHaveAttribute("aria-valuenow", "63");
    expect(bar).toHaveAttribute("aria-valuemin", "0");
    expect(bar).toHaveAttribute("aria-valuemax", "100");
  });

  it("clamps out-of-range values instead of overflowing the track", () => {
    render(<Progress value={140} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  });

  it("shows a numeric read-out when asked", () => {
    render(<Progress value={48.6} label="Profile" showValue />);
    expect(screen.getByText("49%")).toBeInTheDocument();
  });
});

describe("ScoreRing", () => {
  it("announces the score as text, not only as an arc", () => {
    render(<ScoreRing value={72} label="Readiness" />);
    expect(screen.getByRole("img", { name: "Readiness: 72 percent" })).toBeInTheDocument();
    expect(screen.getByText("72")).toBeInTheDocument();
  });
});

describe("SkillBadge", () => {
  it("shows the level alongside the skill", () => {
    render(<SkillBadge name="React" level="ADVANCED" source="ASSESSMENT" confidence={0.9} />);
    expect(screen.getByText("React")).toBeInTheDocument();
    expect(screen.getByText("Advanced")).toBeInTheDocument();
  });

  it("does not render a level chip for NONE", () => {
    render(<SkillBadge name="Kubernetes" level="NONE" />);
    expect(screen.getByText("Kubernetes")).toBeInTheDocument();
    expect(screen.queryByText("None")).not.toBeInTheDocument();
  });
});

describe("Button", () => {
  it("calls its handler", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Apply now</Button>);
    await userEvent.click(screen.getByRole("button", { name: "Apply now" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("is disabled and non-interactive while loading", async () => {
    const onClick = vi.fn();
    render(
      <Button isLoading onClick={onClick}>
        Submit
      </Button>,
    );
    const button = screen.getByRole("button");
    expect(button).toBeDisabled();
    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });
});

describe("Input / Field", () => {
  it("links the label and error message to the control", () => {
    render(
      <Input label="Email" error="Already registered" placeholder="you@college.edu" />,
    );

    const input = screen.getByLabelText(/Email/);
    expect(input).toHaveAttribute("aria-invalid", "true");

    const describedBy = input.getAttribute("aria-describedby") ?? "";
    const described = describedBy
      .split(" ")
      .filter(Boolean)
      .map((id) => document.getElementById(id)?.textContent);
    expect(described).toContain("Already registered");
    expect(screen.getByRole("alert")).toHaveTextContent("Already registered");
  });

  it("links the hint when there is no error", () => {
    render(<Input label="Roll number" hint="As printed on your ID card" />);
    const input = screen.getByLabelText(/Roll number/);
    const hintId = input.getAttribute("aria-describedby") ?? "";
    expect(document.getElementById(hintId)).toHaveTextContent("As printed on your ID card");
  });

  it("marks required fields for screen readers as well as visually", () => {
    render(<Input label="Full name" required />);
    expect(screen.getByLabelText(/Full name/)).toBeRequired();
  });

  it("supports the render-prop form for custom controls", () => {
    render(
      <Field label="Availability" error="Pick a date">
        {({ id, describedBy, invalid }) => (
          <input id={id} aria-describedby={describedBy} aria-invalid={invalid} type="date" />
        )}
      </Field>,
    );
    expect(screen.getByLabelText(/Availability/)).toHaveAttribute("aria-invalid", "true");
  });
});

describe("Badge", () => {
  it("renders its content", () => {
    render(<Badge tone="success">Shortlisted</Badge>);
    expect(screen.getByText("Shortlisted")).toBeInTheDocument();
  });
});

describe("ErrorState", () => {
  it("shows the API message and code, and offers a retry", async () => {
    const onRetry = vi.fn();
    render(
      <ErrorState
        error={new ApiError(403, "FORBIDDEN", "You do not have access to this posting.")}
        onRetry={onRetry}
      />,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("You do not have access to this posting.")).toBeInTheDocument();
    expect(screen.getByText("FORBIDDEN")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("falls back to a generic message for a non-API failure", () => {
    render(<ErrorState error={"boom"} />);
    expect(screen.getByText("Something went wrong.")).toBeInTheDocument();
  });
});

describe("EmptyState", () => {
  it("renders a title, description and action", () => {
    render(
      <EmptyState
        title="No applications yet"
        description="Apply to an internship to see it here."
        action={<Button>Browse internships</Button>}
      />,
    );
    expect(screen.getByText("No applications yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Browse internships" })).toBeInTheDocument();
  });
});

describe("QueryState", () => {
  const children = (rows: string[]) => <ul>{rows.map((r) => <li key={r}>{r}</li>)}</ul>;

  it("renders the loading placeholder first", () => {
    const { container } = render(
      <QueryState isLoading error={null} data={undefined}>
        {children}
      </QueryState>,
    );
    expect(container.querySelector(".animate-pulse")).toBeTruthy();
  });

  it("prefers the error state over stale data", () => {
    render(
      <QueryState isLoading={false} error={new Error("network down")} data={["stale"]}>
        {children}
      </QueryState>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.queryByText("stale")).not.toBeInTheDocument();
  });

  it("renders the empty state for an empty collection", () => {
    render(
      <QueryState
        isLoading={false}
        error={null}
        data={[]}
        isEmpty={(rows) => rows.length === 0}
        empty={<EmptyState title="No matches yet" />}
      >
        {children}
      </QueryState>,
    );
    expect(screen.getByText("No matches yet")).toBeInTheDocument();
  });

  it("renders data once it arrives", () => {
    render(
      <QueryState isLoading={false} error={null} data={["Backend Intern", "Data Analyst"]}>
        {children}
      </QueryState>,
    );
    expect(screen.getByText("Backend Intern")).toBeInTheDocument();
    expect(screen.getByText("Data Analyst")).toBeInTheDocument();
  });

  it("never renders nothing — undefined data still produces an empty state", () => {
    const { container } = render(
      <QueryState isLoading={false} error={null} data={undefined}>
        {children}
      </QueryState>,
    );
    expect(container.textContent?.trim()).not.toBe("");
  });
});

describe("Card", () => {
  it("composes a header, body and footer", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Backend Intern</CardTitle>
          <CardDescription>Nimbus Labs · Pune</CardDescription>
        </CardHeader>
        <CardContent>Six-month internship.</CardContent>
        <CardFooter>
          <Button size="sm">View</Button>
        </CardFooter>
      </Card>,
    );

    expect(screen.getByRole("heading", { name: "Backend Intern" })).toBeInTheDocument();
    expect(screen.getByText("Nimbus Labs · Pune")).toBeInTheDocument();
    expect(screen.getByText("Six-month internship.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View" })).toBeInTheDocument();
  });
});

describe("Textarea, Select and Checkbox", () => {
  it("labels a textarea and accepts input", async () => {
    render(<Textarea label="Cover note" hint="Optional" />);
    const field = screen.getByLabelText(/Cover note/);
    await userEvent.type(field, "I have shipped two backend projects.");
    expect(field).toHaveValue("I have shipped two backend projects.");
  });

  it("marks an invalid textarea for assistive technology", () => {
    render(<Textarea label="Cover note" error="Too long" />);
    expect(screen.getByLabelText(/Cover note/)).toHaveAttribute("aria-invalid", "true");
  });

  it("labels a select and reports the chosen option", async () => {
    render(
      <Select label="Work mode" defaultValue="">
        <option value="">Any</option>
        <option value="REMOTE">Remote</option>
        <option value="ONSITE">On-site</option>
      </Select>,
    );
    const select = screen.getByLabelText(/Work mode/);
    await userEvent.selectOptions(select, "REMOTE");
    expect(select).toHaveValue("REMOTE");
  });

  it("links a checkbox to its label and its description", async () => {
    const onChange = vi.fn();
    render(
      <Checkbox
        label="I accept the terms of use"
        description="Your documents stay private until you share them."
        onChange={onChange}
      />,
    );

    const checkbox = screen.getByLabelText("I accept the terms of use");
    expect(checkbox).not.toBeChecked();
    await userEvent.click(checkbox);
    expect(checkbox).toBeChecked();
    expect(onChange).toHaveBeenCalled();
    expect(screen.getByText(/documents stay private/)).toBeInTheDocument();
  });
});
