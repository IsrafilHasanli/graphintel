import { EntityChip } from "./EntityChip";
import { EmptyState } from "./ui/StateView";
import type { ReasoningStep } from "@/lib/types";

/**
 * Ordered visualization of the graph traversal that supported an answer.
 * Each step reads: source (type) —RELATION→ target (type).
 */
export function ReasoningPath({ steps }: { steps: ReasoningStep[] }) {
  if (!steps || steps.length === 0) {
    return (
      <EmptyState
        title="No graph reasoning path"
        description="This answer did not rely on graph traversal (vector-only or refusal)."
      />
    );
  }

  return (
    <ol className="flex flex-col gap-2" aria-label="Graph reasoning path">
      {steps.map((step, i) => (
        <li
          key={`${step.relation_id}-${i}`}
          className="flex flex-wrap items-center gap-2 rounded-md border border-surface-border bg-surface-panel/60 px-3 py-2"
        >
          <span className="font-mono text-xs text-slate-500">{i + 1}.</span>
          <EntityChip
            type={step.source_type}
            label={step.source_id}
            href={`/graph?seed=${encodeURIComponent(step.source_id)}`}
          />
          <span className="flex items-center gap-1 text-xs text-slate-400">
            <span aria-hidden="true">—</span>
            <span className="rounded bg-surface-border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-brand-fg">
              {step.relation}
            </span>
            <span aria-hidden="true">→</span>
          </span>
          <EntityChip
            type={step.target_type}
            label={step.target_id}
            href={`/graph?seed=${encodeURIComponent(step.target_id)}`}
          />
        </li>
      ))}
    </ol>
  );
}
