"use client";

import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Select } from "@/components/ui/Field";
import { Table, THead, TH, TR, TD } from "@/components/ui/Table";
import { AsyncView, EmptyState } from "@/components/ui/StateView";
import { JobStatusTimeline, JobErrors } from "@/components/JobStatusTimeline";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { jobStateClasses, JOB_PIPELINE } from "@/lib/theme";
import { relativeTime, titleCase } from "@/lib/format";
import type { JobOut, JobState } from "@/lib/types";

const STATES: (JobState | "")[] = [
  "",
  "queued",
  "parsing",
  "chunking",
  "extracting",
  "indexing",
  "completed",
  "failed",
  "partial",
];

export default function JobsPage() {
  const [state, setState] = useState<string>("");
  const [selected, setSelected] = useState<string | null>(null);

  const jobs = useAsync<JobOut[]>(
    (s) => api.jobs({ state: state || undefined, limit: 100 }, s),
    [state],
  );

  const detail = useAsync<JobOut | null>(
    (s) => (selected ? api.job(selected, s) : Promise.resolve(null)),
    [selected],
  );

  return (
    <div>
      <PageHeader
        title="Ingestion jobs"
        description="Track parsing, chunking, extraction, and indexing. Failed and partial jobs surface their errors."
        actions={
          <Button variant="secondary" onClick={jobs.reload}>
            Refresh
          </Button>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
        <Card>
          <CardHeader
            title="Jobs"
            actions={
              <div className="w-40">
                <Select
                  aria-label="Filter by state"
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                >
                  {STATES.map((s) => (
                    <option key={s || "all"} value={s}>
                      {s ? titleCase(s) : "All states"}
                    </option>
                  ))}
                </Select>
              </div>
            }
          />
          <CardBody className="p-0">
            <AsyncView
              status={jobs.status}
              data={jobs.data}
              error={jobs.error}
              onRetry={jobs.reload}
              isEmpty={(d) => d.length === 0}
              empty={
                <EmptyState
                  title="No jobs"
                  description="Ingest a document to create a job."
                />
              }
            >
              {(data) => (
                <Table>
                  <THead>
                    <tr>
                      <TH>State</TH>
                      <TH>Source</TH>
                      <TH>Errors</TH>
                      <TH>Updated</TH>
                    </tr>
                  </THead>
                  <tbody>
                    {data.map((job) => (
                      <TR
                        key={job.id}
                        onClick={() => setSelected(job.id)}
                        selected={selected === job.id}
                      >
                        <TD>
                          <Badge className={jobStateClasses(job.state)}>
                            {titleCase(job.state)}
                          </Badge>
                        </TD>
                        <TD>
                          <div className="text-slate-100">
                            {job.filename ?? job.source}
                          </div>
                          <div className="font-mono text-[10px] text-slate-500">
                            {job.source_kind} · {job.id}
                          </div>
                        </TD>
                        <TD>
                          {job.errors?.length ? (
                            <Badge className="border-red-500/40 bg-red-500/10 text-red-300">
                              {job.errors.length}
                            </Badge>
                          ) : (
                            <span className="text-xs text-slate-500">0</span>
                          )}
                        </TD>
                        <TD className="text-xs text-slate-400">
                          {relativeTime(job.updated_at)}
                        </TD>
                      </TR>
                    ))}
                  </tbody>
                </Table>
              )}
            </AsyncView>
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Job detail"
            description={selected ?? "Select a job"}
          />
          <CardBody>
            {!selected ? (
              <p className="text-sm text-slate-400">
                Select a job to inspect its pipeline and errors.
              </p>
            ) : (
              <AsyncView
                status={detail.status}
                data={detail.data}
                error={detail.error}
                onRetry={detail.reload}
              >
                {(job) =>
                  job ? (
                    <div className="flex flex-col gap-4">
                      <JobStatusTimeline job={job} />
                      <div>
                        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                          Stats
                        </p>
                        <pre className="max-h-48 overflow-auto rounded border border-surface-border bg-surface-panel p-2 font-mono text-[11px] text-slate-300">
                          {JSON.stringify(job.stats ?? {}, null, 2)}
                        </pre>
                      </div>
                      <div>
                        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                          Errors
                        </p>
                        {job.errors?.length ? (
                          <JobErrors job={job} />
                        ) : (
                          <p className="text-xs text-slate-500">
                            No errors reported.
                          </p>
                        )}
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-slate-400">Not found.</p>
                  )
                }
              </AsyncView>
            )}
          </CardBody>
        </Card>
      </div>

      <p className="mt-3 text-xs text-slate-500">
        Pipeline stages: {JOB_PIPELINE.join(" → ")}
      </p>
    </div>
  );
}
