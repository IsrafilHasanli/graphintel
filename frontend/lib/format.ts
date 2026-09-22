// Small presentation helpers shared across screens.

export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function formatDate(value?: string | null): string {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function relativeTime(value?: string | null): string {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const diffMs = Date.now() - d.getTime();
  const sec = Math.round(diffMs / 1000);
  if (Math.abs(sec) < 60) return `${sec}s ago`;
  const min = Math.round(sec / 60);
  if (Math.abs(min) < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (Math.abs(hr) < 24) return `${hr}h ago`;
  const day = Math.round(hr / 24);
  return `${day}d ago`;
}

export function percent(value?: number | null, digits = 0): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "-";
  return `${(value * 100).toFixed(digits)}%`;
}

export function truncate(text: string, max = 160): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}…`;
}

export function titleCase(text: string): string {
  return text
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
