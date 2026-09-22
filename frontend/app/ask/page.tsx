import { PageHeader } from "@/components/PageHeader";
import { AskPanel } from "@/components/AskPanel";

export const metadata = { title: "Ask — GraphIntel" };

export default function AskPage() {
  return (
    <div>
      <PageHeader
        title="Ask"
        description="Source-grounded answers with citations, reasoning path, and confidence."
      />
      <AskPanel />
    </div>
  );
}
