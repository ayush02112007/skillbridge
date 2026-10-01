"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronRight, Lock, Mail } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { DEMO_ACCOUNTS, DEMO_PASSWORD } from "@/lib/constants";

const schema = z.object({
  email: z.string().min(1, "Enter your email").email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password"),
});

type FormValues = z.infer<typeof schema>;

export function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register, handleSubmit, setValue, formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setFormError(null);
    try {
      const session = await login(values.email, values.password);
      toast.success(`Welcome back, ${session.user.full_name.split(" ")[0]}`);
      router.push(params.get("next") ?? session.home_route);
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "Could not sign you in.";
      setFormError(message);
    }
  };

  const useDemoAccount = (email: string) => {
    setValue("email", email, { shouldValidate: true });
    setValue("password", DEMO_PASSWORD, { shouldValidate: true });
  };

  return (
    <div>
      <h1 className="text-2xl">Sign in</h1>
      <p className="mt-1.5 text-sm text-ink-500">
        New here?{" "}
        <Link href="/register" className="font-medium text-brand-700 hover:underline">
          Create an account
        </Link>
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="mt-7 space-y-4" noValidate>
        {formError && (
          <div
            role="alert"
            className="rounded-lg border border-danger-500/25 bg-danger-50 px-3 py-2.5 text-sm text-danger-700"
          >
            {formError}
          </div>
        )}

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

        <div className="space-y-1.5">
          <Input
            label="Password"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••••"
            leftIcon={<Lock />}
            error={errors.password?.message}
            required
            {...register("password")}
          />
          <div className="text-right">
            <Link
              href="/forgot-password"
              className="text-xs font-medium text-brand-700 hover:underline"
            >
              Forgot password?
            </Link>
          </div>
        </div>

        <Button type="submit" block size="lg" isLoading={isSubmitting}>
          Sign in
        </Button>
      </form>

      {/* Demo accounts are a development convenience and are labelled as such. */}
      <div className="mt-8 rounded-xl border border-ink-200 bg-surface-muted p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">
          Demo accounts
        </p>
        <p className="mt-1 text-xs leading-relaxed text-ink-500">
          Seeded development logins. Selecting one fills the form.
        </p>
        <div className="mt-3 grid gap-1">
          {DEMO_ACCOUNTS.map((account) => (
            <button
              key={account.email}
              type="button"
              onClick={() => useDemoAccount(account.email)}
              className="flex items-center justify-between rounded-lg px-2 py-1.5 text-left text-xs transition-colors hover:bg-surface"
            >
              <span className="font-medium text-ink-800">{account.label}</span>
              <span className="flex items-center gap-1 font-mono text-ink-500">
                {account.email}
                <ChevronRight className="size-3" aria-hidden />
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
