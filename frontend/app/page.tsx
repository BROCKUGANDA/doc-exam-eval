import Link from "next/link";
import { api, fmt, type Coverage, type ProbeRow, type Results } from "@/lib/api";
import { pageMetadata, webpageJsonLd, siteUrl } from "@/lib/site";
import { Pill, Stat } from "@/components/ui";

export const dynamic = "force-dynamic";

const homepageTitle = "DOC-EXAM — evidence-first AI benchmark";
const homepageDescription =
  "A reproducible benchmark testing whether AI models can examine documentary-credit presentations, detect discrepancies, cite evidence, apply rules and abstain when evidence is insufficient.";

export const metadata = pageMetadata({
  title: "Evidence-first AI benchmark",
  description: homepageDescription,
  path: "/",
});

export default async function Home() {
  const [results, coverage, probe, integrity] = await Promise.all([
    api<Results>("/api/v1/results"),
    api<Coverage>("/api/v1/coverage"),
    api<{ probe: ProbeRow[] }>("/api/v1/providers"),
    api<{ fixture_total: number }>("/api/v1/integrity"),
  ]);

  const models = Object.entries(results.models);
  const scored = models.reduce((a, [, m]) => a + m.trials_scored, 0);
  const recorded = models.reduce((a, [, m]) => a + m.trials_recorded, 0);
  const clearances = models.reduce((a, [, m]) => a + m.critical_false_clearances, 0);
  const best = models
    .filter(([, m]) => m.overall_mean_total !== null)
    .sort((a, b) => (b[1].overall_mean_total ?? 0) - (a[1].overall_mean_total ?? 0))[0];
  const callable = probe.probe.filter((r) => r.status === "ok").length;

  return (
    <div className="space-y-10">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify([
            JSON.parse(webpageJsonLd({ title: homepageTitle, description: homepageDescription, path: "/" })),
            {
              "@context": "https://schema.org",
              "@type": "Dataset",
              "@id": siteUrl("/#benchmark-dataset"),
              name: "DOC-EXAM documentary credit benchmark",
              description: homepageDescription,
              url: siteUrl("/"),
              inLanguage: "en",
              keywords: ["documentary credit", "letter of credit", "trade finance", "AI evaluation", "benchmark"],
            },
          ]),
        }}
      />
      <section className="hero-panel relative overflow-hidden rounded-xl border border-ink-700 px-6 py-10 sm:px-9 sm:py-14">
        <div className="hero-grid pointer-events-none absolute inset-0" aria-hidden="true" />
        <div className="relative max-w-4xl">
          <div className="mb-5 flex flex-wrap items-center gap-2">
            <Pill tone="compliant">REPRODUCIBLE BENCHMARK</Pill>
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-400">
              Trade finance · Documentary credit · AI evaluation
            </span>
          </div>
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-verdict-minor">
            The evidence is the test.
          </p>
          <h1 className="mt-4 max-w-4xl text-4xl font-semibold leading-[1.05] tracking-[-0.04em] text-white sm:text-6xl">
            Can an AI model know when a bank should <span className="text-verdict-minor">not pay?</span>
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-7 text-ink-300 sm:text-lg">
            DOC-EXAM tests whether models can find every material discrepancy in a letter-of-credit
            presentation, trace each finding to its source, apply the supplied rulebook, and refuse
            to guess when the evidence cannot establish an answer.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/tasks" className="action-primary">Explore benchmark tasks <span aria-hidden="true">↗</span></Link>
            <Link href="/results" className="action-secondary">Inspect model results <span aria-hidden="true">→</span></Link>
            <Link href="/integrity" className="action-secondary">Verify grader integrity <span aria-hidden="true">→</span></Link>
          </div>
          <div className="mt-10 grid max-w-2xl grid-cols-2 gap-4 border-t border-white/10 pt-5 sm:grid-cols-3">
            <div><div className="font-mono text-2xl text-white">{coverage.tasks}</div><div className="label mt-1">Scenarios</div></div>
            <div><div className="font-mono text-2xl text-white">{coverage.producer_rules}</div><div className="label mt-1">Producer rules</div></div>
            <div><div className="font-mono text-2xl text-white">{integrity.fixture_total}</div><div className="label mt-1">Grader fixtures</div></div>
          </div>
          <p className="mt-3 text-[10px] text-ink-500">Counts are read from the benchmark API artifacts; test totals are reported by the reproducible test command, not hardcoded here.</p>
        </div>
      </section>

      <section aria-label="Live benchmark evidence" className="space-y-3">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div><p className="label">01 / Live evidence</p><h2 className="mt-1 text-xl font-semibold">The benchmark, not the pitch deck.</h2></div>
          <span className="font-mono text-[10px] uppercase tracking-wider text-ink-500">Read from benchmark artifacts</span>
        </div>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <Stat label="Tasks" value={coverage.tasks} hint={`${coverage.clean_tasks} fully compliant control`} />
          <Stat label="Ground-truth findings" value={coverage.total_ground_truth_findings} hint="computed from documents + rules" />
          <Stat label="Trials scored" value={`${scored}/${recorded}`} hint="provider errors remain unscored" />
          <Stat label="Critical false clearances" value={clearances} tone={clearances > 0 ? "critical" : "compliant"} hint="hard-capped trial failures" />
          <Stat label="Models callable" value={callable} tone="unresolved" hint="latest recorded provider probe" />
        </div>
        {best ? (
          <div className="card flex flex-wrap items-center gap-4 px-5 py-4">
            <div className="min-w-0 flex-1"><p className="label">Current leading measured model</p><code className="mt-1 block truncate text-sm text-ink-100">{best[0]}</code></div>
            <div className="text-right"><div className="num text-3xl text-verdict-compliant">{fmt(best[1].overall_mean_total)}</div><div className="label">Mean / 100</div></div>
            <Link href="/results" className="link text-sm">Open full scorecards →</Link>
          </div>
        ) : null}
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="card p-5 sm:p-6">
          <p className="label">02 / Evaluation method</p>
          <h2 className="mt-2 text-xl font-semibold">Four questions. One defensible decision.</h2>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            {[
              ["01", "Detection", "Did the model find the discrepancy that is actually present?"],
              ["02", "Evidence", "Can every finding be traced to a real document and field?"],
              ["03", "Rule application", "Did it apply the governing rule and severity correctly?"],
              ["04", "Restraint", "Did it abstain when the evidence is ambiguous or insufficient?"],
            ].map(([n, title, body]) => (
              <div key={n} className="border-l border-verdict-minor/50 pl-4">
                <span className="font-mono text-xs text-verdict-minor">{n}</span>
                <h3 className="mt-1 text-sm font-semibold text-ink-100">{title}</h3>
                <p className="mt-1 text-xs leading-5 text-ink-400">{body}</p>
              </div>
            ))}
          </div>
          <p className="mt-5 border-t border-ink-700 pt-4 text-xs leading-5 text-ink-400">
            Scoring is deterministic. The grader does not ask another language model to decide whether
            an answer is correct. Hard caps prevent a high partial score from hiding a critical false clearance.
          </p>
        </div>
        <div className="card p-5 sm:p-6">
          <p className="label">03 / Integrity and limitations</p>
          <h2 className="mt-2 text-xl font-semibold">Show the gaps, too.</h2>
          <p className="mt-3 text-sm leading-6 text-ink-300">
            {coverage.rules_exercised} of {coverage.producer_rules} producer rules are exercised by the current task pack.
            Provider errors are not silently scored as model failures.
          </p>
          {results.warnings.length ? (
            <ul className="mt-4 space-y-2 text-xs leading-5 text-ink-300">
              {results.warnings.map((w, i) => <li key={i} className="border-l-2 border-verdict-critical/60 pl-3">{w}</li>)}
            </ul>
          ) : <p className="mt-4 text-xs text-verdict-compliant">No runtime warnings in the current result artifact.</p>}
          <Link href="/integrity" className="link mt-5 inline-block text-sm">Inspect fixtures, mutations and caps →</Link>
        </div>
      </section>

      <section className="card flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
        <div className="max-w-2xl">
          <p className="label">04 / Reproduce it yourself</p>
          <h2 className="mt-2 text-xl font-semibold">No API key. No database. No Docker required.</h2>
          <p className="mt-2 text-sm leading-6 text-ink-400">
            Clone the repository, install the pinned development dependencies and run the validation
            harness. It regenerates the documents, recomputes reference answers and checks that
            deliberately incorrect outputs are rejected.
          </p>
        </div>
        <a className="action-secondary shrink-0" href="https://github.com/BROCKUGANDA/doc-exam-eval" target="_blank" rel="noreferrer">Source repository ↗</a>
      </section>

      <p className="text-[11px] leading-5 text-ink-500">
        DOC-EXAM is a research benchmark using synthetic documents and an authored rulebook. It is not
        a bank examination service, legal opinion, ICC certification, or automated payment decision system.
        Human examiner review and raw-PDF/OCR evaluation remain separate validation requirements.
      </p>
    </div>
  );
}
