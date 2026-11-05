"use client";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  /**
   * The dashboard reads the same files the CLI writes, so a failure here means the artifacts
   * or the API are missing. Showing zeros would be a fabrication, which is the one thing this
   * project is not allowed to do.
   */
  return (
    <div className="mx-auto max-w-2xl py-16">
      <h1 className="text-[20px] font-semibold text-verdict-error">Could not read benchmark artifacts</h1>
      <p className="mt-3 text-[13px] leading-relaxed text-ink-300">
        This page refuses to render placeholder numbers. Either the API is not running or the
        artifacts have not been generated yet.
      </p>
      <pre className="doc-body mt-4 overflow-auto rounded border p-3 text-[11.5px] rule">
        {error.message}
      </pre>
      <div className="mt-5 space-y-2 text-[12px] text-ink-400">
        <p>
          Generate the artifacts: <code className="font-mono text-verdict-minor">python run_eval.py --offline</code>
        </p>
        <p>
          Start the API: <code className="font-mono text-verdict-minor">uvicorn backend.app.main:app --port 8010</code>
        </p>
      </div>
      <button
        onClick={reset}
        className="focus-ring mt-6 rounded border border-ink-700 px-4 py-2 text-[13px] hover:bg-ink-850"
      >
        Try again
      </button>
    </div>
  );
}
