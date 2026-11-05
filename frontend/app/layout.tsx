import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: "DOC-EXAM — documentary credit examination benchmark",
  description:
    "An evaluation of whether AI models can examine a letter-of-credit presentation: find discrepancies, cite evidence, apply the rule, and know when not to decide.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-ink-950 text-ink-100 antialiased">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus-ring focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-ink-800 focus:px-3 focus:py-2"
        >
          Skip to content
        </a>
        <Nav />
        <main id="main" className="mx-auto w-full max-w-console px-6 pb-24 pt-8">
          {children}
        </main>
        <footer className="mx-auto max-w-console border-t px-6 py-6 text-xs text-ink-400 rule">
          Every figure on this site is read from the same artifact files that{" "}
          <code className="font-mono">run_eval.py</code> writes. Nothing here is stored
          separately, so the dashboard cannot disagree with the benchmark.
        </footer>
      </body>
    </html>
  );
}
