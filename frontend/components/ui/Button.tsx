import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cx } from "@/lib/format";

type Variant = "primary" | "secondary" | "danger" | "ghost";
type Size = "sm" | "md";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  children: ReactNode;
}

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-brand text-white hover:bg-blue-500 disabled:bg-blue-500/40 border border-transparent",
  secondary:
    "bg-surface-panel text-slate-200 hover:bg-surface-border border border-surface-border",
  danger:
    "bg-red-600 text-white hover:bg-red-500 disabled:bg-red-600/40 border border-transparent",
  ghost: "bg-transparent text-slate-300 hover:bg-surface-panel border border-transparent",
};

const SIZES: Record<Size, string> = {
  sm: "px-2.5 py-1 text-xs",
  md: "px-3.5 py-2 text-sm",
};

export function Button({
  variant = "secondary",
  size = "md",
  loading = false,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-all hover:-translate-y-px hover:shadow-lg",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-surface",
        "disabled:cursor-not-allowed disabled:opacity-70",
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      disabled={disabled || loading}
      aria-busy={loading}
      {...rest}
    >
      {loading ? (
        <span
          className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
          aria-hidden="true"
        />
      ) : null}
      {children}
    </button>
  );
}
