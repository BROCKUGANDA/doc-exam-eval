import Link from "next/link";

const links = [
  { href: "/", label: "Command centre" },
  { href: "/tasks", label: "Tasks" },
  { href: "/results", label: "Results" },
  { href: "/rulebook", label: "Rulebook" },
  { href: "/transcript", label: "Transcripts" },
  { href: "/integrity", label: "Grader integrity" },
];

export function Nav() {
  return (
    <header className="sticky top-0 z-30 border-b bg-ink-950/95 backdrop-blur rule">
      <div className="mx-auto flex max-w-console items-center gap-8 px-6 py-3">
        <Link href="/" className="focus-ring flex items-baseline gap-2 rounded">
          <span className="font-mono text-[13px] font-semibold tracking-[0.22em] text-ink-100">
            DOC·EXAM
          </span>
          <span className="hidden text-[11px] text-ink-400 sm:inline">
            documentary credit examination benchmark
          </span>
        </Link>
        <nav aria-label="Primary" className="flex flex-wrap gap-x-5 gap-y-1 text-[13px]">
          {links.map((l) => (
            <Link key={l.href} href={l.href} className="focus-ring rounded text-ink-300 hover:text-ink-100">
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
