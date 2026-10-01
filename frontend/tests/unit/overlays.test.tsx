/**
 * Overlay and navigation primitives.
 *
 * These are the components where an accessibility regression is invisible in a
 * screenshot: a dialog that lets focus escape, tabs that only the mouse can
 * reach, a tooltip that cannot be dismissed from the keyboard.
 */
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Stat } from "@/components/ui/stat";
import { Table, TableWrapper, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip } from "@/components/ui/tooltip";

describe("Avatar", () => {
  it("renders the image with the person's name as its alt text", () => {
    render(<Avatar name="Ananya Raghavan" src="https://example.test/a.png" />);
    expect(screen.getByRole("img", { name: "Ananya Raghavan" })).toBeInTheDocument();
  });

  it("falls back to initials, hidden from screen readers to avoid a stray 'AR'", () => {
    const { container } = render(<Avatar name="Ananya Raghavan" />);
    const fallback = container.querySelector("span");
    expect(fallback).toHaveTextContent("AR");
    expect(fallback).toHaveAttribute("aria-hidden");
  });
});

describe("Stat", () => {
  it("shows the label, value and sublabel", () => {
    render(<Stat label="Applications" value={12} sublabel="3 shortlisted" />);
    expect(screen.getByText("Applications")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("3 shortlisted")).toBeInTheDocument();
  });

  it("renders a trend in the direction it points", () => {
    const { rerender } = render(<Stat label="Placements" value={40} trend={{ value: 12, label: "vs last year" }} />);
    expect(screen.getByText(/12%\s*vs last year/)).toBeInTheDocument();

    rerender(<Stat label="Placements" value={40} trend={{ value: -8 }} />);
    // The sign is conveyed by the icon and colour; the figure itself is absolute.
    expect(screen.getByText("8%")).toBeInTheDocument();
  });
});

describe("Table", () => {
  it("renders a semantic table", () => {
    render(
      <TableWrapper>
        <Table>
          <THead>
            <TR>
              <TH>Student</TH>
              <TH>Status</TH>
            </TR>
          </THead>
          <TBody>
            <TR>
              <TD>Ravi Menon</TD>
              <TD>Shortlisted</TD>
            </TR>
          </TBody>
        </Table>
      </TableWrapper>,
    );

    const table = screen.getByRole("table");
    expect(within(table).getByRole("columnheader", { name: "Student" })).toBeInTheDocument();
    expect(within(table).getAllByRole("row")).toHaveLength(2);
    expect(within(table).getByRole("cell", { name: "Ravi Menon" })).toBeInTheDocument();
  });
});

describe("Tabs", () => {
  function Example() {
    return (
      <Tabs defaultValue="overview">
        <TabsList ariaLabel="Application sections">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="skills">Skills</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
        </TabsList>
        <TabsContent value="overview">Overview panel</TabsContent>
        <TabsContent value="skills">Skills panel</TabsContent>
        <TabsContent value="timeline">Timeline panel</TabsContent>
      </Tabs>
    );
  }

  it("shows only the selected panel", async () => {
    render(<Example />);
    expect(screen.getByText("Overview panel")).toBeInTheDocument();
    expect(screen.queryByText("Skills panel")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("tab", { name: "Skills" }));
    expect(screen.getByText("Skills panel")).toBeInTheDocument();
    expect(screen.queryByText("Overview panel")).not.toBeInTheDocument();
  });

  it("links each tab to its panel", () => {
    render(<Example />);
    const tab = screen.getByRole("tab", { name: "Overview" });
    const panel = screen.getByRole("tabpanel");
    expect(tab).toHaveAttribute("aria-selected", "true");
    expect(tab.getAttribute("aria-controls")).toBe(panel.getAttribute("id"));
    expect(panel.getAttribute("aria-labelledby")).toBe(tab.getAttribute("id"));
  });

  it("keeps only the selected tab in the tab order", () => {
    render(<Example />);
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("tab", { name: "Skills" })).toHaveAttribute("tabindex", "-1");
  });

  it("moves between tabs with the arrow keys, wrapping at both ends", async () => {
    render(<Example />);
    screen.getByRole("tab", { name: "Overview" }).focus();

    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Skills" })).toHaveFocus();
    expect(screen.getByText("Skills panel")).toBeInTheDocument();

    await userEvent.keyboard("{ArrowLeft}{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "Timeline" })).toHaveFocus();

    await userEvent.keyboard("{Home}");
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveFocus();

    await userEvent.keyboard("{End}");
    expect(screen.getByRole("tab", { name: "Timeline" })).toHaveFocus();
  });
});

describe("Tooltip", () => {
  it("shows on focus, not only on hover, and describes its trigger", async () => {
    render(
      <Tooltip content="Skill compatibility — decision support only">
        <button type="button">Match</button>
      </Tooltip>,
    );

    await userEvent.tab();
    const tooltip = await screen.findByRole("tooltip");
    expect(tooltip).toHaveTextContent("decision support only");
    expect(screen.getByText("Match").parentElement).toHaveAttribute(
      "aria-describedby",
      tooltip.getAttribute("id"),
    );
  });

  it("can be dismissed with Escape without moving focus", async () => {
    render(
      <Tooltip content="Explains the score">
        <button type="button">Match</button>
      </Tooltip>,
    );

    await userEvent.tab();
    expect(await screen.findByRole("tooltip")).toBeInTheDocument();

    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("tooltip")).not.toBeInTheDocument());
    expect(screen.getByText("Match")).toHaveFocus();
  });
});

describe("Dialog", () => {
  function Example({ onClose = () => {} }: { onClose?: () => void }) {
    const [open, setOpen] = useState(true);
    return (
      <Dialog
        open={open}
        onClose={() => {
          setOpen(false);
          onClose();
        }}
        title="Apply: Backend Intern"
        description="Your application includes your skill profile."
        footer={<Button>Submit application</Button>}
      >
        <p>Cover note goes here.</p>
      </Dialog>
    );
  }

  it("is labelled and described by its own header", () => {
    render(<Example />);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAccessibleName("Apply: Backend Intern");
    expect(dialog).toHaveAccessibleDescription("Your application includes your skill profile.");
  });

  it("moves focus into the panel when it opens", async () => {
    render(<Example />);
    const dialog = screen.getByRole("dialog");
    await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));
  });

  it("closes on Escape", async () => {
    const onClose = vi.fn();
    render(<Example onClose={onClose} />);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("closes from the close button and from the backdrop", async () => {
    const onClose = vi.fn();
    const { unmount } = render(<Example onClose={onClose} />);
    await userEvent.click(screen.getByRole("button", { name: "Close dialog" }));
    expect(onClose).toHaveBeenCalledTimes(1);
    unmount();

    const second = vi.fn();
    render(<Example onClose={second} />);
    await userEvent.click(document.querySelector("[aria-hidden].absolute")!);
    expect(second).toHaveBeenCalledTimes(1);
  });

  it("locks background scroll while open and restores it on close", async () => {
    render(<Example />);
    expect(document.body.style.overflow).toBe("hidden");
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(document.body.style.overflow).toBe(""));
  });

  it("wraps focus at the end of the panel instead of leaving it", async () => {
    render(<Example />);
    const dialog = screen.getByRole("dialog");
    await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));

    for (let index = 0; index < 8; index += 1) await userEvent.tab();
    expect(dialog.contains(document.activeElement)).toBe(true);
  });
});
