import { api } from "@/lib/api";
import { Pill } from "@/components/ui";

export const dynamic = "force-dynamic";

type Integrity = {
  fixtures_by_task: Record<string, string[]>;
  fixture_total: number;
  grader_levers: Record<string, string>;
  index_levers: Record<string, string>;
  rulebook_version: string;
  rulebook_fingerprint: string;
};

type Coverage = { rules_exercised: number; producer_rules: number; rules_never_exercised: string[]; codes_declared: number; codes_never_exercised: string[]; tasks: number };

export default async function IntegrityPage() {
  const [data, cov] = await Promise.all([
    api<Integrity>("/api/v1/integrity"),
    api<Coverage>("/api/v1/coverage"),
  ]);

  return (
    <div className="space-y-6">
      <header className="max-w-3xl">
        <h1 className="text-[22px] font-semibold tracking-tight">Grader integrity</h1>
        <p className="mt-2 text-[13px] leading-relaxed text-ink-300">
          A grader that has never rejected a wrong answer is untested, and a suite that cannot
          notice a broken grader is decoration. This screen shows both halves: the corpus of
          deliberately wrong answers the grader must reject, and the levers the mutation suite
          breaks to prove the corpus can actually fail.
        </p>
        <p className="mt-2 font-mono text-[11px] text-ink-400">
          rulebook {data.rulebook_version} · fingerprint {data.rulebook_fingerprint}
        </p>
      </header>

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="card p-5">
          <div className="label">Wrong-answer fixtures</div>
          <div className="num mt-1 text-[30px] text-verdict-compliant">{data.fixture_total}</div>
          <p className="mt-1 text-[12px] text-ink-400">
            across {cov.tasks} tasks, each asserting a specific lever rather than a bare
            pass/fail.
          </p>
        </div>
        <div className="card p-5">
          <div className="label">Grader levers mutated</div>
          <div className="num mt-1 text-[30px] text-verdict-compliant">
            {Object.keys(data.grader_levers).length + Object.keys(data.index_levers).length}
          </div>
          <p className="mt-1 text-[12px] text-ink-400">
            each must make the corpus go red, and the corpus must go green again once restored.
          </p>
        </div>
        <div className="card p-5">
          <div className="label">Rules exercised</div>
          <div className="num mt-1 text-[30px]">
            {cov.rules_exercised}/{cov.producer_rules}
          </div>
          <p className="mt-1 text-[12px] text-ink-400">
            {cov.codes_never_exercised.length} of {cov.codes_declared} declared codes are
            planted by no task and are disclosed as unvalidated.
          </p>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="card p-5">
          <h2 className="text-[15px] font-semibold">What each task&rsquo;s corpus asserts</h2>
          <ul className="mt-3 space-y-3">
            {Object.entries(data.fixtures_by_task).map(([task, names]) => (
              <li key={task}>
                <code className="font-mono text-[12px] text-verdict-minor">{task}</code>
                <span className="ml-2 text-[11px] text-ink-400">{names.length} fixtures</span>
                <div className="mt-1 flex flex-wrap gap-1">
                  {names.map((n) => (
                    <Pill key={n}>{n}</Pill>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-4">
          <div className="card p-5">
            <h2 className="text-[15px] font-semibold">Grader levers</h2>
            <p className="mt-1 text-[11px] text-ink-400">
              Asserted by <code className="font-mono">tests/test_mutations.py</code>; the
              inventory and the test set are compared by a drift-guard test.
            </p>
            <dl className="mt-3 space-y-2 text-[12px]">
              {Object.entries(data.grader_levers).map(([name, why]) => (
                <div key={name}>
                  <dt className="font-mono text-[11px] text-verdict-critical">{name}</dt>
                  <dd className="text-ink-300">{why}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="card p-5">
            <h2 className="text-[15px] font-semibold">Index levers — bugs a real transcript exposed</h2>
            <dl className="mt-3 space-y-2 text-[12px]">
              {Object.entries(data.index_levers).map(([name, why]) => (
                <div key={name}>
                  <dt className="font-mono text-[11px] text-verdict-critical">{name}</dt>
                  <dd className="text-ink-300">{why}</dd>
                </div>
              ))}
            </dl>
          </div>

          {cov.codes_never_exercised.length > 0 ? (
            <div className="card p-5">
              <h2 className="text-[15px] font-semibold text-verdict-critical">
                Declared but not planted by any task
              </h2>
              <ul className="mt-2 flex flex-wrap gap-1">
                {cov.codes_never_exercised.map((c) => (
                  <li key={c}>
                    <Pill tone="unresolved">{c}</Pill>
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-[11px] text-ink-400">
                Results on these codes should not be read as validation. The list is pinned by
                a test so it cannot grow silently.
              </p>
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}
