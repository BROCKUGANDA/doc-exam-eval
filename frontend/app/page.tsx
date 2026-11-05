import Link from "next/link";
import { api, fmt, type Coverage, type ProbeRow, type Results } from "@/lib/api";
import { Pill, Stat } from "@/components/ui";

export const dynamic = "force-dynamic";

/**
 * Command centre. Every number is read from the artifacts the CLI writes; nothing is
 * computed in the browser, and a missing artifact surfaces as an error rather than a zero.
 */
export default async function Home() {
  const [results, coverage, probe] = await Promise.all([
    api<Results>("/api/v1/results"),
    api<Coverage>("/api/v1/coverage"),
    api<{ probe: ProbeRow[] }>("/api/v1/providers"),
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
    <div className="space-y-8">
      <header className="max-w-3xl">
        <h1 className="text-[30px] font-semibold leading-tight tracking-tight">
          Can a model examine a letter of credit?
        </h1>
        <p className="mt-3 text-[15px] leading-relaxed text-ink-300">
          A bank has a fixed number of days to decide whether documents conform before it
          pays. This benchmark measures four things that decision depends on: detecting the
          discrepancy, naming its source document, applying the correct rule, and declining
          to decide what the evidence cannot establish. Reference answers are computed from
          the same document text the model reads, and the grader is tested against
          deliberately wrong answers before it is trusted with a single model output.
        </p>
      </header>

      <section aria-label="Headline figures" className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Stat label="Tasks" value={coverage.tasks} hint={`${coverage.clean_tasks} fully compliant`} />
        <Stat
          label="Ground-truth findings"
          value={coverage.total_ground_truth_findings}
          hint="computed, not typed"
        />
        <Stat label="Trials scored" value={`${scored}/${recorded}`} hint="unscored are provider errors" />
        <Stat
          label="Critical false clearances"
          value={clearances}
          tone={clearances > 0 ? "critical" : "compliant"}
          hint="trial forced to 0"
        />
        <Stat label="Models callable" value={callable} tone="unresolved" hint="from live probe" />
      </section>

      {best ? (
        <section className="card px-5 py-4">
          <div className="label">Best mean score so far</div>
          <div className="mt-2 flex flex-wrap items-baseline gap-3">
            <code className="font-mono text-[15px] text-ink-100">{best[0]}</code>
            <span className="num text-[26px] text-verdict-compliant">{fmt(best[1].overall_mean_total)}</span>
            <span className="text-[12px] text-ink-400">
              pass^k on {best[1].tasks_passed_hat_k}/{best[1].tasks_covered} tasks
            </span>
            <Link href="/results" className="link ml-auto text-[13px]">
              Full results →
            </Link>
          </div>
        </section>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="card p-5">
          <h2 className="text-[15px] font-semibold">How to read this console</h2>
          <ul className="mt-3 space-y-2 text-[13px] text-ink-300">
            <li>
              <Pill tone="critical">amber</Pill> a critical finding — the kind that should stop
              payment.
            </li>
            <li>
              <Pill tone="compliant">teal</Pill> compliant, or a dimension fully earned.
            </li>
            <li>
              <Pill tone="unresolved">violet</Pill> not established from the evidence; the
              correct behaviour is to escalate it, not to guess.
            </li>
            <li>
              <Pill tone="error">red</Pill> a dimension scored zero, or a trial that never
              reached the grader.
            </li>
          </ul>
          <p className="mt-3 text-[12px] leading-relaxed text-ink-400">
            Results appear only where a real request completed. A provider error is shown as
            a coverage gap, never as a zero, because a 429 is not a model limitation.
          </p>
        </div>

        <div className="card p-5">
          <h2 className="text-[15px] font-semibold">Coverage and warnings</h2>
          <p className="mt-2 text-[13px] text-ink-300">
            {coverage.rules_exercised}/{coverage.producer_rules} producer rules exercised by
            tasks; {coverage.codes_declared} codes declared.
          </p>
          {results.warnings.length === 0 ? (
            <p className="mt-3 text-[13px] text-verdict-compliant">No open warnings.</p>
          ) : (
            <ul className="mt-3 space-y-2 text-[12px] text-ink-300">
              {results.warnings.slice(0, 8).map((w, i) => (
                <li key={i} className="border-l-2 border-verdict-critical/50 pl-3">
                  {w}
                </li>
              ))}
              {results.warnings.length > 8 ? (
                <li className="text-ink-400">+{results.warnings.length - 8} more</li>
              ) : null}
            </ul>
          )}
          <Link href="/integrity" className="link mt-4 inline-block text-[13px]">
            How the grader was proven →
          </Link>
        </div>
      </section>
    </div>
  );
}
