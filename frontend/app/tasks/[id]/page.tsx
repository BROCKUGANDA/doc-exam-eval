import Link from "next/link";
import { api, fmt, type Documents, type Results, type TaskDetail } from "@/lib/api";
import { Pill, ScoreBar } from "@/components/ui";

export const dynamic = "force-dynamic";

type Props = { params: Promise<{ id: string }> };

/**
 * One task, shown as the model sees it: the exact prompt text and the exact rendered
 * documents. Page and line anchors exist so a finding can be traced to the place it came
 * from, which is the whole point of the evidence dimension.
 */
export default async function TaskPage({ params }: Props) {
  const { id } = await params;
  const [detail, docs, results] = await Promise.all([
    api<TaskDetail>(`/api/v1/tasks/${id}`),
    api<Documents>(`/api/v1/tasks/${id}/documents`),
    api<Results>("/api/v1/results"),
  ]);

  const byModel = Object.entries(results.models)
    .map(([spec, m]) => ({ spec, task: m.per_task[id] }))
    .filter((row) => row.task);

  const pagesByDoc = docs.documents.map((doc) => {
    const pages = new Map<number, typeof doc.fields[string][]>();
    Object.values(doc.fields).forEach((f) => {
      const list = pages.get(f.page) ?? [];
      list.push(f);
      pages.set(f.page, list);
    });
    return { doc, pages };
  });

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="label">{id}</div>
          <h1 className="mt-1 text-[22px] font-semibold tracking-tight">{String(detail.meta.title ?? id)}</h1>
        </div>
        <div className="flex gap-2 text-[12px] text-ink-400">
          <Pill>{docs.documents.length} documents</Pill>
          <Pill>seed {docs.seed}</Pill>
          <Pill>rulebook v{String(detail.meta.rulebook ?? "")}</Pill>
        </div>
      </header>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <section className="space-y-4">
          <h2 className="text-[15px] font-semibold">Documents presented</h2>
          {pagesByDoc.map(({ doc, pages }) => (
            <article key={doc.doc_id} id={`doc-${doc.doc_id}`} className="card scroll-mt-20 p-4">
              <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b pb-2 rule">
                <code className="font-mono text-[13px] text-verdict-minor">{doc.doc_id}</code>
                <span className="text-[13px]">{doc.title}</span>
                <span className="ml-auto text-[11px] text-ink-400">
                  {doc.doc_type} · {doc.page_count} page{doc.page_count > 1 ? "s" : ""} · issued by{" "}
                  {doc.issuer}
                </span>
              </header>

              {[...pages.entries()]
                .sort((a, b) => a[0] - b[0])
                .map(([pageNo, fields]) => (
                  <div key={pageNo} className="mt-3">
                    <div className="label">page {pageNo}</div>
                    <div className="doc-body mt-1">
                      {fields
                        .slice()
                        .sort((a, b) => a.line - b.line)
                        .map((f) => (
                          <div
                            key={f.name}
                            id={`doc-${doc.doc_id}-p${pageNo}-${f.line}`}
                            className={`scroll-mt-24 rounded-sm px-1 ${f.unreadable ? "bg-verdict-unresolved/10" : ""}`}
                          >
                            <span className="mr-2 select-none text-[10px] text-ink-600">
                              {String(f.line).padStart(2, "0")}
                            </span>
                            <span className="text-ink-300">{f.label}:</span>{" "}
                            {f.unreadable ? (
                              <Pill tone="unresolved">{f.raw}</Pill>
                            ) : (
                              <span>{f.raw}</span>
                            )}
                          </div>
                        ))}
                    </div>
                  </div>
                ))}
            </article>
          ))}

          <details className="card p-4">
            <summary className="cursor-pointer text-[13px] text-ink-300">
              Show the exact prompt sent to every model
            </summary>
            <pre className="doc-body mt-3 max-h-[520px] overflow-auto whitespace-pre-wrap text-[11.5px]">
              {detail.instruction}
            </pre>
          </details>
        </section>

        <aside className="space-y-4">
          <h2 className="text-[15px] font-semibold">Results for this task</h2>
          {byModel.length === 0 ? (
            <p className="card p-4 text-[13px] text-ink-400">
              No scored trials yet. Run <code className="font-mono">run_eval.py --live</code>.
            </p>
          ) : (
            byModel.map(({ spec, task }) => (
              <div key={spec} className="card p-4">
                <code className="block truncate font-mono text-[12px] text-ink-100">{spec}</code>
                <div className="num mt-1 text-[22px]">{fmt(task!.mean_total, 2)}</div>
                <div className="mt-1 flex flex-wrap gap-1 text-[11px]">
                  <Pill tone={task!.pass_hat_k ? "compliant" : "error"}>
                    pass^k {task!.pass_hat_k ? "yes" : "no"}
                  </Pill>
                  <Pill tone={task!.pass_at_k ? "compliant" : "critical"}>
                    pass@k {task!.pass_at_k ? "yes" : "no"}
                  </Pill>
                  <Pill>{task!.trials} trials</Pill>
                  <Pill>spread ±{fmt(task!.spread, 1)}</Pill>
                </div>
                {task!.caps_observed.length > 0 ? (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {task!.caps_observed.map((c) => (
                      <Pill key={c} tone="critical">
                        {c}
                      </Pill>
                    ))}
                  </div>
                ) : null}
                <div className="mt-3 space-y-2">
                  {Object.entries(task!.dimension_means).map(([name, points]) => (
                    <ScoreBar
                      key={name}
                      name={name}
                      points={points}
                      weight={
                        ({ recall: 25, precision: 20, rule_mapping: 15, evidence: 15, severity: 10, uncertainty: 10, format: 5 } as Record<string, number>)[
                          name
                        ] ?? 10
                      }
                    />
                  ))}
                </div>
                <Link
                  href={`/transcript?model=${encodeURIComponent(spec)}&task=${id}&trial=1`}
                  className="link mt-3 inline-block text-[12px]"
                >
                  Read the transcript →
                </Link>
              </div>
            ))
          )}
        </aside>
      </div>
    </div>
  );
}
