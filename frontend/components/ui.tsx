import { fmt } from "@/lib/api";

/**
 * Counts are counts. Formatting a task total as "8.0" makes a dashboard look computed by
 * someone who never read the numbers, and it hides the one case that matters: a genuine
 * null has to stay visually distinct from a real zero.
 */
function renderValue(value: string | number | null): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
  }
  return value;
}

export function Stat({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: string | number | null;
  hint?: string;
  tone?: "neutral" | "critical" | "compliant" | "unresolved";
}) {
  const toneClass =
    tone === "critical"
      ? "text-verdict-critical"
      : tone === "compliant"
        ? "text-verdict-compliant"
        : tone === "unresolved"
          ? "text-verdict-unresolved"
          : "text-ink-100";

  return (
    <div className="card px-4 py-3">
      <div className="label">{label}</div>
      <div className={`num mt-1 text-[26px] leading-none ${toneClass}`}>
        {renderValue(value)}
      </div>
      {hint ? <div className="mt-1 text-[11px] text-ink-400">{hint}</div> : null}
    </div>
  );
}

/**
 * Dimension bar. Weight is shown as the track and the earned portion as the fill, so a
 * reviewer can see at a glance whether a low total came from a small dimension being empty
 * or a large one being missed.
 */
export function ScoreBar({
  name,
  points,
  weight,
  detail,
}: {
  name: string;
  points: number;
  weight: number;
  detail?: string;
}) {
  const pct = weight > 0 ? Math.max(0, Math.min(100, (points / weight) * 100)) : 0;
  const tone = pct >= 99.5 ? "bg-verdict-compliant" : pct <= 0.5 ? "bg-verdict-error" : "bg-verdict-critical";

  return (
    <div>
      <div className="flex items-baseline justify-between text-[12px]">
        <span className="text-ink-300">{name}</span>
        <span className="num text-ink-400">
          {fmt(points, 2)} / {weight}
        </span>
      </div>
      <div
        className="mt-1 h-[6px] w-full overflow-hidden rounded-sm bg-ink-800"
        role="img"
        aria-label={`${name}: ${fmt(points, 2)} of ${weight} points`}
      >
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      {detail ? <div className="mt-1 text-[11px] text-ink-400">{detail}</div> : null}
    </div>
  );
}

export function Pill({ children, tone = "neutral" }: { children: React.ReactNode; tone?: string }) {
  const map: Record<string, string> = {
    critical: "border-verdict-critical/40 text-verdict-critical",
    minor: "border-verdict-minor/40 text-verdict-minor",
    compliant: "border-verdict-compliant/40 text-verdict-compliant",
    unresolved: "border-verdict-unresolved/40 text-verdict-unresolved",
    error: "border-verdict-error/40 text-verdict-error",
    neutral: "border-ink-700 text-ink-300",
  };
  return (
    <span
      className={`inline-flex items-center rounded-sm border px-1.5 py-[1px] font-mono text-[11px] ${map[tone] ?? map.neutral}`}
    >
      {children}
    </span>
  );
}
