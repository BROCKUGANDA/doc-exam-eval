import Link from "next/link";
import { api, type TaskSummary } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Tasks() {
  const tasks = await api<TaskSummary[]>("/api/v1/tasks");

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-[22px] font-semibold tracking-tight">Tasks</h1>
        <p className="mt-2 max-w-3xl text-[13px] leading-relaxed text-ink-300">
          Each task is a complete presentation: the credit, any amendments, the documents the
          beneficiary lodged, and the business calendar that applies. The prompt is the whole
          rulebook plus the rendered documents, so nothing a model is graded on was left
          unstated. Reference answers are computed from those documents by the rule engine and
          are not served to the browser.
        </p>
      </header>

      <div className="card divide-y overflow-hidden">
        <table className="w-full text-[13px]">
          <caption className="sr-only">Task index</caption>
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-[0.12em] text-ink-400">
              <th className="px-4 py-2 font-normal">Task</th>
              <th className="px-4 py-2 font-normal">Findings</th>
              <th className="px-4 py-2 font-normal">Unestablishable</th>
              <th className="px-4 py-2 font-normal">Prompt tokens</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.case_id} className="border-t rule hover:bg-ink-850">
                <td className="px-4 py-3">
                  <Link href={`/tasks/${t.case_id}`} className="focus-ring rounded font-mono text-verdict-minor underline underline-offset-4">
                    {t.case_id}
                  </Link>
                  <div className="mt-0.5 text-[12px] text-ink-300">{t.title}</div>
                </td>
                <td className="num px-4 py-3">{t.expected_findings}</td>
                <td className="num px-4 py-3">{t.expected_unresolved}</td>
                <td className="num px-4 py-3 text-ink-400">~{t.prompt_tokens_estimate?.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
