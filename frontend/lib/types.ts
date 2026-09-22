// Shared TypeScript types mirroring the GraphIntel FastAPI contract.

// ---- Meta ----
export interface HealthOut {
  status: string;
}

export interface ReadyOut {
  status: string;
  database: boolean | string;
  graph: boolean | string;
  llm: boolean | string;
  embeddings: boolean | string;
}

// ---- Admin / stats ----
export interface SeedResult {
  jobs: number;
  documents: number;
  chunks: number;
  entities: number;
  relations: number;
  may_violate_derived: number;
  job_states: Record<string, number>;
}

export interface AdminStats {
  documents: number;
  chunks: number;
  jobs: number;
  entities: number;
  relations: number;
  answers: number;
  job_states: Record<string, number>;
  entity_types: Record<string, number>;
}

export interface AuditEntry {
  id: string;
  action: string;
  entity_type: string | null;
  target_id: string | null;
  detail: Record<string, unknown> | string | null;
  actor: string | null;
  created_at: string;
}

// ---- Ingestion & jobs ----
export type JobState =
  | "queued"
  | "parsing"
  | "chunking"
  | "extracting"
  | "indexing"
  | "completed"
  | "failed"
  | "partial";

export interface JobError {
  scope: string;
  ref: string | null;
  reason: string;
}

export interface JobOut {
  id: string;
  source: string;
  source_kind: string;
  filename: string | null;
  state: JobState;
  stats: Record<string, unknown>;
  errors: JobError[];
  created_at: string;
  updated_at: string;
}

export interface DocumentOut {
  id: string;
  source_type: string;
  source_kind: string;
  filename: string | null;
  title: string | null;
  sha256: string;
  chunk_count: number;
  created_at: string;
}

export interface ChunkOut {
  id: string;
  document_id: string;
  ordinal: number;
  text: string;
  meta: Record<string, unknown>;
}

// ---- Entities & relations ----
export type EntityType =
  | "Customer"
  | "SupportTicket"
  | "Incident"
  | "IncidentUpdate"
  | "Postmortem"
  | "Runbook"
  | "Service"
  | "Team"
  | "SLAContract"
  | "SLAClause"
  | "ErrorSignature"
  | "RootCause";

export type RelationType =
  | "REPORTED"
  | "RELATED_TO"
  | "AFFECTED"
  | "OWNED_BY"
  | "CAUSED_BY"
  | "HAS_UPDATE"
  | "MENTIONS"
  | "APPLIES_TO"
  | "PART_OF"
  | "CONSTRAINS"
  | "MAY_VIOLATE"
  | "MITIGATES"
  | "ANALYZES"
  | "EXHIBITS";

export interface EntityOut {
  id: string;
  type: EntityType | string;
  canonical_name: string;
  aliases: string[];
  attributes: Record<string, unknown>;
  confidence: number;
  method: string;
  merged_into: string | null;
}

export interface RelationOut {
  id: string;
  type: RelationType | string;
  source_id: string;
  target_id: string;
  confidence: number;
  method: string;
  deleted: boolean;
}

// ---- Graph ----
export interface GraphNode {
  id: string;
  type: EntityType | string;
  label: string;
  attributes: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  type: RelationType | string;
  source: string;
  target: string;
  confidence: number;
}

export interface GraphView {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ---- Ask ----
export type Confidence = "high" | "medium" | "low" | "insufficient";

export interface Citation {
  ref_id: string;
  kind: "chunk" | "entity";
  entity_type?: EntityType | string;
  snippet: string;
  source_document_id?: string | null;
  score: number;
}

export interface ReasoningStep {
  source_id: string;
  source_type: string;
  relation: string;
  target_id: string;
  target_type: string;
  relation_id: string;
}

export interface AnswerPlan {
  intent: string;
  entities: string[];
  time_range_days?: number | null;
  required_evidence_types: string[];
  keywords: string[];
}

export interface AnswerOut {
  id: string;
  question: string;
  answer: string;
  confidence: Confidence;
  confidence_score: number;
  citations: Citation[];
  reasoning_path: ReasoningStep[];
  actions: string[];
  limitations: string[];
  plan: AnswerPlan;
  created_at: string;
}

// ---- Evaluation ----
export interface EvalSummary {
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
  avg_entity_recall: number;
  avg_evidence_recall: number;
  avg_reasoning_recall: number;
  avg_theme_coverage: number;
  refusals: number;
}

export interface EvalResult {
  question_id: string;
  question: string;
  passed: boolean;
  metrics: Record<string, number>;
  expected: Record<string, unknown>;
  actual: Record<string, unknown>;
}

export interface EvalRunOut {
  id: string;
  started_at: string;
  finished_at: string | null;
  summary: EvalSummary;
  results: EvalResult[];
}

export type ReleaseGateStatus = "PASS" | "CONDITIONAL PASS" | "FAIL";

export interface ReleaseGate {
  status: ReleaseGateStatus;
  blockers: string[];
  warnings: string[];
  checks: Record<string, unknown>;
}
