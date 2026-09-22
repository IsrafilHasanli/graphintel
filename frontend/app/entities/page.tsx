"use client";

import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { TextInput, Select, Label } from "@/components/ui/Field";
import { Modal } from "@/components/ui/Modal";
import { AsyncView, EmptyState } from "@/components/ui/StateView";
import { EntityTable } from "@/components/EntityTable";
import { EntityChip } from "@/components/EntityChip";
import { RelationReviewPanel } from "@/components/RelationReviewPanel";
import { api, ApiError } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import { ENTITY_TYPES } from "@/lib/theme";
import { percent } from "@/lib/format";
import type { EntityOut } from "@/lib/types";

const ACTOR = "frontend-operator";

export default function EntitiesPage() {
  const [type, setType] = useState("");
  const [q, setQ] = useState("");
  const [includeMerged, setIncludeMerged] = useState(false);
  const [selected, setSelected] = useState<EntityOut | null>(null);

  const list = useAsync<EntityOut[]>(
    (s) =>
      api.entities(
        {
          type: type || undefined,
          q: q || undefined,
          include_merged: includeMerged,
          limit: 200,
        },
        s,
      ),
    [type, q, includeMerged],
  );

  return (
    <div>
      <PageHeader
        title="Entity review"
        description="Inspect, edit, merge duplicates, and correct relations from extraction."
      />

      <div className="grid gap-4 lg:grid-cols-[1fr_420px]">
        <Card>
          <CardHeader
            title="Entities"
            actions={
              <label className="flex items-center gap-1.5 text-xs text-slate-400">
                <input
                  type="checkbox"
                  checked={includeMerged}
                  onChange={(e) => setIncludeMerged(e.target.checked)}
                  className="accent-brand"
                />
                Show merged
              </label>
            }
          />
          <div className="flex flex-wrap items-end gap-2 border-b border-surface-border px-4 py-3">
            <div className="w-48">
              <Select
                label="Type"
                value={type}
                onChange={(e) => setType(e.target.value)}
              >
                <option value="">All types</option>
                {ENTITY_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </Select>
            </div>
            <div className="flex-1 min-w-[180px]">
              <TextInput
                label="Search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="name or alias…"
              />
            </div>
          </div>
          <CardBody className="p-0">
            <AsyncView
              status={list.status}
              data={list.data}
              error={list.error}
              onRetry={list.reload}
              isEmpty={(d) => d.length === 0}
              empty={
                <EmptyState
                  title="No entities"
                  description="Adjust filters or seed demo data."
                />
              }
            >
              {(data) => (
                <EntityTable
                  entities={data}
                  selectedId={selected?.id}
                  onSelect={setSelected}
                />
              )}
            </AsyncView>
          </CardBody>
        </Card>

        <EntityDetail
          entity={selected}
          entities={list.data ?? []}
          onChanged={(updated) => {
            setSelected(updated);
            list.reload();
          }}
          onMerged={() => {
            setSelected(null);
            list.reload();
          }}
        />
      </div>
    </div>
  );
}

function EntityDetail({
  entity,
  entities,
  onChanged,
  onMerged,
}: {
  entity: EntityOut | null;
  entities: EntityOut[];
  onChanged: (e: EntityOut) => void;
  onMerged: () => void;
}) {
  if (!entity) {
    return (
      <Card>
        <CardHeader title="Detail" description="Select an entity" />
        <CardBody>
          <p className="text-sm text-slate-400">
            Choose an entity to edit its name/aliases, merge duplicates, or review
            relations.
          </p>
        </CardBody>
      </Card>
    );
  }
  return <EntityDetailInner key={entity.id} entity={entity} entities={entities} onChanged={onChanged} onMerged={onMerged} />;
}

function EntityDetailInner({
  entity,
  entities,
  onChanged,
  onMerged,
}: {
  entity: EntityOut;
  entities: EntityOut[];
  onChanged: (e: EntityOut) => void;
  onMerged: () => void;
}) {
  const [name, setName] = useState(entity.canonical_name);
  const [aliases, setAliases] = useState((entity.aliases ?? []).join(", "));
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const [mergeOpen, setMergeOpen] = useState(false);
  const [mergeTarget, setMergeTarget] = useState("");
  const [mergeBusy, setMergeBusy] = useState(false);
  const [mergeError, setMergeError] = useState<string | null>(null);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    setSaved(false);
    try {
      const updated = await api.patchEntity(entity.id, {
        canonical_name: name.trim(),
        aliases: aliases
          .split(",")
          .map((a) => a.trim())
          .filter(Boolean),
        actor: ACTOR,
      });
      setSaved(true);
      onChanged(updated);
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : (err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function doMerge() {
    if (!mergeTarget) return;
    setMergeBusy(true);
    setMergeError(null);
    try {
      // Merge the currently selected entity (source) into the chosen target.
      await api.mergeEntities({
        source_id: entity.id,
        target_id: mergeTarget,
        actor: ACTOR,
      });
      setMergeOpen(false);
      onMerged();
    } catch (err) {
      setMergeError(err instanceof ApiError ? err.message : (err as Error).message);
    } finally {
      setMergeBusy(false);
    }
  }

  const mergeCandidates = entities.filter(
    (e) => e.id !== entity.id && e.type === entity.type && !e.merged_into,
  );

  return (
    <Card>
      <CardHeader
        title="Entity detail"
        description={entity.id}
        actions={
          <Button
            size="sm"
            variant="secondary"
            onClick={() => setMergeOpen(true)}
            disabled={!!entity.merged_into}
          >
            Merge…
          </Button>
        }
      />
      <CardBody className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <EntityChip type={entity.type} label={entity.type} />
          <Badge>conf {percent(entity.confidence)}</Badge>
          <Badge>{entity.method}</Badge>
          {entity.merged_into ? (
            <Badge className="border-amber-500/40 bg-amber-500/10 text-amber-300">
              merged → {entity.merged_into}
            </Badge>
          ) : null}
        </div>

        <form onSubmit={save} className="flex flex-col gap-3">
          <TextInput
            label="Canonical name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={!!entity.merged_into}
          />
          <TextInput
            label="Aliases (comma-separated)"
            value={aliases}
            onChange={(e) => setAliases(e.target.value)}
            disabled={!!entity.merged_into}
          />
          {Object.keys(entity.attributes ?? {}).length > 0 ? (
            <div>
              <Label htmlFor="attrs">Attributes (read-only)</Label>
              <pre
                id="attrs"
                className="max-h-40 overflow-auto rounded border border-surface-border bg-surface-panel p-2 font-mono text-[11px] text-slate-300"
              >
                {JSON.stringify(entity.attributes, null, 2)}
              </pre>
            </div>
          ) : null}
          {saveError ? (
            <p role="alert" className="text-xs text-red-300">
              {saveError}
            </p>
          ) : null}
          {saved ? (
            <p role="status" className="text-xs text-emerald-300">
              Saved.
            </p>
          ) : null}
          <div className="flex justify-end">
            <Button
              type="submit"
              size="sm"
              variant="primary"
              loading={saving}
              disabled={!!entity.merged_into}
            >
              Save changes
            </Button>
          </div>
        </form>

        <div className="border-t border-surface-border pt-3">
          <RelationReviewPanel entity={entity} />
        </div>
      </CardBody>

      <Modal
        open={mergeOpen}
        onClose={() => setMergeOpen(false)}
        title="Merge entities"
        footer={
          <>
            <Button variant="ghost" onClick={() => setMergeOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={mergeBusy}
              disabled={!mergeTarget}
              onClick={() => void doMerge()}
            >
              Merge
            </Button>
          </>
        }
      >
        <p className="mb-3 text-sm text-slate-300">
          Merge{" "}
          <span className="font-medium text-slate-100">
            {entity.canonical_name}
          </span>{" "}
          ({entity.id}) into a canonical target. The source will be marked
          merged and its relations re-pointed.
        </p>
        <Label htmlFor="merge-target">Target entity (same type)</Label>
        <Select
          id="merge-target"
          value={mergeTarget}
          onChange={(e) => setMergeTarget(e.target.value)}
        >
          <option value="">Select target…</option>
          {mergeCandidates.map((c) => (
            <option key={c.id} value={c.id}>
              {c.canonical_name} ({c.id})
            </option>
          ))}
        </Select>
        {mergeCandidates.length === 0 ? (
          <p className="mt-2 text-xs text-slate-500">
            No same-type candidates loaded. Broaden the list filters.
          </p>
        ) : null}
        {mergeError ? (
          <p role="alert" className="mt-2 text-xs text-red-300">
            {mergeError}
          </p>
        ) : null}
      </Modal>
    </Card>
  );
}
