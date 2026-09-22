"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Edge,
  type Node,
  Position,
  ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";

import { Card, CardBody, CardHeader } from "./ui/Card";
import { Button } from "./ui/Button";
import { TextInput, Select } from "./ui/Field";
import { Badge } from "./ui/Badge";
import { AsyncView } from "./ui/StateView";
import { entityColor, ENTITY_TYPES, RELATION_TYPES } from "@/lib/theme";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import type { GraphNode, GraphView } from "@/lib/types";

/** Deterministic circular layout so we don't need a layout engine dependency. */
function layout(view: GraphView): { nodes: Node[]; edges: Edge[] } {
  const n = view.nodes.length || 1;
  const radius = Math.max(160, n * 26);
  const nodes: Node[] = view.nodes.map((gn, i) => {
    const angle = (2 * Math.PI * i) / n;
    return {
      id: gn.id,
      position: {
        x: radius + radius * Math.cos(angle),
        y: radius + radius * Math.sin(angle),
      },
      data: { label: gn.label, entity: gn },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: {
        background: "#111725",
        color: "#e2e8f0",
        border: `2px solid ${entityColor(gn.type)}`,
        borderRadius: 8,
        fontSize: 11,
        padding: "6px 10px",
        width: 150,
      },
    };
  });

  const edges: Edge[] = view.edges.map((ge) => ({
    id: ge.id,
    source: ge.source,
    target: ge.target,
    label: ge.type,
    labelStyle: { fill: "#93c5fd", fontSize: 9 },
    labelBgStyle: { fill: "#0b0f17" },
    style: { stroke: "#334155" },
    animated: ge.type === "MAY_VIOLATE",
  }));

  return { nodes, edges };
}

type Mode = "browse" | "expand";

