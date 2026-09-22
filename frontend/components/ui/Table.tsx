import type { ReactNode } from "react";
import { cx } from "@/lib/format";

export function Table({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className="overflow-x-auto">
      <table className={cx("w-full border-collapse text-sm", className)}>
        {children}
      </table>
    </div>
  );
}

export function THead({ children }: { children: ReactNode }) {
  return (
    <thead className="border-b border-surface-border text-left text-xs uppercase tracking-wide text-slate-400">
      {children}
    </thead>
  );
}

export function TH({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <th scope="col" className={cx("px-3 py-2 font-medium", className)}>
      {children}
    </th>
  );
}

export function TR({
  children,
  onClick,
  selected,
  className,
}: {
  children: ReactNode;
  onClick?: () => void;
  selected?: boolean;
  className?: string;
}) {
  const interactive = Boolean(onClick);
  return (
    <tr
      onClick={onClick}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      tabIndex={interactive ? 0 : undefined}
      role={interactive ? "button" : undefined}
      className={cx(
        "border-b border-surface-border/60",
        interactive &&
          "cursor-pointer hover:bg-surface-panel focus:bg-surface-panel focus:outline-none",
        selected && "bg-brand/10",
        className,
      )}
    >
      {children}
    </tr>
  );
}

export function TD({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <td className={cx("px-3 py-2 align-top", className)}>{children}</td>;
}
