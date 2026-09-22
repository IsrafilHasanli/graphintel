"use client";

import { useState } from "react";
import { Button } from "./ui/Button";
import { TextInput, Select, Label } from "./ui/Field";
import { Badge } from "./ui/Badge";
import { AsyncView } from "./ui/StateView";
import { RELATION_TYPES } from "@/lib/theme";
import { percent } from "@/lib/format";
import { api, ApiError } from "@/lib/api";
import { useAsync } from "@/lib/useAsync";
import type { EntityOut, RelationOut } from "@/lib/types";

const ACTOR = "frontend-operator";

/**
 * Shows relations for the selected entity with delete (reasoned) and an
 * add-relation form that surfaces 422 ontology violations inline.
 */
export function RelationReviewPanel({ entity }: { entity: EntityOut }) {
  const state = useAsync<RelationOut[]>(
    (signal) => api.relations({ entity: entity.id, limit: 100 }, signal),
    [entity.id],
  );

  const [newType, setNewType] = useState<string>("RELATED_TO");
  const [newSource, setNewSource] = useState(entity.id);
  const [newTarget, setNewTarget] = useState("");
  const [addError, setAddError] = useState<string | null>(null);
  const [addBusy, setAddBusy] = useState(false);

  async function addRelation(e: React.FormEvent) {
    e.preventDefault();
    if (!newSource.trim() || !newTarget.trim()) return;
    setAddBusy(true);
    setAddError(null);
    try {
      await api.createRelation({
        type: newType,
        source_id: newSource.trim(),
        target_id: newTarget.trim(),
        actor: ACTOR,
      });
      setNewTarget("");
      state.reload();
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        setAddError(`Ontology violation: ${err.message}`);
      } else {
        setAddError(err instanceof Error ? err.message : "Failed to add relation");
      }
    } finally {
      setAddBusy(false);
    }
  }

  async function removeRelation(rel: RelationOut) {
    const reason = window.prompt(
      `Reason for deleting ${rel.type} (${rel.source_id} → ${rel.target_id})?`,
      "incorrect extraction",
    );
    if (reason === null) return;
    try {
      await api.deleteRelation(rel.id, { reason, actor: ACTOR });
      state.setData((prev) =>
        (prev ?? []).map((r) =>
          r.id === rel.id ? { ...r, deleted: true } : r,
        ),
      );
    } catch (err) {
      window.alert(
        err instanceof Error ? err.message : "Failed to delete relation",
      );
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Relations
        </h3>
        <AsyncView
          status={state.status}
          data={state.data}
          error={state.error}
          onRetry={state.reload}
          isEmpty={(d) => d.length === 0}
          loadingLabel="Loading relations…"
          empty={<p className="text-xs text-slate-500">No relations found.</p>}
        >
          {(relations) => (
            <ul className="flex flex-col gap-1.5">
              {relations.map((r) => (
                <li
                  key={r.id}
                  className="flex items-center justify-between gap-2 rounded border border-surface-border bg-surface-panel/60 px-2 py-1.5 text-xs"
                >
                  <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                    <span className="font-mono text-slate-400">
                      {r.source_id}
                    </span>
                    <Badge className="border-brand/40 bg-brand/10 text-brand-fg">
                      {r.type}
                    </Badge>
                    <span className="font-mono text-slate-400">
                      {r.target_id}
                    </span>
                    <span className="text-slate-500">
                      · {percent(r.confidence)}
                    </span>
                    {r.deleted ? (
                      <Badge className="border-red-500/40 bg-red-500/10 text-red-300">
                        deleted
                      </Badge>
                    ) : null}
                  </div>
                  {!r.deleted ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-red-300 hover:bg-red-500/10"
                      onClick={() => void removeRelation(r)}
                    >
                      Delete
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </AsyncView>
      </div>

      <form
        onSubmit={addRelation}
        className="rounded-md border border-surface-border bg-surface-panel/40 p-3"
      >
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Add relation
        </h3>
        <div className="grid grid-cols-2 gap-2">
          <TextInput
            label="Source id"
            value={newSource}
            onChange={(e) => setNewSource(e.target.value)}
            required
          />
          <TextInput
            label="Target id"
            value={newTarget}
            onChange={(e) => setNewTarget(e.target.value)}
            placeholder="SVC-1"
            required
          />
        </div>
        <div className="mt-2">
          <Label htmlFor="rel-type">Relation type</Label>
          <Select
            id="rel-type"
            value={newType}
            onChange={(e) => setNewType(e.target.value)}
          >
            {RELATION_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </Select>
        </div>
        {addError ? (
          <p role="alert" className="mt-2 text-xs text-red-300">
            {addError}
          </p>
        ) : null}
        <div className="mt-3 flex justify-end">
          <Button
            type="submit"
            size="sm"
            variant="primary"
            loading={addBusy}
            disabled={!newTarget.trim()}
          >
            Add relation
          </Button>
        </div>
      </form>
    </div>
  );
}
