"use client";

import {
  ChevronDown, Compass, LogOut, Menu, Search, Settings, User, X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { CommandPalette, useCommandPalette } from "@/components/layout/command-palette";
import { navForRoles, type NavSection } from "@/components/layout/nav-config";
import { NotificationMenu } from "@/components/layout/notification-menu";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth";
import { APP_NAME, ROLE_LABELS } from "@/lib/constants";
import { cn } from "@/lib/utils";

function SidebarNav({
  sections,
  pathname,
  onNavigate,
}: {
  sections: NavSection[];
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4" aria-label="Main">
      {sections.map((section, index) => (
        <div key={section.title ?? index}>
          {section.title && (
            <p
              id={`nav-group-${index}`}
              className="mb-1.5 px-3 text-2xs font-semibold uppercase tracking-wide text-ink-400"
            >
              {section.title}
            </p>
          )}
          <ul
            className="space-y-0.5"
            role={section.title ? "group" : undefined}
            aria-labelledby={section.title ? `nav-group-${index}` : undefined}
          >
            {section.items.map((item) => {
              const active =
                pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors [&_svg]:size-4",
                      active
                        ? "bg-brand-50 font-medium text-brand-800"
                        : "text-ink-600 hover:bg-ink-100 hover:text-ink-900",
                    )}
                  >
                    <span className={active ? "text-brand-700" : "text-ink-400"} aria-hidden>
                      {item.icon}
                    </span>
                    <span className="truncate">{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

function UserMenu() {
  const { session, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (event: MouseEvent) => {
      if (!ref.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  if (!session) return null;
  const primaryRole = session.roles[0];

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label="Account menu"
        aria-expanded={open}
        aria-haspopup="menu"
        className="flex items-center gap-2 rounded-lg p-1 pr-2 transition-colors hover:bg-ink-100"
      >
        <Avatar name={session.user.full_name} src={session.user.avatar_url} size="sm" />
        <span className="hidden text-left sm:block">
          <span className="block max-w-[10rem] truncate text-sm font-medium leading-tight text-ink-900">
            {session.user.full_name}
          </span>
          <span className="block text-2xs leading-tight text-ink-500">
            {ROLE_LABELS[primaryRole]}
          </span>
        </span>
        <ChevronDown className="size-4 shrink-0 text-ink-400" aria-hidden />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-2 w-60 animate-slide-up overflow-hidden rounded-xl border border-ink-200 bg-surface shadow-popover"
        >
          <div className="border-b border-ink-100 px-4 py-3">
            <p className="truncate text-sm font-medium text-ink-900">
              {session.user.full_name}
            </p>
            <p className="truncate text-xs text-ink-500">{session.user.email}</p>
            <div className="mt-2 flex flex-wrap gap-1">
              {session.roles.map((role) => (
                <Badge key={role} tone="brand">{ROLE_LABELS[role]}</Badge>
              ))}
            </div>
          </div>
          <div className="p-1">
            <Link
              href={`${session.home_route.split("/").slice(0, 2).join("/")}/profile`}
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-ink-700 transition-colors hover:bg-ink-50 [&_svg]:size-4"
            >
              <User className="text-ink-400" aria-hidden />
              My profile
            </Link>
            <Link
              href={`${session.home_route.split("/").slice(0, 2).join("/")}/settings`}
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-ink-700 transition-colors hover:bg-ink-50 [&_svg]:size-4"
            >
              <Settings className="text-ink-400" aria-hidden />
              Settings
            </Link>
            <button
              type="button"
              onClick={() => void logout()}
              className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-danger-700 transition-colors hover:bg-danger-50 [&_svg]:size-4"
            >
              <LogOut aria-hidden />
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const { session } = useAuth();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { open: paletteOpen, setOpen: setPaletteOpen } = useCommandPalette();

  const sections = navForRoles(session?.roles ?? []);
  const primaryItems = sections
    .flatMap((section) => section.items)
    .filter((item) => item.primary)
    .slice(0, 5);

  useEffect(() => setMobileOpen(false), [pathname]);

  return (
    <div className="min-h-dvh bg-surface-muted">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col border-r border-ink-200 bg-surface lg:flex">
        <div className="flex h-16 shrink-0 items-center gap-2.5 border-b border-ink-100 px-5">
          <span className="flex size-8 items-center justify-center rounded-lg bg-brand-700 text-white">
            <Compass className="size-4" aria-hidden />
          </span>
          <span className="text-[17px] font-semibold tracking-tight text-ink-950">
            {APP_NAME}
          </span>
        </div>
        <SidebarNav sections={sections} pathname={pathname} />
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 animate-fade-in bg-canvas/60"
            onClick={() => setMobileOpen(false)}
            aria-hidden
          />
          <aside className="relative flex h-full w-72 max-w-[85vw] animate-slide-up flex-col bg-surface">
            <div className="flex h-16 shrink-0 items-center justify-between border-b border-ink-100 px-4">
              <span className="flex items-center gap-2.5">
                <span className="flex size-8 items-center justify-center rounded-lg bg-brand-700 text-white">
                  <Compass className="size-4" aria-hidden />
                </span>
                <span className="text-[17px] font-semibold text-ink-950">{APP_NAME}</span>
              </span>
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                aria-label="Close navigation"
                className="rounded-lg p-2 text-ink-500 hover:bg-ink-100"
              >
                <X className="size-5" />
              </button>
            </div>
            <SidebarNav
              sections={sections}
              pathname={pathname}
              onNavigate={() => setMobileOpen(false)}
            />
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 border-b border-ink-200 bg-surface/90 backdrop-blur-md">
          <div className="flex h-16 items-center gap-3 px-4 sm:px-6">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation"
              className="rounded-lg p-2 text-ink-600 hover:bg-ink-100 lg:hidden"
            >
              <Menu className="size-5" />
            </button>

            <button
              type="button"
              onClick={() => setPaletteOpen(true)}
              className="flex h-9 flex-1 items-center gap-2.5 rounded-lg border border-ink-200 bg-surface-muted px-3 text-left text-sm text-ink-400 transition-colors hover:border-ink-300 hover:bg-surface sm:max-w-md"
            >
              <Search className="size-4 shrink-0" aria-hidden />
              <span className="flex-1 truncate">Search everything…</span>
              <kbd className="hidden shrink-0 rounded border border-ink-200 bg-surface px-1.5 py-0.5 font-mono text-2xs text-ink-500 sm:block">
                ⌘K
              </kbd>
            </button>

            <div className="ml-auto flex items-center gap-1">
              <ThemeToggle />
              <NotificationMenu />
              <UserMenu />
            </div>
          </div>
        </header>

        <main id="main" className="px-4 pb-24 pt-6 sm:px-6 lg:pb-10">
          {children}
        </main>
      </div>

      {/* Mobile bottom navigation for the most-used destinations. */}
      <nav
        aria-label="Quick navigation"
        className="fixed inset-x-0 bottom-0 z-20 border-t border-ink-200 bg-surface/95 backdrop-blur-md lg:hidden"
      >
        <ul className="grid grid-cols-5">
          {primaryItems.map((item) => {
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex flex-col items-center gap-0.5 px-1 py-2.5 text-2xs [&_svg]:size-5",
                    active ? "text-brand-700" : "text-ink-500",
                  )}
                >
                  {item.icon}
                  <span className="max-w-full truncate">
                    {item.label.split(" ")[0]}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  );
}
