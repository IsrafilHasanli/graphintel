import { Card, CardBody, CardHeader } from "./ui/Card";
import { Badge } from "./ui/Badge";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { CitationList } from "./CitationList";
import { ReasoningPath } from "./ReasoningPath";
import { cx, formatDate, titleCase } from "@/lib/format";
import type { AnswerOut } from "@/lib/types";

/**
 * Prominent answer presentation with confidence, plan, citations, reasoning
 * path, suggested actions, and limitations. Insufficient answers get refusal
 * styling so operators never mistake a refusal for a grounded answer.
 */
export function AnswerCard({ answer }: { answer: AnswerOut }) {
  const insufficient = answer.confidence === "insufficient";

  return (
    <div className="flex flex-col gap-4">
      <Card
        as="article"
        className={cx(
          insufficient && "border-red-500/50",
        )}
      >
        <div
          className={cx(
            "flex flex-wrap items-start justify-between gap-3 border-b px-4 py-3",
            insufficient
              ? "border-red-500/40 bg-red-500/10"
              : "border-surface-border",
          )}
        >
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">
              Answer
            </p>
            <h2 className="mt-0.5 text-sm font-semibold text-slate-100">
              {answer.question}
            </h2>
          </div>
          <ConfidenceBadge
            confidence={answer.confidence}
            score={answer.confidence_score}
          />
        </div>
        <CardBody>
          <div
            aria-live="polite"
            className={cx(
              "whitespace-pre-wrap text-sm leading-relaxed",
              insufficient ? "text-red-200" : "text-slate-100",
            )}
          >
            {answer.answer}
          </div>

          {answer.actions?.length ? (
            <div className="mt-4">
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                Suggested actions
              </h3>
              <ul className="list-inside list-disc space-y-1 text-sm text-slate-300">
                {answer.actions.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {answer.limitations?.length ? (
            <div className="mt-4 rounded-md border border-amber-500/30 bg-amber-500/10 p-3">
              <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-300">
                Limitations / partial evidence
              </h3>
              <ul className="list-inside list-disc space-y-1 text-sm text-amber-200/90">
                {answer.limitations.map((l, i) => (
                  <li key={i}>{l}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </CardBody>
      </Card>

      {answer.plan ? (
        <Card>
          <CardHeader title="Query plan" description="Parsed intent & retrieval strategy" />
          <CardBody className="flex flex-col gap-2 text-xs text-slate-300">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-slate-500">Intent</span>
              <Badge className="border-brand/40 bg-brand/10 text-brand-fg">
                {titleCase(answer.plan.intent || "unknown")}
              </Badge>
              {typeof answer.plan.time_range_days === "number" ? (
                <Badge>{answer.plan.time_range_days}d window</Badge>
              ) : null}
            </div>
            {answer.plan.entities?.length ? (
              <PlanRow label="Entities" items={answer.plan.entities} />
            ) : null}
            {answer.plan.required_evidence_types?.length ? (
              <PlanRow
                label="Required evidence"
                items={answer.plan.required_evidence_types}
              />
            ) : null}
            {answer.plan.keywords?.length ? (
              <PlanRow label="Keywords" items={answer.plan.keywords} />
            ) : null}
          </CardBody>
        </Card>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Citations"
            description={`${answer.citations?.length ?? 0} source(s)`}
          />
          <CardBody>
            <CitationList citations={answer.citations ?? []} />
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Reasoning path"
            description={`${answer.reasoning_path?.length ?? 0} graph step(s)`}
          />
          <CardBody>
            <ReasoningPath steps={answer.reasoning_path ?? []} />
          </CardBody>
        </Card>
      </div>

      <p className="text-right font-mono text-[10px] text-slate-500">
        answer {answer.id} · {formatDate(answer.created_at)}
      </p>
    </div>
  );
}

function PlanRow({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-slate-500">{label}</span>
      {items.map((item, i) => (
        <Badge key={`${item}-${i}`}>{item}</Badge>
      ))}
    </div>
  );
}
