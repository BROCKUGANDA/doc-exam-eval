/**
 * Site identity — single source of truth for SEO / AEO / GEO metadata.
 *
 * Set NEXT_PUBLIC_SITE_URL to your deployment origin (e.g.
 * https://doc-exam.example.com). It must not end with a slash. The placeholder
 * below is only for local development; the build fails loudly in CI if it is
 * still the placeholder and NEXT_PUBLIC_SITE_URL is unset.
 */
const DEFAULT_ORIGIN = "https://doc-exam.example.com";

export function siteOrigin(): string {
  const env = process.env.NEXT_PUBLIC_SITE_URL;
  if (env) {
    return env.replace(/\/$/, "");
  }
  return DEFAULT_ORIGIN;
}

export const SITE_NAME = "DOC-EXAM";
export const SITE_TAGLINE =
  "Measure what intelligence misses — documentary credit examination benchmark.";
export const TWITTER_HANDLE = "@micro1";
export const DEFAULT_IMAGE = "/og-image.png";
export const DEFAULT_IMAGE_WIDTH = 1200;
export const DEFAULT_IMAGE_HEIGHT = 630;

/** Absolute URL for a path, e.g. /tasks → https://doc-exam.example.com/tasks */
export function siteUrl(path: string): string {
  return `${siteOrigin()}${path}`;
}

/** Build per-page metadata: title, description, Open Graph, JSON-LD WebPage. */
export function pageMetadata({
  title,
  description,
  path,
  image,
}: {
  title: string;
  description: string;
  path: string;
  image?: string;
}) {
  const url = siteUrl(path);
  return {
    title: `${title} | DOC-EXAM`,
    description,
    alternates: { canonical: url },
    openGraph: {
      type: "website",
      locale: "en_US",
      url,
      siteName: SITE_NAME,
      title,
      description,
      images: image
        ? [{ url: siteUrl(image), width: DEFAULT_IMAGE_WIDTH, height: DEFAULT_IMAGE_HEIGHT, alt: title }]
        : [{ url: siteUrl(DEFAULT_IMAGE), width: DEFAULT_IMAGE_WIDTH, height: DEFAULT_IMAGE_HEIGHT, alt: title }],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: image ? [siteUrl(image)] : [siteUrl(DEFAULT_IMAGE)],
    },
  };
}

/** JSON-LD WebPage block as a JSON string for dangerouslySetInnerHTML. */
export function webpageJsonLd({ title, description, path }: { title: string; description: string; path: string }) {
  return JSON.stringify({
    "@context": "https://schema.org",
    "@type": "WebPage",
    "@id": siteUrl(path),
    "url": siteUrl(path),
    "name": title,
    "description": description,
    "inLanguage": "en-US",
    "isPartOf": {
      "@type": "WebSite",
      "@id": siteOrigin(),
      "name": SITE_NAME,
      "url": siteOrigin(),
    },
    "publisher": {
      "@type": "Organization",
      "name": "micro1 Eval Hackathon 2026",
      "url": siteOrigin(),
    },
  });
}
