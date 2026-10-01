"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { Building2, GraduationCap, Lock, Mail, User } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Checkbox, Input, Select } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";
import { useAuth, type RegisterPayload } from "@/lib/auth";
import { cn } from "@/lib/utils";
import type { Institution, Paged } from "@/types/api";

const ROLE_OPTIONS = [
  {
    value: "STUDENT" as const,
    label: "Student",
    description: "Assess skills, close gaps, find opportunities",
    icon: <GraduationCap />,
  },
  {
    value: "ACADEMICIAN" as const,
    label: "Academician",
    description: "Faculty programmes, research and mentoring",
    icon: <User />,
  },
  {
    value: "INDUSTRY_ADMIN" as const,
    label: "Industry",
    description: "Post roles and find candidates",
    icon: <Building2 />,
  },
];

// Mirrors the server-side policy so users get feedback before submitting.
const passwordSchema = z
  .string()
  .min(10, "At least 10 characters")
  .max(128, "At most 128 characters")
  .regex(/[a-z]/, "Include a lowercase letter")
  .regex(/[A-Z]/, "Include an uppercase letter")
  .regex(/\d/, "Include a digit")
  .regex(/[^a-zA-Z0-9]/, "Include a symbol");

const schema = z
  .object({
    role: z.enum(["STUDENT", "ACADEMICIAN", "INDUSTRY_ADMIN"]),
    full_name: z.string().min(2, "Enter your full name").max(160),
    email: z.string().min(1, "Enter your email").email("Enter a valid email address"),
    password: passwordSchema,
    institution_id: z.string().optional(),
    company_name: z.string().optional(),
    accept_terms: z.literal(true, {
      errorMap: () => ({ message: "You must accept the terms to continue" }),
    }),
  })
  .superRefine((values, ctx) => {
    if (values.role === "INDUSTRY_ADMIN" && !values.company_name?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["company_name"],
        message: "Enter your company name",
      });
    }
  });

type FormValues = z.infer<typeof schema>;

