import type { ReactNode } from "react";
import { Button } from "./Button";

/** Skeleton block used while data loads. */
export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex flex-col items-center justify-center gap-3 px-4 py-12 text-slate-400"
    >
      <span
        className="h-6 w-6 animate-spin rounded-full border-2 border-slate-500 border-t-transparent"
        aria-hidden="true"
      />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function EmptyState({
  title = "Nothing here yet",
  description,
  action,
}: {
  title?: string;
  description?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-4 py-12 text-center">
      <p className="text-sm font-medium text-slate-200">{title}</p>
      {description ? (
        <p className="max-w-md text-xs text-slate-400">{description}</p>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  error,
  onRetry,
}: {
  error: Error | string;
  onRetry?: () => void;
}) {
  const message = typeof error === "string" ? error : error.message;
  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center gap-3 px-4 py-12 text-center"
    >
      <p className="text-sm font-semibold text-red-300">Something went wrong</p>
      <p className="max-w-lg break-words text-xs text-slate-400">{message}</p>
      {onRetry ? (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </div>
  );
}

/**
 * Convenience wrapper: renders loading/error/empty fallbacks and only invokes
 * `children` when data is present.
 */
export function AsyncView<T>({
  status,
  data,
  error,
  onRetry,
  empty,
  isEmpty,
  loadingLabel,
  children,
}: {
  status: "idle" | "loading" | "success" | "error";
  data: T | null;
  error: Error | null;
  onRetry?: () => void;
  empty?: ReactNode;
  isEmpty?: (data: T) => boolean;
  loadingLabel?: string;
  children: (data: T) => ReactNode;
}) {
  if (status === "loading" || status === "idle") {
    return <Loading label={loadingLabel} />;
  }
  if (status === "error") {
    return <ErrorState error={error ?? "Unknown error"} onRetry={onRetry} />;
  }
  if (data === null) {
    return <>{empty ?? <EmptyState />}</>;
  }
  if (isEmpty && isEmpty(data)) {
    return <>{empty ?? <EmptyState />}</>;
  }
  return <>{children(data)}</>;
}
