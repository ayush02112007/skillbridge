import type { Metadata } from "next";
import { Suspense } from "react";

import { RegisterForm } from "@/features/auth/register-form";

export const metadata: Metadata = {
  title: "Create an account",
  description: "Join SkillBridge as a student, academician or company.",
};

export default function RegisterPage() {
  return (
    <Suspense>
      <RegisterForm />
    </Suspense>
  );
}
