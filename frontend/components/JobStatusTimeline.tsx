import { JOB_PIPELINE, jobStateClasses } from "@/lib/theme";
import { Badge } from "./ui/Badge";
import { cx, titleCase } from "@/lib/format";
import type { JobOut } from "@/lib/types";

/**
 * Horizontal pipeline showing where a job is (or where it stopped). Failed /
 * partial states are surfaced explicitly rather than hidden.
 */
export function JobStatusTimeline({ job }: { job: JobOut }) {
  const failed = job.state === "failed";
  const partial = job.state === "partial";
  const terminalIndex = (JOB_PIPELINE as readonly string[]).indexOf(job.state);
  // For failed/partial, treat progress up to the stage before the terminal flag.
  const reachedIndex =
    terminalIndex === -1 ? JOB_PIPELINE.length - 1 : terminalIndex;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <Badge className={jobStateClasses(job.state)}>{titleCase(job.state)}</Badge>
        {failed ? (
          <span className="text-xs text-red-300">Pipeline halted</span>
        ) : null}
        {partial ? (
          <span className="text-xs text-amber-300">
            Completed with errors
          </span>
        ) : null}
      </div>
      <ol className="flex flex-wrap items-center gap-1.5" aria-label="Job pipeline">
        {JOB_PIPELINE.map((stage, i) => {
          const done = i < reachedIndex || job.state === "completed";
          const current = i === reachedIndex && job.state !== "completed";
          return (
            <li key={stage} className="flex items-center gap-1.5">
              <span
                className={cx(
                  "rounded px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide",
                  done && "bg-emerald-500/15 text-emerald-300",
                  current && !failed && !partial && "bg-sky-500/20 text-sky-200",
                  current && failed && "bg-red-500/20 text-red-200",
                  current && partial && "bg-amber-500/20 text-amber-200",
                  !done && !current && "bg-surface-panel text-slate-500",
                )}
              >
                {stage}
              </span>
              {i < JOB_PIPELINE.length - 1 ? (
                <span className="text-slate-600" aria-hidden="true">
                  →
                </span>
              ) : null}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

/** Compact error list for a job. */
export function JobErrors({ job }: { job: JobOut }) {
  if (!job.errors || job.errors.length === 0) return null;
  return (
    <ul className="mt-2 space-y-1" aria-label="Job errors">
      {job.errors.map((err, i) => (
        <li
          key={i}
          className="rounded border border-red-500/30 bg-red-500/10 px-2 py-1 text-xs text-red-200"
        >
          <span className="font-mono text-[10px] uppercase text-red-300">
            {err.scope}
            {err.ref ? ` · ${err.ref}` : ""}
          </span>
          <span className="ml-2">{err.reason}</span>
        </li>
      ))}
    </ul>
  );
}
