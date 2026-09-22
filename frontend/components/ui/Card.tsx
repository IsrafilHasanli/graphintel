import type { ReactNode } from "react";
import { cx } from "@/lib/format";

interface CardProps {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article";
}

export function Card({ children, className, as: Tag = "div" }: CardProps) {
  return (
    <Tag
      className={cx(
        "rounded-lg border border-surface-border bg-surface-raised shadow-sm",
        className,
      )}
    >
      {children}
    </Tag>
  );
}

interface CardHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}

export function CardHeader({ title, description, actions }: CardHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-surface-border px-4 py-3">
      <div>
        <h2 className="text-sm font-semibold text-slate-100">{title}</h2>
        {description ? (
          <p className="mt-0.5 text-xs text-slate-400">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function CardBody({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cx("p-4", className)}>{children}</div>;
}
