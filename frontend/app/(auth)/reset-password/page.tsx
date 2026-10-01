import type { Metadata } from "next";
import { Suspense } from "react";

import { ResetPasswordForm } from "@/features/auth/password-reset-forms";

export const metadata: Metadata = {
  title: "Choose a new password",
  description: "Set a new password for your SkillBridge account.",
  // A reset link should never be indexed or forwarded to a referrer.
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  );
}
