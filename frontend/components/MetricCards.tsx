import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Card } from "./ui/Card";
import { cx } from "@/lib/format";

export interface Metric {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "default" | "good" | "warn" | "bad";
  icon?: LucideIcon;
}

const TONES: Record<NonNullable<Metric["tone"]>, string> = {
  default: "text-slate-100",
  good: "text-emerald-300",
  warn: "text-amber-300",
  bad: "text-red-300",
};

/** Grid of compact operational stat cards. */
export function MetricCards({
  metrics,
  columns = 4,
}: {
  metrics: Metric[];
  columns?: 2 | 3 | 4 | 5 | 6;
}) {
  const colClass = {
    2: "sm:grid-cols-2",
    3: "sm:grid-cols-3",
    4: "sm:grid-cols-2 lg:grid-cols-4",
    5: "sm:grid-cols-3 lg:grid-cols-5",
    6: "sm:grid-cols-3 lg:grid-cols-6",
  }[columns];

  return (
    <div className={cx("grid grid-cols-1 gap-3", colClass)}>
      {metrics.map((m, index) => (
        <Card key={m.label} className={cx("rise-in p-4", `stagger-${Math.min(index + 1, 4)}`)}>
          <div className="flex items-start justify-between gap-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
              {m.label}
            </p>
            {m.icon ? (
              <m.icon size={16} className="text-cyan-300/70" aria-hidden="true" />
            ) : null}
          </div>
          <p
            className={cx(
              "mt-2 text-2xl font-semibold tabular-nums tracking-tight",
              TONES[m.tone ?? "default"],
            )}
          >
            {m.value}
          </p>
          {m.hint ? (
            <p className="mt-0.5 text-xs text-slate-500">{m.hint}</p>
          ) : null}
        </Card>
      ))}
    </div>
  );
}
