import { Badge } from "./ui/Badge";
import { confidenceClasses } from "@/lib/theme";
import { percent } from "@/lib/format";
import type { Confidence } from "@/lib/types";

const LABELS: Record<Confidence, string> = {
  high: "High confidence",
  medium: "Medium confidence",
  low: "Low confidence",
  insufficient: "Insufficient evidence",
};

/**
 * Color-coded confidence badge. "insufficient" uses refusal (red) styling to
 * make source-grounding failures obvious to operators.
 */
export function ConfidenceBadge({
  confidence,
  score,
}: {
  confidence: Confidence;
  score?: number;
}) {
  return (
    <Badge className={confidenceClasses(confidence)} title={LABELS[confidence]}>
      <span
        className="h-1.5 w-1.5 rounded-full bg-current"
        aria-hidden="true"
      />
      {LABELS[confidence]}
      {typeof score === "number" ? (
        <span className="font-mono opacity-80">· {percent(score)}</span>
      ) : null}
    </Badge>
  );
}
