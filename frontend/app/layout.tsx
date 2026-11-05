import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/Nav";
import { siteOrigin, siteUrl, SITE_NAME, DEFAULT_IMAGE, DEFAULT_IMAGE_WIDTH, DEFAULT_IMAGE_HEIGHT } from "@/lib/site";

export const metadata: Metadata = {
  metadataBase: new URL(siteOrigin()),
  title: {
    template: "%s | DOC-EXAM",
    default: "DOC-EXAM — documentary credit examination benchmark",
  },
  description:
    "An AI evaluation benchmark for documentary credit (letter of credit) examination. Tests whether frontier AI models can examine a letter-of-credit presentation, detect every material discrepancy, cite the document that proves each finding, apply the governing rule, and refuse to decide what the evidence does not establish.",
  keywords: [
    "documentary credit",
    "letter of credit",
    "trade finance",
    "AI evaluation",
    "benchmark",
    "frontier models",
    "document examination",
    "compliance",
    "AEO",
    "GEO",
  ],
  authors: [{ name: "micro1 Eval Hackathon 2026" }],
  creator: "DOC-EXAM",
  publisher: "micro1",
  robots: "index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1",
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "/",
    siteName: SITE_NAME,
    title: "DOC-EXAM — documentary credit examination benchmark",
    description:
      "Measuring whether frontier AI models can examine a letter of credit, detect discrepancies, cite evidence, apply the rule, and know when not to decide.",
    images: [
      {
        url: siteUrl(DEFAULT_IMAGE),
        width: DEFAULT_IMAGE_WIDTH,
        height: DEFAULT_IMAGE_HEIGHT,
        alt: "DOC-EXAM command centre",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    site: "@micro1",
    creator: "@micro1",
    title: "DOC-EXAM — documentary credit examination benchmark",
    description:
      "An AI evaluation benchmark for documentary credit examination.",
    images: [siteUrl(DEFAULT_IMAGE)],
  },
  alternates: {
    canonical: siteUrl("/"),
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" dir="ltr">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png" />
        <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
        <link rel="icon" type="image/svg+xml" href="/og-image.svg" />
        <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
        <link rel="apple-touch-icon" sizes="192x192" href="/android-chrome-192x192.png" />
        <link rel="apple-touch-icon" sizes="512x512" href="/android-chrome-512x512.png" />
        <link rel="alternate" type="application/llms+txt" href="/llms.txt" />
        <link rel="alternate" type="application/llms+txt" href="/llms-full.txt" />
        <link rel="sitemap" type="application/xml" href="/sitemap.xml" />
      </head>
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
