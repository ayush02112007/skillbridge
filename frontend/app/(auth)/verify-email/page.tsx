import type { Metadata } from "next";
import { Suspense } from "react";

import { VerifyEmailPanel } from "@/features/auth/password-reset-forms";

export const metadata: Metadata = {
  title: "Verify your email",
  description: "Confirm your email address to finish setting up your account.",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export default function VerifyEmailPage() {
  return (
    <Suspense>
      <VerifyEmailPanel />
    </Suspense>
  );
}
