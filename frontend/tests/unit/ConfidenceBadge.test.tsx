import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { confidenceClasses } from "@/lib/theme";

describe("confidenceClasses", () => {
  it("maps each level to distinct color tokens", () => {
    expect(confidenceClasses("high")).toContain("emerald");
    expect(confidenceClasses("medium")).toContain("amber");
    expect(confidenceClasses("low")).toContain("orange");
    expect(confidenceClasses("insufficient")).toContain("red");
  });

  it("uses refusal (red) styling for insufficient evidence", () => {
    // Refusals must be visually distinct from any grounded answer.
    expect(confidenceClasses("insufficient")).not.toEqual(
      confidenceClasses("high"),
    );
    expect(confidenceClasses("insufficient")).toContain("red");
  });
});

describe("ConfidenceBadge", () => {
  it("renders the human label and score", () => {
    render(<ConfidenceBadge confidence="high" score={0.92} />);
    expect(screen.getByText("High confidence")).toBeInTheDocument();
    expect(screen.getByText(/92%/)).toBeInTheDocument();
  });

  it("renders refusal label for insufficient", () => {
    render(<ConfidenceBadge confidence="insufficient" />);
    expect(screen.getByText("Insufficient evidence")).toBeInTheDocument();
  });
});
