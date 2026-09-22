import { EntityChip } from "./EntityChip";
import { Badge } from "./ui/Badge";
import { EmptyState } from "./ui/StateView";
import { percent } from "@/lib/format";
import type { Citation } from "@/lib/types";

/** Renders answer citations: chunk snippets and entity chips with scores. */
export function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations || citations.length === 0) {
    return (
      <EmptyState
        title="No citations"
        description="The answer is not backed by any retrieved sources."
      />
    );
  }

  return (
    <ul className="flex flex-col gap-2">
      {citations.map((c, i) => (
        <li
          key={`${c.ref_id}-${i}`}
          className="rounded-md border border-surface-border bg-surface-panel/60 p-3"
        >
          <div className="mb-1 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Badge
                className={
                  c.kind === "chunk"
                    ? "border-sky-500/40 bg-sky-500/10 text-sky-300"
                    : "border-violet-500/40 bg-violet-500/10 text-violet-300"
                }
              >
                {c.kind}
              </Badge>
              <span className="font-mono text-xs text-slate-400">
                {c.ref_id}
              </span>
            </div>
            <span className="font-mono text-[10px] text-slate-500">
              score {percent(c.score, 0)}
            </span>
          </div>

          {c.kind === "entity" && c.entity_type ? (
            <div className="mb-1">
              <EntityChip
                type={c.entity_type}
                label={c.ref_id}
                href={`/graph?seed=${encodeURIComponent(c.ref_id)}`}
              />
            </div>
          ) : null}

          {c.snippet ? (
            <blockquote className="border-l-2 border-surface-border pl-2 text-sm text-slate-300">
              {c.snippet}
            </blockquote>
          ) : null}

          {c.source_document_id ? (
            <p className="mt-1 font-mono text-[10px] text-slate-500">
              doc {c.source_document_id}
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
