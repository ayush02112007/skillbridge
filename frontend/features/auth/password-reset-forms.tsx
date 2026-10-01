"use client";

/**
 * The two halves of a password reset, plus email verification.
 *
 * `/reset-password` and `/verify-email` are the destinations the backend puts
 * in its emails (see backend/app/services/auth.py), so their paths and the
 * `token` query parameter are a contract, not a choice.
 */
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, CheckCircle2, Lock, Mail, XCircle } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

// Mirrors the server-side policy so users get feedback before submitting.
const passwordSchema = z
  .string()
  .min(10, "At least 10 characters")
  .max(128, "At most 128 characters")
  .regex(/[a-z]/, "Include a lowercase letter")
  .regex(/[A-Z]/, "Include an uppercase letter")
  .regex(/\d/, "Include a digit")
  .regex(/[^a-zA-Z0-9]/, "Include a symbol");

function PasswordRules({ password }: { password: string }) {
  const rules = [
    { label: "10+ characters", ok: password.length >= 10 },
    { label: "Upper & lowercase", ok: /[a-z]/.test(password) && /[A-Z]/.test(password) },
    { label: "A digit", ok: /\d/.test(password) },
    { label: "A symbol", ok: /[^a-zA-Z0-9]/.test(password) },
  ];
  return (
    <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
      {rules.map((rule) => (
        <li
          key={rule.label}
          className={cn("flex items-center gap-1 text-xs", rule.ok ? "text-success-700" : "text-ink-400")}
        >
          <span
            className={cn("size-1.5 rounded-full", rule.ok ? "bg-success-500" : "bg-ink-300")}
            aria-hidden
          />
          {rule.label}
        </li>
      ))}
    </ul>
  );
}

function BackToSignIn() {
  return (
    <Link
      href="/login"
      className="mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-brand-700 hover:underline"
    >
      <ArrowLeft className="size-4" aria-hidden />
      Back to sign in
    </Link>
  );
}

// ------------------------------------------------------------ request a link
const forgotSchema = z.object({
  email: z.string().min(1, "Enter your email").email("Enter a valid email address"),
});

