import Link from "next/link";
import { api, fmt, type Results } from "@/lib/api";
import { Pill } from "@/components/ui";

export const dynamic = "force-dynamic";

const TASKS = Array.from({ length: 8 }, (_, i) => `DOC-00${i + 1}`);

export default async function ResultsPage() {
  const results = await api<Results>("/api/v1/results");
  const models = Object.entries(results.models);

  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <h1 className="text-[22px] font-semibold tracking-tight">Results</h1>
        <p className="mt-2 text-[13px] leading-relaxed text-ink-300">
          pass@k is &ldquo;succeeded at least once in k tries&rdquo;; pass^k is
          &ldquo;succeeded every time&rdquo;. A bank cannot afford the first definition, so
          pass^k across {results.totals.trials_per_task ?? 3} trials is the number that
          matters for professional work.
        </p>
      </header>

      <div className="card overflow-x-auto">
        <table className="w-full min-w-[900px] text-[13px]">
          <caption className="sr-only">Model comparison</caption>
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-[0.12em] text-ink-400">
              <th className="px-4 py-2 font-normal">Model</th>
              <th className="px-4 py-2 font-normal">Scored</th>
              <th className="px-4 py-2 font-normal">Mean</th>
              <th className="px-4 py-2 font-normal">pass^k tasks</th>
              <th className="px-4 py-2 font-normal">Critical FC</th>
              <th className="px-4 py-2 font-normal">Prompt tok</th>
              <th className="px-4 py-2 font-normal">Latency</th>
            </tr>
          </thead>
          <tbody>
            {models.map(([spec, m]) => (
              <tr key={spec} className="border-t rule">
                <td className="px-4 py-3">
                  <code className="font-mono text-[12px]">{spec}</code>
                  {Object.keys(m.status_counts).length > 1 ? (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {Object.entries(m.status_counts).map(([s, n]) => (
                        <Pill key={s} tone={s === "ok" ? "neutral" : "error"}>
                          {s}:{n}
                        </Pill>
                      ))}
                    </div>
                  ) : null}
                </td>
                <td className="num px-4 py-3">
                  {m.trials_scored}/{m.trials_recorded}
                </td>
                <td className="num px-4 py-3 text-verdict-compliant">{fmt(m.overall_mean_total, 2)}</td>
                <td className="num px-4 py-3">
                  {m.tasks_passed_hat_k}/{m.tasks_covered}
                </td>
                <td className={`num px-4 py-3 ${m.critical_false_clearances ? "text-verdict-critical" : ""}`}>
                  {m.critical_false_clearances}
                </td>
                <td className="num px-4 py-3 text-ink-400">{fmt(m.mean_prompt_tokens, 0)}</td>
                <td className="num px-4 py-3 text-ink-400">
                  {/* "—s" is a dash with a unit stuck to it. A model with no scored trials has no
                      latency, and rendering the unit makes an absence look like a measurement. */}
                  {m.mean_latency_s === null || m.mean_latency_s === undefined
                    ? "—"
                    : `${fmt(m.mean_latency_s, 2)}s`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 className="pt-2 text-[15px] font-semibold">Per task</h2>
      <div className="card overflow-x-auto">
        <table className="w-full min-w-[900px] text-[12.5px]">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-[0.12em] text-ink-400">
              <th className="px-4 py-2 font-normal">Task</th>
              {models.map(([spec]) => (
                <th key={spec} className="px-3 py-2 font-normal">
                  <span className="block max-w-[150px] truncate font-mono text-[11px] normal-case">
                    {spec.split(":")[1] ?? spec}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {TASKS.map((task) => (
              <tr key={task} className="border-t rule">
                <td className="px-4 py-2">
                  <Link href={`/tasks/${task}`} className="link font-mono text-[12px]">
                    {task}
                  </Link>
                </td>
                {models.map(([spec, m]) => {
                  const t = m.per_task[task];
                  if (!t) return <td key={spec} className="px-3 py-2 text-ink-600">—</td>;
                  const tone = t.pass_hat_k ? "text-verdict-compliant" : t.pass_at_k ? "text-verdict-critical" : "text-verdict-error";
                  return (
                    <td key={spec} className="px-3 py-2">
                      <Link
                        href={`/transcript?model=${encodeURIComponent(spec)}&task=${task}&trial=1`}
                        className={`focus-ring num block rounded font-mono ${tone} hover:underline`}
                      >
                        {fmt(t.mean_total, 1)}
                        <span className="ml-1 text-[10px] text-ink-400">
                          {t.pass_hat_k ? "^k" : t.pass_at_k ? "@k" : "0"}
                        </span>
                      </Link>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {results.warnings.length > 0 ? (
        <section className="card p-5">
          <h2 className="text-[15px] font-semibold text-verdict-critical">
            Coverage and ordering warnings
          </h2>
          <ul className="mt-3 space-y-2 text-[12px] text-ink-300">
            {results.warnings.map((w, i) => (
              <li key={i} className="border-l-2 border-verdict-critical/50 pl-3">
                {w}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
