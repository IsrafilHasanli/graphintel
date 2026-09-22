"use client";

import { useRef, useState } from "react";
import { Card, CardBody, CardHeader } from "./ui/Card";
import { Button } from "./ui/Button";
import { TextArea, TextInput, Select } from "./ui/Field";
import { JobStatusTimeline, JobErrors } from "./JobStatusTimeline";
import { cx } from "@/lib/format";
import { api, ApiError } from "@/lib/api";
import type { JobOut } from "@/lib/types";

const SOURCE_KINDS = [
  "ticket",
  "incident",
  "postmortem",
  "runbook",
  "sla",
  "service",
  "other",
];

export function DocumentUpload({ onJob }: { onJob?: (job: JobOut) => void }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <FileUpload onJob={onJob} />
      <TextUpload onJob={onJob} />
    </div>
  );
}

function JobResult({ job }: { job: JobOut | null }) {
  if (!job) return null;
  return (
    <div className="mt-4 rounded-md border border-surface-border bg-surface-panel/60 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-xs text-slate-400">{job.id}</span>
        <span className="text-xs text-slate-500">
          {job.filename ?? job.source}
        </span>
      </div>
      <JobStatusTimeline job={job} />
      <JobErrors job={job} />
    </div>
  );
}

function FileUpload({ onJob }: { onJob?: (job: JobOut) => void }) {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState<JobOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function upload(file: File) {
    setLoading(true);
    setError(null);
    try {
      const result = await api.uploadFile(file);
      setJob(result);
      onJob?.(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : (err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Upload a document"
        description="Drag & drop or pick a file (txt, md, json, csv, pdf)."
      />
      <CardBody>
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            const file = e.dataTransfer.files?.[0];
            if (file) void upload(file);
          }}
          className={cx(
            "flex flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed p-6 text-center transition-colors",
            dragging
              ? "border-brand bg-brand/10"
              : "border-surface-border bg-surface-panel/40",
          )}
        >
          <p className="text-sm text-slate-300">
            Drop a file here, or
          </p>
          <Button
            variant="secondary"
            size="sm"
            loading={loading}
            onClick={() => inputRef.current?.click()}
          >
            Choose file
          </Button>
          <input
            ref={inputRef}
            type="file"
            className="sr-only"
            aria-label="Upload document file"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void upload(file);
              e.target.value = "";
            }}
          />
        </div>
        {error ? (
          <p role="alert" className="mt-2 text-xs text-red-300">
            {error}
          </p>
        ) : null}
        <JobResult job={job} />
      </CardBody>
    </Card>
  );
}

function TextUpload({ onJob }: { onJob?: (job: JobOut) => void }) {
  const [filename, setFilename] = useState("");
  const [content, setContent] = useState("");
  const [sourceKind, setSourceKind] = useState("ticket");
  const [loading, setLoading] = useState(false);
  const [job, setJob] = useState<JobOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!filename.trim() || !content.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.ingestText({
        filename: filename.trim(),
        content,
        source_kind: sourceKind,
      });
      setJob(result);
      onJob?.(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : (err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Paste text"
        description="Ingest raw text as a named document."
      />
      <CardBody>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
          className="flex flex-col gap-3"
        >
          <div className="grid grid-cols-2 gap-3">
            <TextInput
              label="Filename"
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              placeholder="incident-INC-999.md"
              required
            />
            <Select
              label="Source kind"
              value={sourceKind}
              onChange={(e) => setSourceKind(e.target.value)}
            >
              {SOURCE_KINDS.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </Select>
          </div>
          <TextArea
            label="Content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={6}
            placeholder="Paste ticket / incident / postmortem text…"
            required
          />
          <div className="flex justify-end">
            <Button
              type="submit"
              variant="primary"
              loading={loading}
              disabled={!filename.trim() || !content.trim()}
            >
              Ingest text
            </Button>
          </div>
        </form>
        {error ? (
          <p role="alert" className="mt-2 text-xs text-red-300">
            {error}
          </p>
        ) : null}
        <JobResult job={job} />
      </CardBody>
    </Card>
  );
}
