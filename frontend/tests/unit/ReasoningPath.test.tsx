import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReasoningPath } from "@/components/ReasoningPath";
import type { ReasoningStep } from "@/lib/types";

const STEPS: ReasoningStep[] = [
  {
    source_id: "INC-247",
    source_type: "Incident",
    relation: "AFFECTED",
    target_id: "SVC-payments",
    target_type: "Service",
    relation_id: "r1",
  },
  {
    source_id: "SVC-payments",
    source_type: "Service",
    relation: "OWNED_BY",
    target_id: "TEAM-pay",
    target_type: "Team",
    relation_id: "r2",
  },
];

describe("ReasoningPath", () => {
  it("renders each ordered traversal step with its relation label", () => {
    render(<ReasoningPath steps={STEPS} />);
    expect(screen.getByText("AFFECTED")).toBeInTheDocument();
    expect(screen.getByText("OWNED_BY")).toBeInTheDocument();
    // Ordered list with two steps.
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
  });

  it("shows an empty state when there is no path", () => {
    render(<ReasoningPath steps={[]} />);
    expect(screen.getByText(/No graph reasoning path/i)).toBeInTheDocument();
  });

  it("links entities into the graph explorer", () => {
    render(<ReasoningPath steps={STEPS} />);
    const links = screen.getAllByRole("link");
    expect(links.some((l) => l.getAttribute("href")?.includes("seed=INC-247"))).toBe(
      true,
    );
  });
});
