"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { GraphExplorer } from "@/components/GraphExplorer";
import { Loading } from "@/components/ui/StateView";

function GraphInner() {
  const params = useSearchParams();
  const seed = params.get("seed") ?? undefined;
  return <GraphExplorer initialSeed={seed} />;
}

export default function GraphPage() {
  return (
    <div>
      <PageHeader
        title="Graph explorer"
        description="Interactive customer · ticket · incident · service · SLA graph."
      />
      <Suspense fallback={<Loading label="Loading explorer…" />}>
        <GraphInner />
      </Suspense>
    </div>
  );
}
