import Link from "next/link";

const links = [
  { href: "/", label: "Overview" },
  { href: "/tasks", label: "Tasks" },
  { href: "/results", label: "Results" },
  { href: "/rulebook", label: "Rulebook" },
  { href: "/transcript", label: "Transcripts" },
  { href: "/integrity", label: "Integrity" },
];

export function Nav() {
  return (
    <header className="sticky top-0 z-30 border-b border-ink-700 bg-ink-950/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-console flex-col gap-3 px-5 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <Link href="/" className="focus-ring flex w-fit items-center gap-3 rounded">
          <span className="flex h-8 w-8 items-center justify-center rounded border border-verdict-minor/50 bg-verdict-minor/10 font-mono text-xs font-bold text-verdict-minor">D·E</span>
          <span>
            <span className="block font-mono text-[13px] font-semibold tracking-[0.2em] text-ink-100">DOC-EXAM</span>
            <span className="block text-[10px] tracking-wide text-ink-500">EVIDENCE-FIRST AI EVALUATION</span>
          </span>
        </Link>
        <nav aria-label="Primary" className="-mx-1 flex gap-1 overflow-x-auto pb-1 text-[12px] sm:mx-0 sm:flex-wrap sm:overflow-visible sm:pb-0">
          {links.map((l) => (
            <Link key={l.href} href={l.href} className="focus-ring shrink-0 rounded px-3 py-2 text-ink-300 transition hover:bg-ink-800 hover:text-white">
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
