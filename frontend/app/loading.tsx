export default function Loading() {
  // Pages render server-side from the artifact API, so this is the honest shape of a slow
  // read: structure first, never a spinner over a blank panel.
  return (
    <div className="space-y-6" aria-busy="true" aria-live="polite">
      <div className="h-7 w-72 animate-pulse rounded bg-ink-800" />
      <div className="h-4 w-full max-w-2xl animate-pulse rounded bg-ink-850" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-[78px] animate-pulse rounded-md bg-ink-900" />
        ))}
      </div>
      <div className="h-[280px] animate-pulse rounded-md bg-ink-900" />
    </div>
  );
}
