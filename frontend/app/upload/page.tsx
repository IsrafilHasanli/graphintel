"use client";

import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { DocumentUpload } from "@/components/DocumentUpload";

export default function UploadPage() {
  return (
    <div>
      <PageHeader
        title="Ingest documents"
        description="Upload files or paste text. Track extraction in the jobs view."
        actions={
          <Link
            href="/jobs"
            className="rounded-md border border-surface-border bg-surface-panel px-3 py-1.5 text-sm text-slate-200 hover:bg-surface-border"
          >
            View jobs
          </Link>
        }
      />
      <DocumentUpload />
    </div>
  );
}
