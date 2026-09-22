import { Table, THead, TH, TR, TD } from "./ui/Table";
import { Badge } from "./ui/Badge";
import { EntityChip } from "./EntityChip";
import { percent, truncate } from "@/lib/format";
import type { EntityOut } from "@/lib/types";

export function EntityTable({
  entities,
  selectedId,
  onSelect,
}: {
  entities: EntityOut[];
  selectedId?: string | null;
  onSelect: (entity: EntityOut) => void;
}) {
  return (
    <Table>
      <THead>
        <tr>
          <TH>Type</TH>
          <TH>Canonical name</TH>
          <TH>Aliases</TH>
          <TH className="text-right">Conf.</TH>
          <TH>Method</TH>
        </tr>
      </THead>
      <tbody>
        {entities.map((e) => (
          <TR
            key={e.id}
            onClick={() => onSelect(e)}
            selected={e.id === selectedId}
          >
            <TD>
              <EntityChip type={e.type} label={e.type} />
            </TD>
            <TD>
              <span className="font-medium text-slate-100">
                {e.canonical_name}
              </span>
              <span className="ml-2 font-mono text-[10px] text-slate-500">
                {e.id}
              </span>
              {e.merged_into ? (
                <Badge className="ml-2 border-amber-500/40 bg-amber-500/10 text-amber-300">
                  merged → {e.merged_into}
                </Badge>
              ) : null}
            </TD>
            <TD className="text-xs text-slate-400">
              {e.aliases?.length ? truncate(e.aliases.join(", "), 48) : "-"}
            </TD>
            <TD className="text-right font-mono text-xs text-slate-300">
              {percent(e.confidence)}
            </TD>
            <TD className="text-xs text-slate-400">{e.method}</TD>
          </TR>
        ))}
      </tbody>
    </Table>
  );
}