export function ForgotPasswordForm() {
  const [sentTo, setSentTo] = useState<string | null>(null);
  const {
    register, handleSubmit, formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof forgotSchema>>({ resolver: zodResolver(forgotSchema) });

  const onSubmit = handleSubmit(async (values) => {
    // The API answers identically for known and unknown addresses so that this
    // form cannot be used to discover who has an account. The UI must not leak
    // the difference either, so there is no "no such user" branch here.
    await api.post("/auth/forgot-password", { email: values.email }, { anonymous: true });
    setSentTo(values.email);
  });

  if (sentTo) {
    return (
      <div>
        <div className="flex size-11 items-center justify-center rounded-full bg-success-50 text-success-600">
          <Mail className="size-5" aria-hidden />
        </div>
        <h1 className="mt-4 text-2xl">Check your inbox</h1>
        <p className="mt-2 text-sm leading-relaxed text-ink-600">
          If <span className="font-medium text-ink-900">{sentTo}</span> is registered, a reset
          link is on its way. It expires in 60 minutes and can be used once.
        </p>
        <p className="mt-3 text-sm text-ink-500">
          Nothing arrived?{" "}
          <button
            type="button"
            onClick={() => setSentTo(null)}
            className="font-medium text-brand-700 hover:underline"
          >
            Try a different address
          </button>
          .
        </p>
        <BackToSignIn />
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl">Reset your password</h1>
      <p className="mt-1.5 text-sm text-ink-500">
        Enter the email you signed up with and we will send you a link.
      </p>

      <form onSubmit={onSubmit} className="mt-7 space-y-4" noValidate>
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@example.edu"
          leftIcon={<Mail />}
          error={errors.email?.message}
          required
          {...register("email")}
        />
        <Button type="submit" block size="lg" isLoading={isSubmitting}>
          Send reset link
        </Button>
      </form>

      <BackToSignIn />
    </div>
  );
}

// ------------------------------------------------------------- set a new one
const resetSchema = z
  .object({
    new_password: passwordSchema,
    confirm_password: z.string().min(1, "Confirm your new password"),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    path: ["confirm_password"],
    message: "Passwords do not match",
  });

export function ResetPasswordForm() {
  const params = useSearchParams();
  const router = useRouter();
  const token = params.get("token") ?? "";
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register, handleSubmit, watch, formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof resetSchema>>({ resolver: zodResolver(resetSchema) });

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    try {
      await api.post(
        "/auth/reset-password",
        { token, new_password: values.new_password },
        { anonymous: true },
      );
      toast.success("Password updated. Please sign in.");
      router.push("/login");
    } catch (error) {
      setFormError(
        error instanceof ApiError
          ? (Object.values(error.fieldErrors)[0] ?? error.message)
          : "Could not reset your password.",
      );
    }
  });

  if (!token) {
    return (
      <div>
        <div className="flex size-11 items-center justify-center rounded-full bg-danger-50 text-danger-600">
          <XCircle className="size-5" aria-hidden />
        </div>
        <h1 className="mt-4 text-2xl">This link is incomplete</h1>
        <p className="mt-2 text-sm leading-relaxed text-ink-600">
          Open the link exactly as it appears in the email, or request a new one.
        </p>
        <Link href="/forgot-password" className="mt-5 inline-block">
          <Button>Request a new link</Button>
        </Link>
        <BackToSignIn />
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl">Choose a new password</h1>
      <p className="mt-1.5 text-sm text-ink-500">
        Setting a new password signs out every other device.
      </p>

      <form onSubmit={onSubmit} className="mt-7 space-y-4" noValidate>
        {formError && (
          <div
            role="alert"
            className="rounded-lg border border-danger-500/25 bg-danger-50 px-3 py-2.5 text-sm text-danger-700"
          >
            {formError}
          </div>
        )}

        <div>
          <Input
            label="New password"
            type="password"
            autoComplete="new-password"
            placeholder="••••••••••"
            leftIcon={<Lock />}
            error={errors.new_password?.message}
            required
            {...register("new_password")}
          />
          <PasswordRules password={watch("new_password") ?? ""} />
        </div>

        <Input
          label="Confirm new password"
          type="password"
          autoComplete="new-password"
          placeholder="••••••••••"
          leftIcon={<Lock />}
          error={errors.confirm_password?.message}
          required
          {...register("confirm_password")}
        />

        <Button type="submit" block size="lg" isLoading={isSubmitting}>
          Update password
        </Button>
      </form>

      <BackToSignIn />
    </div>
  );
}

// ------------------------------------------------------------ verify email
type VerifyState = "verifying" | "verified" | "failed";

export function VerifyEmailPanel() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [state, setState] = useState<VerifyState>(token ? "verifying" : "failed");
  const [message, setMessage] = useState<string>(
    token ? "" : "This link is missing its verification token.",
  );
  // React 18+ runs effects twice in development; the token is single-use.
  const attempted = useRef(false);

  useEffect(() => {
    if (!token || attempted.current) return;
    attempted.current = true;
    api
      .post<{ message: string }>("/auth/verify-email", { token }, { anonymous: true })
      .then(() => setState("verified"))
      .catch((error: unknown) => {
        setState("failed");
        setMessage(
          error instanceof ApiError
            ? error.message
            : "We could not verify this address.",
        );
      });
  }, [token]);

  if (state === "verifying") {
    return (
      <div>
        <div className="size-11 animate-pulse rounded-full bg-ink-100" aria-hidden />
        <h1 className="mt-4 text-2xl">Verifying your email…</h1>
        <p className="mt-2 text-sm text-ink-500" role="status">
          This only takes a moment.
        </p>
      </div>
    );
  }

  if (state === "verified") {
    return (
      <div>
        <div className="flex size-11 items-center justify-center rounded-full bg-success-50 text-success-600">
          <CheckCircle2 className="size-5" aria-hidden />
        </div>
        <h1 className="mt-4 text-2xl">Email verified</h1>
        <p className="mt-2 text-sm leading-relaxed text-ink-600">
          Your address is confirmed. You can sign in now.
        </p>
        <Link href="/login" className="mt-5 inline-block">
          <Button size="lg">Go to sign in</Button>
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="flex size-11 items-center justify-center rounded-full bg-danger-50 text-danger-600">
        <XCircle className="size-5" aria-hidden />
      </div>
      <h1 className="mt-4 text-2xl">We could not verify this link</h1>
      <p className="mt-2 text-sm leading-relaxed text-ink-600" role="alert">
        {message} Verification links expire after 48 hours and work only once.
      </p>
      <ResendVerification />
      <BackToSignIn />
    </div>
  );
}

function ResendVerification() {
  const [sent, setSent] = useState(false);
  const {
    register, handleSubmit, formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof forgotSchema>>({ resolver: zodResolver(forgotSchema) });

  const onSubmit = handleSubmit(async (values) => {
    await api.post("/auth/resend-verification", { email: values.email }, { anonymous: true });
    setSent(true);
  });

  if (sent) {
    return (
      <p className="mt-5 rounded-lg border border-ink-200 bg-surface-muted px-3 py-2.5 text-sm text-ink-600">
        If that address needs verifying, a new link is on its way.
      </p>
    );
  }

  return (
    <form onSubmit={onSubmit} className="mt-6 space-y-3" noValidate>
      <Input
        label="Send a new link to"
        type="email"
        autoComplete="email"
        placeholder="you@example.edu"
        leftIcon={<Mail />}
        error={errors.email?.message}
        required
        {...register("email")}
      />
      <Button type="submit" variant="secondary" block isLoading={isSubmitting}>
        Resend verification email
      </Button>
    </form>
  );
}
