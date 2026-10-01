import type { Metadata } from "next";

import { Departments } from "@/features/institution/directory";

export const metadata: Metadata = { title: "Departments" };

export default function Page() {
  return <Departments />;
}