export function GraphExplorer({ initialSeed }: { initialSeed?: string }) {
  const [mode, setMode] = useState<Mode>(initialSeed ? "expand" : "browse");
  const [typeFilter, setTypeFilter] = useState("");
  const [relFilter, setRelFilter] = useState("");
  const [seedInput, setSeedInput] = useState(initialSeed ?? "");
  const [seeds, setSeeds] = useState<string[]>(initialSeed ? [initialSeed] : []);
  const [hops, setHops] = useState(2);
  const [selected, setSelected] = useState<GraphNode | null>(null);

  const state = useAsync<GraphView>(
    (signal) =>
      mode === "expand" && seeds.length > 0
        ? api.graphExpand(
            { seed: seeds, hops, rel_types: relFilter || undefined },
            signal,
          )
        : api.graph(
            {
              types: typeFilter || undefined,
              rel_types: relFilter || undefined,
              limit: 150,
            },
            signal,
          ),
    [mode, seeds.join(","), hops, typeFilter, relFilter],
  );

  const flow = useMemo(
    () => (state.data ? layout(state.data) : { nodes: [], edges: [] }),
    [state.data],
  );

  const onNodeClick = useCallback(
    (_: unknown, node: Node) => {
      const entity = (node.data as { entity?: GraphNode })?.entity ?? null;
      setSelected(entity);
    },
    [],
  );

  useEffect(() => {
    if (initialSeed) {
      setSeeds([initialSeed]);
      setSeedInput(initialSeed);
      setMode("expand");
    }
  }, [initialSeed]);

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <Card className="flex flex-col">
        <CardHeader
          title="Graph explorer"
          description="Customer · Ticket · Incident · Service · SLA knowledge graph"
          actions={
            <div className="flex gap-1">
              <Button
                size="sm"
                variant={mode === "browse" ? "primary" : "ghost"}
                onClick={() => setMode("browse")}
              >
                Browse
              </Button>
              <Button
                size="sm"
                variant={mode === "expand" ? "primary" : "ghost"}
                onClick={() => setMode("expand")}
              >
                Expand
              </Button>
            </div>
          }
        />
        <div className="flex flex-wrap items-end gap-2 border-b border-surface-border px-4 py-3">
          {mode === "browse" ? (
            <div className="w-40">
              <Select
                label="Node type"
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
              >
                <option value="">All types</option>
                {ENTITY_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </Select>
            </div>
          ) : (
            <>
              <div className="w-48">
                <TextInput
                  label="Seed entity id"
                  value={seedInput}
                  onChange={(e) => setSeedInput(e.target.value)}
                  placeholder="INC-247"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && seedInput.trim()) {
                      setSeeds([seedInput.trim()]);
                    }
                  }}
                />
              </div>
              <div className="w-24">
                <Select
                  label="Hops"
                  value={String(hops)}
                  onChange={(e) => setHops(Number(e.target.value))}
                >
                  {[1, 2, 3].map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </Select>
              </div>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => seedInput.trim() && setSeeds([seedInput.trim()])}
              >
                Expand
              </Button>
            </>
          )}
          <div className="w-44">
            <Select
              label="Relation type"
              value={relFilter}
              onChange={(e) => setRelFilter(e.target.value)}
            >
              <option value="">All relations</option>
              {RELATION_TYPES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </Select>
          </div>
        </div>

        <div className="h-[600px]">
          <AsyncView
            status={state.status}
            data={state.data}
            error={state.error}
            onRetry={state.reload}
            isEmpty={(d) => d.nodes.length === 0}
            loadingLabel="Loading graph…"
            empty={
              <div className="flex h-full items-center justify-center text-sm text-slate-400">
                No nodes. Seed demo data or adjust filters.
              </div>
            }
          >
            {() => (
              <ReactFlowProvider>
                <ReactFlow
                  nodes={flow.nodes}
                  edges={flow.edges}
                  onNodeClick={onNodeClick}
                  fitView
                  minZoom={0.1}
                  proOptions={{ hideAttribution: true }}
                >
                  <Background color="#1e293b" gap={20} />
                  <Controls className="!bg-surface-panel !border-surface-border" />
                  <MiniMap
                    pannable
                    zoomable
                    nodeColor={(node) =>
                      entityColor(
                        (node.data as { entity?: GraphNode })?.entity?.type ??
                          "",
                      )
                    }
                    className="!bg-surface-panel"
                  />
                </ReactFlow>
              </ReactFlowProvider>
            )}
          </AsyncView>
        </div>
      </Card>

      <Card>
        <CardHeader title="Details" description="Click a node to inspect" />
        <CardBody>
          {selected ? (
            <div className="flex flex-col gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span
                    className="h-3 w-3 rounded-full"
                    style={{ backgroundColor: entityColor(selected.type) }}
                    aria-hidden="true"
                  />
                  <Badge>{selected.type}</Badge>
                </div>
                <p className="mt-2 text-sm font-medium text-slate-100">
                  {selected.label}
                </p>
                <p className="font-mono text-[10px] text-slate-500">
                  {selected.id}
                </p>
              </div>
              <div>
                <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">
                  Attributes
                </p>
                {Object.keys(selected.attributes ?? {}).length === 0 ? (
                  <p className="text-xs text-slate-500">None</p>
                ) : (
                  <dl className="space-y-1 text-xs">
                    {Object.entries(selected.attributes).map(([k, v]) => (
                      <div key={k} className="flex gap-2">
                        <dt className="shrink-0 text-slate-500">{k}</dt>
                        <dd className="break-all text-slate-300">
                          {typeof v === "object"
                            ? JSON.stringify(v)
                            : String(v)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                )}
              </div>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  setSeedInput(selected.id);
                  setSeeds([selected.id]);
                  setMode("expand");
                }}
              >
                Expand from this node
              </Button>
            </div>
          ) : (
            <p className="text-sm text-slate-400">
              Select a node in the graph to see its type and attributes.
            </p>
          )}

          <div className="mt-4 border-t border-surface-border pt-3">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">
              Legend
            </p>
            <div className="flex flex-wrap gap-1.5">
              {ENTITY_TYPES.map((t) => (
                <span
                  key={t}
                  className="inline-flex items-center gap-1 text-[10px] text-slate-400"
                >
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: entityColor(t) }}
                    aria-hidden="true"
                  />
                  {t}
                </span>
              ))}
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
