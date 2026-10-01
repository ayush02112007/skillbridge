import type { Metadata } from "next";

import { EventsPage } from "@/features/shared/events-page";

export const metadata: Metadata = { title: "Workshops & Events" };

export default function Page() {
  return <EventsPage />;
}
