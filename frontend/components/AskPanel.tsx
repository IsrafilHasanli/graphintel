"use client";

import { useState } from "react";
import { ArrowUpRight, Command, Lightbulb, Send, Sparkles } from "lucide-react";
import { Card, CardBody, CardHeader } from "./ui/Card";
import { Button } from "./ui/Button";
import { TextArea } from "./ui/Field";
import { AnswerCard } from "./AnswerCard";
import { ErrorState, Loading } from "./ui/StateView";
import { api, ApiError } from "@/lib/api";
import type { AnswerOut } from "@/lib/types";

const GOLDEN_QUESTIONS = [
  "Which customers were affected by Payment API incidents in the last 30 days?",
  "Is Acme Corp at SLA risk because of checkout or payment incidents?",
  "Which engineering team owns the service involved in INC-247?",
  "What is the likely root cause of recurring checkout timeout tickets?",
  "Which runbook should be used for payment gateway timeout errors?",
];

export function AskPanel() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState<AnswerOut | null>(null);
  const [error, setError] = useState<Error | null>(null);

  async function submit(q: string) {
    const trimmed = q.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.ask({ question: trimmed });
      setAnswer(result);
    } catch (err) {
      setError(err instanceof ApiError ? err : (err as Error));
      setAnswer(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card className="rise-in overflow-hidden border-cyan-300/15">
        <CardHeader
          title={
            <span className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-cyan-300/10 text-cyan-200">
                <Sparkles size={15} aria-hidden="true" />
              </span>
              Ask the operational graph
            </span>
          }
          description="Answers are source-grounded. If evidence is insufficient the system refuses."
        />
        <CardBody>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void submit(question);
            }}
            className="flex flex-col gap-3"
          >
            <TextArea
              label="Question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              rows={3}
              placeholder="e.g. Which engineering team owns the service involved in INC-247?"
              onKeyDown={(e) => {
                if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                  e.preventDefault();
                  void submit(question);
                }
              }}
            />
              <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="inline-flex items-center gap-1.5 text-xs text-slate-500">
                <Command size={13} aria-hidden="true" />
                Ctrl/Cmd + Enter to submit
              </span>
              <Button
                type="submit"
                variant="primary"
                loading={loading}
                disabled={!question.trim()}
              >
                <Send size={14} aria-hidden="true" />
                Ask
              </Button>
            </div>
          </form>

          <div className="mt-4">
            <p className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-[0.14em] text-slate-400">
              <Lightbulb size={13} className="text-amber-300" aria-hidden="true" />
              Suggested investigations
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {GOLDEN_QUESTIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => {
                    setQuestion(q);
                    void submit(q);
                  }}
                  className="group flex items-start justify-between gap-3 rounded-md border border-surface-border bg-surface-panel/70 px-3 py-2.5 text-left text-xs leading-5 text-slate-300 transition-all hover:-translate-y-px hover:border-cyan-300/40 hover:bg-cyan-300/5 hover:text-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
                >
                  {q}
                  <ArrowUpRight size={14} className="mt-0.5 shrink-0 text-slate-600 transition-colors group-hover:text-cyan-300" aria-hidden="true" />
                </button>
              ))}
            </div>
          </div>
        </CardBody>
      </Card>

      <div aria-live="polite">
        {loading ? (
          <Card>
            <Loading label="Retrieving graph + vector evidence…" />
          </Card>
        ) : null}
        {error ? (
          <Card>
            <ErrorState error={error} onRetry={() => void submit(question)} />
          </Card>
        ) : null}
        {answer && !loading ? <AnswerCard answer={answer} /> : null}
      </div>
    </div>
  );
}
