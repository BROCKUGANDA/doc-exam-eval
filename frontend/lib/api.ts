const API = process.env.DOCX_BACKEND_URL ?? "http://127.0.0.1:8010";

/**
 * Server-side artifact reads. Every page is rendered from the API that reads the CLI's own
 * files, so the dashboard cannot show a number the harness did not produce. If the API is
 * down the page throws rather than painting zeros — a blank screen is honest, a fabricated
 * score is not.
 */
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, { cache: "no-store", ...init });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`${path} -> HTTP ${res.status} ${detail.slice(0, 200)}`);
  }
  return (await res.json()) as T;
}

/**
 * Fetch that treats a 404 as an absent artifact rather than a crash. A trial that has not
 * run yet, or a task with no results, is a real state this console has to display; letting
 * it throw blanked the whole page instead of saying "not recorded yet".
 */
export async function apiOptional<T>(path: string): Promise<T | null> {
  try {
    return await api<T>(path);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    if (/HTTP 404/.test(message)) return null;
    throw err;
  }
}

export type TaskSummary = {
  case_id: string;
  title: string;
  expected_findings: number;
  expected_unresolved: number;
  prompt_tokens_estimate: number;
};

export type Dimension = { name: string; weight: number; ratio: number; points: number; detail: string };

export type Scorecard = {
  case_id: string;
  total: number;
  passed: boolean;
  threshold: number;
  caps: string[];
  dimensions: Dimension[];
  matched_findings: string[];
  missed_findings: string[];
  fabricated_findings: { code: string; field?: string; why: string }[];
  safety_metrics: Record<string, unknown>;
};

export type Trial = {
  panel_id: string;
  case_id: string;
  model_id: string;
  provider: string;
  trial: number;
  status: string;
  started_at: string;
  finished_at: string;
  prompt_sha256: string;
  prompt_tokens_estimated: number;
  prompt_tokens_reported: number | null;
  completion_tokens_reported: number | null;
  latency_s: number | null;
  settings: Record<string, unknown>;
  normalization: string[];
  error: string;
  scorecard?: Scorecard | null;
  raw_output?: string;
  normalized_output?: string;
};

export type ModelResult = {
  trials_recorded: number;
  trials_scored: number;
  status_counts: Record<string, number>;
  tasks_covered: number;
  overall_mean_total: number | null;
  tasks_passed_at_k: number;
  tasks_passed_hat_k: number;
  critical_false_clearances: number;
  fabricated_on_clean: number;
  mean_prompt_tokens: number | null;
  mean_latency_s: number | null;
  per_task: Record<
    string,
    {
      trials: number;
      mean_total: number | null;
      spread: number;
      pass_at_k: boolean;
      pass_hat_k: boolean;
      pass_rate: number | null;
      dimension_means: Record<string, number>;
      caps_observed: string[];
    }
  >;
};

export type Results = {
  panel: Record<string, unknown>;
  totals: Record<string, number>;
  models: Record<string, ModelResult>;
  warnings: string[];
};

export type Rule = {
  id: string;
  title: string;
  kind: string;
  severity: string;
  codes: string[];
  applies_to: { docs: string[]; fields: string[] };
  statement: string;
};

export type Rulebook = {
  version: string;
  fingerprint: string;
  markdown: string;
  rules: Rule[];
  codes: string[];
  code_to_rules: Record<string, string[]>;
};

export type DocField = {
  name: string;
  label: string;
  raw: string;
  synonyms: string[];
  unreadable: boolean;
  page: number;
  line: number;
};

export type DocRecord = {
  doc_id: string;
  doc_type: string;
  title: string;
  issuer: string;
  page_count: number;
  fields: Record<string, DocField>;
};

export type Documents = {
  case_id: string;
  seed: number;
  documents: DocRecord[];
  governing_terms: Record<string, unknown>;
};

export type TaskDetail = {
  meta: Record<string, unknown>;
  instruction: string;
  grader_config: Record<string, unknown>;
};

export type Coverage = {
  tasks: number;
  total_ground_truth_findings: number;
  clean_tasks: number;
  rules_declared: number;
  producer_rules: number;
  rules_exercised: number;
  rules_never_exercised: string[];
  codes_declared: number;
  codes_never_exercised: string[];
};

export type ProbeRow = {
  candidate: string;
  status: string;
  http?: number | null;
  detail?: string;
  latency_s?: number;
  prompt_tokens?: number;
  completion_tokens?: number;
  text?: string;
};

export const specId = (provider: string, modelId: string) => `${provider}:${modelId}`;

export function severityTone(severity: string): string {
  switch (severity) {
    case "critical":
      return "text-verdict-critical";
    case "minor":
      return "text-verdict-minor";
    case "none":
      return "text-ink-400";
    default:
      return "text-verdict-unresolved";
  }
}

export function fmt(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toFixed(digits);
}
