"use client";

import { createContext, useContext, useId, useState } from "react";

import { cn } from "@/lib/utils";

interface TabsContextValue {
  value: string;
  setValue: (value: string) => void;
  baseId: string;
}

const TabsContext = createContext<TabsContextValue | null>(null);

export function Tabs({
  defaultValue,
  value: controlled,
  onValueChange,
  children,
  className,
}: {
  defaultValue: string;
  value?: string;
  onValueChange?: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}) {
  const [internal, setInternal] = useState(defaultValue);
  const baseId = useId();
  const value = controlled ?? internal;
  const setValue = (next: string) => {
    if (controlled === undefined) setInternal(next);
    onValueChange?.(next);
  };
  return (
    <TabsContext.Provider value={{ value, setValue, baseId }}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  );
}

function useTabs() {
  const context = useContext(TabsContext);
  if (!context) throw new Error("Tabs components must be used inside <Tabs>");
  return context;
}

export function TabsList({
  children,
  className,
  ariaLabel,
}: {
  children: React.ReactNode;
  className?: string;
  ariaLabel?: string;
}) {
  /**
   * Triggers use a roving tabindex (only the selected tab is in the tab order),
   * so the arrow keys have to move between them — otherwise the unselected
   * tabs are unreachable by keyboard altogether.
   */
  const onKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const keys = ["ArrowRight", "ArrowLeft", "Home", "End"];
    if (!keys.includes(event.key)) return;

    const tabs = Array.from(
      event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]:not([disabled])'),
    );
    if (tabs.length < 2) return;

    const current = tabs.indexOf(document.activeElement as HTMLButtonElement);
    const from = current === -1 ? tabs.findIndex((tab) => tab.getAttribute("aria-selected") === "true") : current;
    const next = {
      ArrowRight: (from + 1) % tabs.length,
      ArrowLeft: (from - 1 + tabs.length) % tabs.length,
      Home: 0,
      End: tabs.length - 1,
    }[event.key]!;

    event.preventDefault();
    // Follows the selection, which is the expected behaviour for tab panels
    // that are cheap to render.
    tabs[next].focus();
    tabs[next].click();
  };

  return (
    <div
      role="tablist"
      aria-label={ariaLabel ?? "Sections"}
      onKeyDown={onKeyDown}
      className={cn(
        "inline-flex items-center gap-1 overflow-x-auto rounded-xl bg-ink-100 p-1",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function TabsTrigger({
  value,
  children,
  className,
}: {
  value: string;
  children: React.ReactNode;
  className?: string;
}) {
  const { value: active, setValue, baseId } = useTabs();
  const selected = active === value;
  return (
    <button
      type="button"
      role="tab"
      id={`${baseId}-tab-${value}`}
      aria-selected={selected}
      aria-controls={`${baseId}-panel-${value}`}
      tabIndex={selected ? 0 : -1}
      onClick={() => setValue(value)}
      className={cn(
        "whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600",
        selected
          ? "bg-surface text-ink-900 shadow-card"
          : "text-ink-600 hover:text-ink-900",
        className,
      )}
    >
      {children}
    </button>
  );
}

export function TabsContent({
  value,
  children,
  className,
}: {
  value: string;
  children: React.ReactNode;
  className?: string;
}) {
  const { value: active, baseId } = useTabs();
  if (active !== value) return null;
  return (
    <div
      role="tabpanel"
      id={`${baseId}-panel-${value}`}
      aria-labelledby={`${baseId}-tab-${value}`}
      tabIndex={0}
      className={cn("mt-4 focus-visible:outline-none", className)}
    >
      {children}
    </div>
  );
}
