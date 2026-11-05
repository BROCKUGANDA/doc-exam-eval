import { api, type Coverage, type Rulebook } from "@/lib/api";
import { Pill } from "@/components/ui";

export const dynamic = "force-dynamic";

export default async function RulebookPage() {
  const [rb, cov] = await Promise.all([
    api<Rulebook>("/api/v1/rulebook"),
    api<Coverage>("/api/v1/coverage"),
  ]);

  const exercised = new Set<string>();
  // A rule is exercised if any task's ground truth cites it; coverage gives the counts,
  // the per-rule detail comes from the codes the tasks actually produced.
  for (const code of Object.keys(rb.code_to_rules)) {
    if (!cov.codes_never_exercised.includes(code)) {
      rb.code_to_rules[code].forEach((r) => exercised.add(r));
    }
  }

  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <h1 className="text-[22px] font-semibold tracking-tight">Rulebook</h1>
        <p className="mt-2 text-[13px] leading-relaxed text-ink-300">
          The governing standard handed to every model, in full, inside the prompt. It is
          written for this benchmark rather than copied from ICC publications, so no model can
          fail because a rule was left unstated and no licensed text is redistributed.
          Severity is declared here, which is what turns &ldquo;is this critical or minor&rdquo;
          from an opinion into a lookup — and what makes that judgment explicitly the
          examiner&rsquo;s to review.
        </p>
        <p className="mt-2 font-mono text-[11px] text-ink-400">
          version {rb.version} · fingerprint {rb.fingerprint} · {rb.rules.length} rules ·{" "}
          {rb.codes.length} codes · {cov.rules_exercised}/{cov.producer_rules} producer rules
          exercised by tasks
        </p>
      </header>

      <div className="space-y-3">
        {rb.rules.map((r) => (
          <article key={r.id} className="card p-4">
            <header className="flex flex-wrap items-baseline gap-2">
              <code className="font-mono text-[13px] text-verdict-minor">{r.id}</code>
              <h2 className="text-[14px]">{r.title}</h2>
              <span className="ml-auto flex gap-1">
                <Pill tone={r.severity === "critical" ? "critical" : r.severity === "minor" ? "minor" : "neutral"}>
                  {r.severity}
                </Pill>
                <Pill tone={exercised.has(r.id) ? "compliant" : "unresolved"}>
                  {exercised.has(r.id) ? "exercised" : "not exercised"}
                </Pill>
              </span>
            </header>
            <p className="mt-2 text-[13px] leading-relaxed text-ink-300">{r.statement}</p>
            <div className="mt-2 flex flex-wrap gap-1">
              {r.codes.map((c) => (
                <code key={c} className="rounded-sm border border-ink-700 px-1.5 py-[1px] font-mono text-[11px] text-ink-400">
                  {c}
                </code>
              ))}
            </div>
            <div className="mt-2 text-[11px] text-ink-400">
              kind <code className="font-mono">{r.kind}</code> · applies to{" "}
              {r.applies_to.docs.join(", ")} / {r.applies_to.fields.join(", ")}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
