// Deterministic color assignments for entity + relation types so the graph,
// entity chips, and citations use a consistent visual language.

import type { Confidence, EntityType } from "./types";

export const ENTITY_COLORS: Record<string, string> = {
  Customer: "#38bdf8", // sky
  SupportTicket: "#f59e0b", // amber
  Incident: "#ef4444", // red
  IncidentUpdate: "#fb7185", // rose
  Postmortem: "#a78bfa", // violet
  Runbook: "#34d399", // emerald
  Service: "#60a5fa", // blue
  Team: "#c084fc", // purple
  SLAContract: "#facc15", // yellow
  SLAClause: "#fcd34d", // amber-light
  ErrorSignature: "#f87171", // red-light
  RootCause: "#fb923c", // orange
};

export const DEFAULT_ENTITY_COLOR = "#94a3b8";

export function entityColor(type: EntityType | string): string {
  return ENTITY_COLORS[type] ?? DEFAULT_ENTITY_COLOR;
}

export const ENTITY_TYPES: EntityType[] = [
  "Customer",
  "SupportTicket",
  "Incident",
  "IncidentUpdate",
  "Postmortem",
  "Runbook",
  "Service",
  "Team",
  "SLAContract",
  "SLAClause",
  "ErrorSignature",
  "RootCause",
];

export const RELATION_TYPES = [
  "REPORTED",
  "RELATED_TO",
  "AFFECTED",
  "OWNED_BY",
  "CAUSED_BY",
  "HAS_UPDATE",
  "MENTIONS",
  "APPLIES_TO",
  "PART_OF",
  "CONSTRAINS",
  "MAY_VIOLATE",
  "MITIGATES",
  "ANALYZES",
  "EXHIBITS",
] as const;

// Tailwind class fragments for confidence badges. Exported for direct testing.
export const CONFIDENCE_STYLES: Record<Confidence, string> = {
  high: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  medium: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  low: "bg-orange-500/15 text-orange-300 border-orange-500/40",
  insufficient: "bg-red-500/15 text-red-300 border-red-500/50",
};

export function confidenceClasses(confidence: Confidence): string {
  return CONFIDENCE_STYLES[confidence] ?? CONFIDENCE_STYLES.insufficient;
}

export const JOB_STATE_STYLES: Record<string, string> = {
  queued: "bg-slate-500/15 text-slate-300 border-slate-500/40",
  parsing: "bg-sky-500/15 text-sky-300 border-sky-500/40",
  chunking: "bg-sky-500/15 text-sky-300 border-sky-500/40",
  extracting: "bg-indigo-500/15 text-indigo-300 border-indigo-500/40",
  indexing: "bg-violet-500/15 text-violet-300 border-violet-500/40",
  completed: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
  failed: "bg-red-500/15 text-red-300 border-red-500/50",
  partial: "bg-amber-500/15 text-amber-300 border-amber-500/40",
};

export function jobStateClasses(state: string): string {
  return JOB_STATE_STYLES[state] ?? "bg-slate-500/15 text-slate-300 border-slate-500/40";
}

// Ordered pipeline used by the job status timeline.
export const JOB_PIPELINE = [
  "queued",
  "parsing",
  "chunking",
  "extracting",
  "indexing",
  "completed",
] as const;