export function RegisterForm() {
  const { register: registerAccount } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [formError, setFormError] = useState<string | null>(null);

  const initialRole =
    (params.get("role") as FormValues["role"] | null) ?? "STUDENT";

  const {
    register, handleSubmit, watch, setValue, formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { role: initialRole, accept_terms: false as unknown as true },
  });

  const role = watch("role");
  const password = watch("password") ?? "";

  const { data: institutions } = useQuery({
    queryKey: ["institutions", "signup"],
    queryFn: () =>
      api.paged<Institution>("/institutions", { page_size: 50 }) as Promise<
        Paged<Institution>
      >,
    enabled: role === "STUDENT" || role === "ACADEMICIAN",
    staleTime: 10 * 60_000,
  });

  const rules = [
    { label: "10+ characters", ok: password.length >= 10 },
    { label: "Upper & lowercase", ok: /[a-z]/.test(password) && /[A-Z]/.test(password) },
    { label: "A digit", ok: /\d/.test(password) },
    { label: "A symbol", ok: /[^a-zA-Z0-9]/.test(password) },
  ];

  const onSubmit = async (values: FormValues) => {
    setFormError(null);
    const payload: RegisterPayload = {
      email: values.email,
      password: values.password,
      full_name: values.full_name,
      role: values.role,
      accept_terms: true,
      ...(values.institution_id ? { institution_id: values.institution_id } : {}),
      ...(values.company_name ? { company_name: values.company_name } : {}),
    };
    try {
      const session = await registerAccount(payload);
      toast.success("Account created. Welcome to SkillBridge.");
      router.push(session.home_route);
    } catch (error) {
      if (error instanceof ApiError) {
        const fields = error.fieldErrors;
        setFormError(
          Object.values(fields)[0] ?? error.message ?? "Could not create your account.",
        );
      } else {
        setFormError("Could not create your account.");
      }
    }
  };

  return (
    <div>
      <h1 className="text-2xl">Create your account</h1>
      <p className="mt-1.5 text-sm text-ink-500">
        Already registered?{" "}
        <Link href="/login" className="font-medium text-brand-700 hover:underline">
          Sign in
        </Link>
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="mt-7 space-y-5" noValidate>
        {formError && (
          <div
            role="alert"
            className="rounded-lg border border-danger-500/25 bg-danger-50 px-3 py-2.5 text-sm text-danger-700"
          >
            {formError}
          </div>
        )}

        <fieldset>
          <legend className="mb-2 block text-sm font-medium text-ink-800">
            I am joining as
          </legend>
          <div className="grid gap-2">
            {ROLE_OPTIONS.map((option) => (
              <label
                key={option.value}
                className={cn(
                  "flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition-colors",
                  role === option.value
                    ? "border-brand-600 bg-brand-50/60 ring-1 ring-brand-600"
                    : "border-ink-200 hover:border-ink-300 hover:bg-ink-50",
                )}
              >
                <input
                  type="radio"
                  value={option.value}
                  className="sr-only"
                  {...register("role")}
                />
                <span
                  className={cn(
                    "mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg [&_svg]:size-4",
                    role === option.value
                      ? "bg-brand-700 text-white"
                      : "bg-ink-100 text-ink-500",
                  )}
                  aria-hidden
                >
                  {option.icon}
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-medium text-ink-900">
                    {option.label}
                  </span>
                  <span className="block text-xs text-ink-500">{option.description}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <Input
          label="Full name"
          placeholder="Aditi Sharma"
          autoComplete="name"
          leftIcon={<User />}
          error={errors.full_name?.message}
          required
          {...register("full_name")}
        />

        <Input
          label="Email"
          type="email"
          placeholder="you@example.edu"
          autoComplete="email"
          leftIcon={<Mail />}
          error={errors.email?.message}
          required
          {...register("email")}
        />

        {(role === "STUDENT" || role === "ACADEMICIAN") && (
          <Select
            label="Institution"
            hint="You can change this later in your profile."
            error={errors.institution_id?.message}
            {...register("institution_id")}
          >
            <option value="">Select your institution</option>
            {institutions?.data.map((institution) => (
              <option key={institution.id} value={institution.id}>
                {institution.name}
                {institution.city ? ` — ${institution.city}` : ""}
              </option>
            ))}
          </Select>
        )}

        {role === "INDUSTRY_ADMIN" && (
          <Input
            label="Company name"
            placeholder="Nimbus Labs"
            hint="This creates your company workspace."
            leftIcon={<Building2 />}
            error={errors.company_name?.message}
            required
            {...register("company_name")}
          />
        )}

        <div>
          <Input
            label="Password"
            type="password"
            autoComplete="new-password"
            placeholder="••••••••••"
            leftIcon={<Lock />}
            error={errors.password?.message}
            required
            {...register("password")}
          />
          <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
            {rules.map((rule) => (
              <li
                key={rule.label}
                className={cn(
                  "flex items-center gap-1 text-xs",
                  rule.ok ? "text-success-700" : "text-ink-400",
                )}
              >
                <span
                  className={cn(
                    "size-1.5 rounded-full",
                    rule.ok ? "bg-success-500" : "bg-ink-300",
                  )}
                  aria-hidden
                />
                {rule.label}
              </li>
            ))}
          </ul>
        </div>

        <Checkbox
          label={
            <>
              I accept the terms of use and privacy policy
            </>
          }
          description="Your documents stay private until you choose to share them."
          {...register("accept_terms")}
        />
        {errors.accept_terms && (
          <p role="alert" className="-mt-3 text-xs font-medium text-danger-600">
            {errors.accept_terms.message}
          </p>
        )}

        <Button type="submit" block size="lg" isLoading={isSubmitting}>
          Create account
        </Button>
      </form>
    </div>
  );
}
