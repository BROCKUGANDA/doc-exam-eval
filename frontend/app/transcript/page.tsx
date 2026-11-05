import Link from "next/link";
import { api, apiOptional, fmt, type Documents, type Trial } from "@/lib/api";
import { pageMetadata, webpageJsonLd } from "@/lib/site";
import { Pill, ScoreBar } from "@/components/ui";

export const dynamic = "force-dynamic";

export const metadata = pageMetadata({
  title: "Transcripts",
  description:
    "DOC-EXAM model transcripts: raw output, normalized output, per-dimension scores, and findings traced to the exact document page and line they cite.",
  path: "/transcript",
});

type Props = { searchParams: Promise<{ model?: string; task?: string; trial?: string }> };

/**
 * One trial, end to end: the settings that were sent, the raw bytes the model returned,
 * the per-dimension score, and a jump from every finding to the exact document line it
 * cites. This is the screen the guide asks for when it says the analysis must come from
 * reading transcripts — so the transcript is where the console lands.
 */
export default async function TranscriptPage({ searchParams }: Props) {
  const sp = await searchParams;
  const model = sp.model ?? "";
  const task = sp.task ?? "DOC-002";
  const trial = Number(sp.trial ?? 1);

  if (!model) {
    const results = await api<{ models: Record<string, unknown> }>("/api/v1/results");
    return (
      <div className="space-y-4">
        <h1 className="text-[22px] font-semibold">Transcripts</h1>
        <p className="text-[13px] text-ink-300">Pick a model to inspect its trials.</p>
        <ul className="card divide-y">
          {Object.keys(results.models).map((spec) => (
            <li key={spec}>
              <Link
                href={`/transcript?model=${encodeURIComponent(spec)}&task=DOC-002&trial=1`}
                className="focus-ring block px-4 py-3 font-mono text-[13px] text-verdict-minor hover:bg-ink-850"
              >
                {spec}
              </Link>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  const [rec, docs] = await Promise.all([
    apiOptional<Trial>(
      `/api/v1/transcripts?model=${encodeURIComponent(model)}&task=${task}&trial=${trial}`,
    ),
    api<Documents>(`/api/v1/tasks/${task}/documents`),
  ]);

  if (!rec) {
    return (
      <div className="space-y-5">
        <h1 className="text-[22px] font-semibold">No trial recorded for this combination</h1>
        <p className="max-w-2xl text-[13px] leading-relaxed text-ink-300">
          <code className="font-mono">{model}</code> on <code className="font-mono">{task}</code>{" "}
          trial {trial} has no completed request. The console shows only trials that actually
          ran — an absent trial is displayed as absent rather than as a score of zero, because
          a provider error and a model failure are different facts.
        </p>
        <div className="card p-4 text-[12px] text-ink-300">
          <div className="label">what to do</div>
          <ul className="mt-2 space-y-1">
            <li>
              Try another trial number, or{" "}
              <Link href="/results" className="link">pick a model with scored trials</Link>.
            </li>
            <li>
              Run the panel: <code className="font-mono">python run_eval.py --live</code>
            </li>
            <li>
              Regenerate results after a grader change:{" "}
              <code className="font-mono">python run_eval.py --regrade</code>
            </li>
          </ul>
        </div>
      </div>
    );
  }

  const card = rec.scorecard;
  const findings = parseFindings(rec.normalized_output ?? rec.raw_output ?? "");
  const docTitles = new Map(docs.documents.map((d) => [d.doc_id, d.title]));

  return (
    <div className="space-y-6">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: webpageJsonLd({
            title: "Transcripts",
            description:
              "DOC-EXAM model transcripts: raw output, normalized output, per-dimension scores, and findings traced to the exact document page and line they cite.",
            path: "/transcript",
          }),
        }}
      />
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="label">
            trial {rec.trial} · {rec.status}
          </div>
          <h1 className="mt-1 font-mono text-[18px]">{model}</h1>
          <Link href={`/tasks/${task}`} className="link text-[12px]">
            {task} — open the task
          </Link>
        </div>
        <div className="flex flex-wrap gap-1">
          <Pill tone={card?.passed ? "compliant" : "critical"}>
            {fmt(card?.total ?? null, 2)} / 100
          </Pill>
          <Pill>{fmt(rec.latency_s, 2)}s</Pill>
          <Pill>
            tok {rec.prompt_tokens_reported ?? "?"}→{rec.completion_tokens_reported ?? "?"}
          </Pill>
          {(card?.caps ?? []).map((c) => (
            <Pill key={c} tone="critical">
              {c}
            </Pill>
          ))}
        </div>
      </header>

      {rec.error ? (
        <div className="card border-verdict-error/40 p-4 text-[13px] text-verdict-error">
          {rec.error}
        </div>
      ) : null}

      <nav aria-label="Trial picker" className="flex flex-wrap gap-2 text-[12px]">
        {[1, 2, 3].map((n) => (
          <Link
            key={n}
            href={`/transcript?model=${encodeURIComponent(model)}&task=${task}&trial=${n}`}
            className={`focus-ring rounded border px-2 py-1 font-mono ${
              n === trial ? "border-verdict-minor text-verdict-minor" : "border-ink-700 text-ink-400"
            }`}
          >
            trial {n}
          </Link>
        ))}
      </nav>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <section className="space-y-4">
          <h2 className="text-[15px] font-semibold">Model output</h2>
          {rec.normalization.length > 0 ? (
            <p className="text-[11px] text-verdict-unresolved">
              normalised before grading: {rec.normalization.join("; ")}
            </p>
          ) : null}
          <pre className="doc-body card max-h-[640px] overflow-auto p-4 text-[11.5px]">
            {pretty(rec.raw_output ?? "")}
          </pre>
        </section>

        <aside className="space-y-4">
          {card ? (
            <div className="card space-y-3 p-4">
              <h2 className="text-[14px] font-semibold">Dimension scores</h2>
              {card.dimensions.map((d) => (
                <ScoreBar key={d.name} name={d.name} points={d.points} weight={d.weight} detail={d.detail} />
              ))}
            </div>
          ) : null}

          <div className="card p-4">
            <h2 className="text-[14px] font-semibold">Findings and where they came from</h2>
            {findings.length === 0 ? (
              <p className="mt-2 text-[12px] text-ink-400">
                The model reported no discrepancies.
              </p>
            ) : (
              <ul className="mt-3 space-y-3">
                {findings.map((f, i) => (
                  <li key={i} className="text-[12px]">
                    <div className="flex flex-wrap items-center gap-1">
                      <Pill tone={f.severity === "critical" ? "critical" : "minor"}>{f.severity}</Pill>
                      <code className="font-mono text-[11px]">{f.code}</code>
                      <code className="ml-auto font-mono text-[11px] text-ink-400">{f.rule}</code>
                    </div>
                    <ul className="mt-1 space-y-0.5">
                      {(f.evidence ?? []).map((e, j) => (
                        <li key={j}>
                          <a
                            href={`/tasks/${task}#doc-${e.document_id}`}
                            className="focus-ring rounded font-mono text-[11px] text-verdict-minor underline underline-offset-2"
                          >
                            {e.document_id} · p{e.page ?? "?"} · {truncate(e.location)}
                          </a>
                          <span className="ml-1 text-[11px] text-ink-400">{docTitles.get(e.document_id) ?? ""}</span>
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            )}

            {card && card.missed_findings.length > 0 ? (
              <p className="mt-3 text-[11px] text-verdict-critical">
                missed ground-truth findings: {card.missed_findings.join(", ")}
              </p>
            ) : null}
            {card && card.fabricated_findings.length > 0 ? (
              <ul className="mt-2 space-y-1 text-[11px] text-verdict-error">
                {card.fabricated_findings.map((f, i) => (
                  <li key={i}>
                    unsupported: {f.code}
                    {f.field ? ` on ${f.field}` : ""} — {f.why}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>

          <div className="card p-4 text-[11px] text-ink-400">
            <div className="label">settings sent</div>
            <pre className="mt-2 overflow-auto font-mono">{JSON.stringify(rec.settings, null, 1)}</pre>
            <div className="label mt-3">prompt sha256</div>
            <code className="mt-1 block break-all font-mono">{rec.prompt_sha256}</code>
          </div>
        </aside>
      </div>
    </div>
  );
}

function truncate(s: string | undefined): string {
  if (!s) return "(no location given)";
  return s.length > 46 ? `${s.slice(0, 43)}…` : s;
}

function pretty(text: string): string {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text || "(empty)";
  }
}

type ParsedFinding = {
  code?: string;
  severity?: string;
  rule?: string;
  evidence?: { document_id: string; page?: number; location?: string }[];
};

function parseFindings(text: string): ParsedFinding[] {
  try {
    const obj = JSON.parse(text);
    return Array.isArray(obj?.discrepancies) ? obj.discrepancies : [];
  } catch {
    return [];
  }
}
