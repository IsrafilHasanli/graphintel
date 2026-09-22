"use client";

import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { MetricCards } from "@/components/MetricCards";
import { EvalRunTable } from "@/components/EvalRunTable";
import { AsyncView, EmptyState, ErrorState } from "@/components/ui/StateView";
import { api, ApiError } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { percent, formatDate } from "@/lib/format";
import type { EvalRunOut, ReleaseGate } from "@/lib/types";

const GATE_STYLES: Record<string, string> = {
  PASS: "border-emerald-500/50 bg-emerald-500/10 text-emerald-300",
  "CONDITIONAL PASS": "border-amber-500/50 bg-amber-500/10 text-amber-300",
  FAIL: "border-red-500/50 bg-red-500/10 text-red-300",
};

export default function EvaluationPage() {
  const gate = useAsync<ReleaseGate>((s) => api.releaseGate(s), []);
  const [run, setRun] = useState<EvalRunOut | null>(null);
  const [runStatus, setRunStatus] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle");
  const [runError, setRunError] = useState<Error | null>(null);
  const [running, setRunning] = useState(false);

  // Load latest run on mount (404 => no run yet).
  const latest = useAsync<EvalRunOut | null>(
    (s) =>
      api.evalLatest(s).catch((err) => {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }),
    [],
  );

  const activeRun = run ?? latest.data ?? null;

  async function runEval() {
    setRunning(true);
    setRunStatus("loading");
    setRunError(null);
    try {
      const result = await api.evalRun();
      setRun(result);
      setRunStatus("success");
      gate.reload();
    } catch (err) {
      setRunError(err instanceof ApiError ? err : (err as Error));
      setRunStatus("error");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Evaluation"
        description="Golden questions, retrieval quality metrics, and the release gate."
        actions={
          <Button variant="primary" loading={running} onClick={() => void runEval()}>
            Run evaluation
          </Button>
        }
      />

      <section className="mb-4" aria-label="Release gate">
        <Card>
          <CardHeader title="Release gate" description="Eval-driven readiness signal" />
          <CardBody>
            <AsyncView
              status={gate.status}
              data={gate.data}
              error={gate.error}
              onRetry={gate.reload}
            >
              {(g) => (
                <div className="flex flex-col gap-3">
                  <Badge className={GATE_STYLES[g.status] ?? ""}>
                    <span className="text-sm font-semibold">{g.status}</span>
                  </Badge>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-red-300">
                        Blockers ({g.blockers?.length ?? 0})
                      </p>
                      {g.blockers?.length ? (
                        <ul className="mt-1 list-inside list-disc text-xs text-red-200">
                          {g.blockers.map((b, i) => (
                            <li key={i}>{b}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-xs text-slate-500">None</p>
                      )}
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-amber-300">
                        Warnings ({g.warnings?.length ?? 0})
                      </p>
                      {g.warnings?.length ? (
                        <ul className="mt-1 list-inside list-disc text-xs text-amber-200">
                          {g.warnings.map((w, i) => (
                            <li key={i}>{w}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-xs text-slate-500">None</p>
                      )}
                    </div>
                  </div>
                  {g.checks && Object.keys(g.checks).length > 0 ? (
                    <details className="text-xs">
                      <summary className="cursor-pointer text-slate-400">
                        Checks
                      </summary>
                      <pre className="mt-1 max-h-56 overflow-auto rounded border border-surface-border bg-surface-panel p-2 font-mono text-[11px] text-slate-300">
                        {JSON.stringify(g.checks, null, 2)}
                      </pre>
                    </details>
                  ) : null}
                </div>
              )}
            </AsyncView>
          </CardBody>
        </Card>
      </section>

      {runStatus === "error" && runError ? (
        <Card className="mb-4">
          <ErrorState error={runError} onRetry={() => void runEval()} />
        </Card>
      ) : null}

      <section aria-label="Evaluation run">
        <AsyncView
          status={run ? "success" : latest.status}
          data={activeRun}
          error={latest.error}
          onRetry={latest.reload}
          isEmpty={(d) => d === null}
          loadingLabel={running ? "Running evaluation…" : "Loading latest run…"}
          empty={
            <Card>
              <EmptyState
                title="No evaluation run yet"
                description="Run the golden-question suite to see pass rate and per-question metrics."
                action={
                  <Button
                    variant="primary"
                    loading={running}
                    onClick={() => void runEval()}
                  >
                    Run evaluation
                  </Button>
                }
              />
            </Card>
          }
        >
          {(r) => (
            <div className="flex flex-col gap-4">
              <MetricCards
                columns={6}
                metrics={[
                  {
                    label: "Pass rate",
                    value: percent(r.summary.pass_rate),
                    tone: r.summary.pass_rate >= 0.8 ? "good" : "warn",
                    hint: `${r.summary.passed}/${r.summary.total} passed`,
                  },
                  {
                    label: "Entity recall",
                    value: percent(r.summary.avg_entity_recall),
                  },
                  {
                    label: "Evidence recall",
                    value: percent(r.summary.avg_evidence_recall),
                  },
                  {
                    label: "Reasoning recall",
                    value: percent(r.summary.avg_reasoning_recall),
                  },
                  {
                    label: "Theme coverage",
                    value: percent(r.summary.avg_theme_coverage),
                  },
                  {
                    label: "Refusals",
                    value: r.summary.refusals,
                    tone: r.summary.refusals > 0 ? "warn" : "default",
                  },
                ]}
              />

              <Card>
                <CardHeader
                  title="Per-question results"
                  description={`Run ${r.id} · started ${formatDate(
                    r.started_at,
                  )}${r.finished_at ? ` · finished ${formatDate(r.finished_at)}` : ""}`}
                />
                <CardBody className="p-0">
                  {r.results?.length ? (
                    <EvalRunTable run={r} />
                  ) : (
                    <EmptyState title="No results in this run" />
                  )}
                </CardBody>
              </Card>
            </div>
          )}
        </AsyncView>
      </section>
    </div>
  );
}
