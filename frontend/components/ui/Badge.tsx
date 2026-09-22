import type { ReactNode } from "react";
import { cx } from "@/lib/format";

interface BadgeProps {
  children: ReactNode;
  className?: string;
  title?: string;
}

/** Generic pill badge. Callers pass color classes via className. */
export function Badge({ children, className, title }: BadgeProps) {
  return (
    <span
      title={title}
      className={cx(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
        className ?? "border-surface-border bg-surface-panel text-slate-300",
      )}
    >
      {children}
    </span>
  );
}
