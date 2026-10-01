"use client";

import { forwardRef, useId } from "react";

import { cn } from "@/lib/utils";

const fieldBase =
  "w-full rounded-lg border bg-surface text-sm text-ink-900 placeholder:text-ink-400 " +
  "transition-colors focus:outline-none focus:ring-2 focus:ring-brand-600/30 " +
  "disabled:cursor-not-allowed disabled:bg-ink-50 disabled:text-ink-400";

export interface FieldWrapperProps {
  label?: string;
  hint?: string;
  error?: string;
  required?: boolean;
  id?: string;
  children: (props: { id: string; describedBy?: string; invalid: boolean }) => React.ReactNode;
  className?: string;
}

/** Shared label/hint/error scaffolding so every field is accessible by default. */
export function Field({
  label, hint, error, required, id, children, className,
}: FieldWrapperProps) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  const hintId = hint ? `${fieldId}-hint` : undefined;
  const errorId = error ? `${fieldId}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={cn("space-y-1.5", className)}>
      {label && (
        <label htmlFor={fieldId} className="block text-sm font-medium text-ink-800">
          {label}
          {required && (
            <span className="ml-0.5 text-danger-600" aria-hidden>
              *
            </span>
          )}
        </label>
      )}
      {children({ id: fieldId, describedBy, invalid: Boolean(error) })}
      {hint && !error && (
        <p id={hintId} className="text-xs text-ink-500">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className="text-xs font-medium text-danger-600">
          {error}
        </p>
      )}
    </div>
  );
}

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
  leftIcon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, hint, error, required, leftIcon, id, ...props }, ref) => (
    <Field label={label} hint={hint} error={error} required={required} id={id}>
      {({ id: fieldId, describedBy, invalid }) => (
        <div className="relative">
          {leftIcon && (
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-400 [&_svg]:size-4">
              {leftIcon}
            </span>
          )}
          <input
            ref={ref}
            id={fieldId}
            aria-describedby={describedBy}
            aria-invalid={invalid || undefined}
            required={required}
            className={cn(
              fieldBase,
              "h-10 px-3",
              leftIcon && "pl-9",
              invalid ? "border-danger-500" : "border-ink-200 hover:border-ink-300",
              className,
            )}
            {...props}
          />
        </div>
      )}
    </Field>
  ),
);
Input.displayName = "Input";

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, hint, error, required, id, ...props }, ref) => (
    <Field label={label} hint={hint} error={error} required={required} id={id}>
      {({ id: fieldId, describedBy, invalid }) => (
        <textarea
          ref={ref}
          id={fieldId}
          aria-describedby={describedBy}
          aria-invalid={invalid || undefined}
          required={required}
          className={cn(
            fieldBase,
            "min-h-24 px-3 py-2 leading-relaxed",
            invalid ? "border-danger-500" : "border-ink-200 hover:border-ink-300",
            className,
          )}
          {...props}
        />
      )}
    </Field>
  ),
);
Textarea.displayName = "Textarea";

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  hint?: string;
  error?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, hint, error, required, id, children, ...props }, ref) => (
    <Field label={label} hint={hint} error={error} required={required} id={id}>
      {({ id: fieldId, describedBy, invalid }) => (
        <select
          ref={ref}
          id={fieldId}
          aria-describedby={describedBy}
          aria-invalid={invalid || undefined}
          required={required}
          className={cn(
            fieldBase,
            "h-10 cursor-pointer appearance-none bg-[length:16px] bg-[right_0.75rem_center] bg-no-repeat pl-3 pr-9",
            "bg-[url(\"data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke-width='2' stroke='%2366738f'%3e%3cpath stroke-linecap='round' stroke-linejoin='round' d='m19.5 8.25-7.5 7.5-7.5-7.5'/%3e%3c/svg%3e\")]",
            invalid ? "border-danger-500" : "border-ink-200 hover:border-ink-300",
            className,
          )}
          {...props}
        >
          {children}
        </select>
      )}
    </Field>
  ),
);
Select.displayName = "Select";

export function Checkbox({
  className, label, description, id, ...props
}: React.InputHTMLAttributes<HTMLInputElement> & {
  label: React.ReactNode;
  description?: string;
}) {
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  return (
    <div className="flex items-start gap-2.5">
      <input
        type="checkbox"
        id={fieldId}
        className={cn(
          "mt-0.5 size-4 shrink-0 cursor-pointer rounded border-ink-300 text-brand-700",
          "focus:ring-2 focus:ring-brand-600/30",
          className,
        )}
        {...props}
      />
      <div className="space-y-0.5">
        <label htmlFor={fieldId} className="cursor-pointer text-sm text-ink-800">
          {label}
        </label>
        {description && <p className="text-xs text-ink-500">{description}</p>}
      </div>
    </div>
  );
}
