"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  Database,
  FileText,
  GitBranch,
  Gauge,
  Server,
  Sparkles,
  Waypoints,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { MetricCards } from "@/components/MetricCards";
import { Modal } from "@/components/ui/Modal";
import { AsyncView } from "@/components/ui/StateView";
import { EntityChip } from "@/components/EntityChip";
import { api, ApiError } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { entityColor } from "@/lib/theme";
import type { AdminStats, ReleaseGate, SeedResult } from "@/lib/types";

const GATE_STYLES: Record<string, string> = {
  PASS: "border-emerald-500/50 bg-emerald-500/10 text-emerald-300",
  "CONDITIONAL PASS": "border-amber-500/50 bg-amber-500/10 text-amber-300",
  FAIL: "border-red-500/50 bg-red-500/10 text-red-300",
};

export default function DashboardPage() {
  const stats = useAsync<AdminStats>((s) => api.stats(s), []);
  const gate = useAsync<ReleaseGate>((s) => api.releaseGate(s), []);

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [seedResult, setSeedResult] = useState<SeedResult | null>(null);
  const [seedError, setSeedError] = useState<string | null>(null);

  async function runSeed() {
    setSeeding(true);
    setSeedError(null);
    try {
      const result = await api.seed(true);
      setSeedResult(result);
      setConfirmOpen(false);
      stats.reload();
      gate.reload();
    } catch (err) {
      setSeedError(err instanceof ApiError ? err.message : (err as Error).message);
    } finally {
      setSeeding(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Operations dashboard"
        description="Corpus, graph coverage, and release readiness at a glance."
        actions={
          <Button variant="primary" onClick={() => setConfirmOpen(true)}>
            <Sparkles size={15} aria-hidden="true" />
            Seed demo data
          </Button>
        }
      />

      <section className="rise-in mb-5 overflow-hidden rounded-lg border border-cyan-300/15 bg-surface-raised/90 shadow-[0_18px_60px_rgba(8,47,73,0.16)]">
        <div className="relative flex flex-col gap-5 p-5 sm:flex-row sm:items-end sm:justify-between sm:p-6">
          <div className="max-w-2xl">
            <div className="mb-3 flex items-center gap-2 text-xs font-medium text-cyan-200">
              <span className="status-pulse flex h-7 w-7 items-center justify-center rounded-md bg-cyan-300/10 text-cyan-200">
                <Waypoints size={16} aria-hidden="true" />
              </span>
              Knowledge graph online
            </div>
            <h2 className="text-2xl font-semibold tracking-tight text-slate-50 sm:text-3xl">
              See the signal behind every incident.
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-slate-400">
              Trace support evidence through services, teams, runbooks, and SLA risk from one operational graph.
            </p>
          </div>
          <Link
            href="/ask"
            className="group inline-flex items-center gap-2 self-start rounded-md border border-cyan-300/25 bg-cyan-300/10 px-3 py-2 text-sm font-medium text-cyan-100 transition-all hover:-translate-y-px hover:border-cyan-200/50 hover:bg-cyan-300/15 sm:self-auto"
          >
            Ask the graph
            <ArrowUpRight size={15} className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" aria-hidden="true" />
          </Link>
        </div>
      </section>

      {seedResult ? (
        <div
          role="status"
          className="mb-4 rounded-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200"
        >
          Seeded {seedResult.documents} documents, {seedResult.entities} entities,{" "}
          {seedResult.relations} relations ({seedResult.may_violate_derived}{" "}
          MAY_VIOLATE derived).
        </div>
      ) : null}

      <section className="mb-5" aria-label="Corpus statistics">
        <AsyncView
          status={stats.status}
          data={stats.data}
          error={stats.error}
          onRetry={stats.reload}
          loadingLabel="Loading stats…"
        >
          {(data) => (
            <MetricCards
              columns={6}
              metrics={[
                { label: "Documents", value: data.documents, icon: FileText },
                { label: "Chunks", value: data.chunks, icon: Database },
                { label: "Entities", value: data.entities, icon: GitBranch },
                { label: "Relations", value: data.relations, icon: Waypoints },
                { label: "Jobs", value: data.jobs, icon: Server },
                { label: "Answers", value: data.answers, icon: Gauge },
              ]}
            />
          )}
        </AsyncView>
      </section>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="rise-in stagger-2 lg:col-span-2">
          <CardHeader
            title="Entity coverage"
            description="Extracted entities by type"
          />
          <CardBody>
            <AsyncView
              status={stats.status}
              data={stats.data}
              error={stats.error}
              onRetry={stats.reload}
              isEmpty={(d) => Object.keys(d.entity_types ?? {}).length === 0}
              empty={
                <p className="text-sm text-slate-400">
                  No entities yet. Seed demo data to populate the graph.
                </p>
              }
            >
              {(data) => <EntityBreakdown data={data} />}
            </AsyncView>
          </CardBody>
        </Card>

        <Card className="rise-in stagger-3">
          <CardHeader
            title="Release gate"
            description="Eval-driven readiness"
            actions={
              <Link
                href="/evaluation"
                className="text-xs text-brand-fg hover:underline"
              >
                Details
              </Link>
            }
          />
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
                  {g.blockers?.length ? (
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-red-300">
                        Blockers
                      </p>
                      <ul className="mt-1 list-inside list-disc text-xs text-red-200">
                        {g.blockers.map((b, i) => (
                          <li key={i}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {g.warnings?.length ? (
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-amber-300">
                        Warnings
                      </p>
                      <ul className="mt-1 list-inside list-disc text-xs text-amber-200">
                        {g.warnings.map((w, i) => (
                          <li key={i}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {!g.blockers?.length && !g.warnings?.length ? (
                    <p className="text-xs text-slate-400">
                      No blockers or warnings.
                    </p>
                  ) : null}
                </div>
              )}
            </AsyncView>
          </CardBody>
        </Card>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <QuickLink href="/ask" title="Ask" body="Run a Graph RAG question." icon={Sparkles} />
        <QuickLink
          href="/graph"
          title="Explore graph"
          body="Traverse the knowledge graph."
          icon={Waypoints}
        />
        <QuickLink
          href="/entities"
          title="Review entities"
          body="Merge & correct extractions."
          icon={GitBranch}
        />
        <QuickLink
          href="/upload"
          title="Ingest"
          body="Upload docs or paste text."
          icon={FileText}
        />
      </div>

      <Modal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title="Seed demo data?"
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" loading={seeding} onClick={() => void runSeed()}>
              Reset &amp; seed
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-300">
          This resets the corpus and loads the deterministic demo dataset
          (customers, tickets, incidents, postmortems, runbooks, SLAs). Existing
          ingested data will be replaced.
        </p>
        {seedError ? (
          <p role="alert" className="mt-2 text-xs text-red-300">
            {seedError}
          </p>
        ) : null}
      </Modal>
    </div>
  );
}

function EntityBreakdown({ data }: { data: AdminStats }) {
  const entries = Object.entries(data.entity_types ?? {}).sort(
    (a, b) => b[1] - a[1],
  );
  const max = Math.max(1, ...entries.map(([, v]) => v));
  return (
    <ul className="flex flex-col gap-2">
      {entries.map(([type, count]) => (
        <li key={type} className="flex items-center gap-3">
          <div className="w-40 shrink-0">
            <EntityChip type={type} label={type} />
          </div>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-panel">
            <div
              className="h-full rounded-full"
              style={{
                width: `${(count / max) * 100}%`,
                backgroundColor: entityColor(type),
              }}
            />
          </div>
          <span className="w-10 text-right font-mono text-xs text-slate-300">
            {count}
          </span>
        </li>
      ))}
    </ul>
  );
}

function QuickLink({
  href,
  title,
  body,
  icon: Icon,
}: {
  href: string;
  title: string;
  body: string;
  icon: typeof Sparkles;
}) {
  return (
    <Link
      href={href}
      className="group flex items-start gap-3 rounded-lg border border-surface-border bg-surface-raised p-4 transition-all hover:-translate-y-0.5 hover:border-cyan-300/40 hover:bg-surface-panel focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
    >
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-slate-800 text-cyan-300 transition-colors group-hover:bg-cyan-300/10">
        <Icon size={16} aria-hidden="true" />
      </span>
      <span>
        <span className="block text-sm font-semibold text-slate-100">{title}</span>
        <span className="mt-0.5 block text-xs text-slate-400">{body}</span>
      </span>
      <ArrowUpRight size={14} className="ml-auto text-slate-600 transition-colors group-hover:text-cyan-300" aria-hidden="true" />
    </Link>
  );
}
