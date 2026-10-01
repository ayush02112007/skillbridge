import type { Metadata } from "next";
import { Suspense } from "react";

import { ForgotPasswordForm } from "@/features/auth/password-reset-forms";

export const metadata: Metadata = {
  title: "Reset your password",
  description: "Request a password reset link for your SkillBridge account.",
};

export default function ForgotPasswordPage() {
  return (
    <Suspense>
      <ForgotPasswordForm />
    </Suspense>
  );
}
