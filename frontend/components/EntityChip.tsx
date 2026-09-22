import Link from "next/link";
import { entityColor } from "@/lib/theme";
import { cx } from "@/lib/format";

interface EntityChipProps {
  type: string;
  label: string;
  /** When set, chip links into the graph explorer seeded on this entity. */
  href?: string;
  title?: string;
  className?: string;
}

/** A colored entity token used in citations, tables, and reasoning paths. */
export function EntityChip({
  type,
  label,
  href,
  title,
  className,
}: EntityChipProps) {
  const color = entityColor(type);
  const inner = (
    <span
      className={cx(
        "inline-flex max-w-full items-center gap-1.5 rounded border border-surface-border bg-surface-panel px-1.5 py-0.5 text-xs",
        href && "hover:border-brand hover:bg-surface-border",
        className,
      )}
      title={title ?? `${type}: ${label}`}
    >
      <span
        className="h-2 w-2 shrink-0 rounded-full"
        style={{ backgroundColor: color }}
        aria-hidden="true"
      />
      <span className="truncate text-slate-200">{label}</span>
      <span className="shrink-0 text-[10px] uppercase tracking-wide text-slate-500">
        {type}
      </span>
    </span>
  );

  if (href) {
    return (
      <Link
        href={href}
        className="focus:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded"
      >
        {inner}
      </Link>
    );
  }
  return inner;
}
