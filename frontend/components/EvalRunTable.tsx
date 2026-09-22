"use client";

import { useState } from "react";
import { Table, THead, TH, TR, TD } from "./ui/Table";
import { Badge } from "./ui/Badge";
import { percent } from "@/lib/format";
import type { EvalResult, EvalRunOut } from "@/lib/types";

export function EvalRunTable({ run }: { run: EvalRunOut }) {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <Table>
      <THead>
        <tr>
          <TH>Result</TH>
          <TH>Question</TH>
          <TH className="text-right">Metrics</TH>
        </tr>
      </THead>
      <tbody>
        {run.results.map((r) => (
          <FragmentRow
            key={r.question_id}
            result={r}
            open={expanded === r.question_id}
            onToggle={() =>
              setExpanded((cur) =>
                cur === r.question_id ? null : r.question_id,
              )
            }
          />
        ))}
      </tbody>
    </Table>
  );
}

function FragmentRow({
  result,
  open,
  onToggle,
}: {
  result: EvalResult;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <TR onClick={onToggle} selected={open}>
        <TD>
          <Badge
            className={
              result.passed
                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                : "border-red-500/50 bg-red-500/10 text-red-300"
            }
          >
            {result.passed ? "PASS" : "FAIL"}
          </Badge>
        </TD>
        <TD>
          <span className="text-slate-100">{result.question}</span>
          <span className="ml-2 font-mono text-[10px] text-slate-500">
            {result.question_id}
          </span>
        </TD>
        <TD className="text-right">
          <div className="flex flex-wrap justify-end gap-1">
            {Object.entries(result.metrics ?? {}).map(([k, v]) => (
              <Badge key={k} title={k}>
                <span className="text-slate-500">{shortMetric(k)}</span>
                <span className="font-mono">
                  {typeof v === "number" ? percent(v) : String(v)}
                </span>
              </Badge>
            ))}
          </div>
        </TD>
      </TR>
      {open ? (
        <tr className="border-b border-surface-border/60">
          <td colSpan={3} className="bg-surface-panel/40 px-3 py-3">
            <div className="grid gap-3 md:grid-cols-2">
              <ExpectedActual title="Expected" value={result.expected} />
              <ExpectedActual title="Actual" value={result.actual} />
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}

function ExpectedActual({
  title,
  value,
}: {
  title: string;
  value: Record<string, unknown>;
}) {
  return (
    <div className="rounded border border-surface-border bg-surface-raised p-2">
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
        {title}
      </p>
      <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words font-mono text-[11px] text-slate-300">
        {JSON.stringify(value ?? {}, null, 2)}
      </pre>
    </div>
  );
}

function shortMetric(key: string): string {
  return key
    .replace(/^avg_/, "")
    .replace(/_recall$/, " rec")
    .replace(/_coverage$/, " cov")
    .replace(/_/g, " ")
    .slice(0, 10);
}
