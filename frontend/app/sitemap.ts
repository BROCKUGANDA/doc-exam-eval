import { MetadataRoute } from "next";
import { siteOrigin } from "@/lib/site";

const base = siteOrigin();

// Per-route crawl hints: the homepage changes most often; task/result pages
// only change when artifacts are regenerated, so weekly is honest.
type Hint = { changeFrequency: "always" | "hourly" | "daily" | "weekly" | "monthly" | "yearly" | "never"; priority: number };
const routeHints: Record<string, Hint> = {
  "": { changeFrequency: "daily", priority: 1 },
  "/tasks": { changeFrequency: "weekly", priority: 0.9 },
  "/results": { changeFrequency: "weekly", priority: 0.9 },
  "/rulebook": { changeFrequency: "monthly", priority: 0.8 },
  "/integrity": { changeFrequency: "monthly", priority: 0.8 },
  "/transcript": { changeFrequency: "monthly", priority: 0.7 },
  "/design-system": { changeFrequency: "monthly", priority: 0.5 },
};

// Individual task pages: these IDs are fixed by the benchmark (DOC-001 … DOC-008)
// and change only when artifacts are regenerated, so weekly is honest.
const TASK_IDS = ["DOC-001", "DOC-002", "DOC-003", "DOC-004", "DOC-005", "DOC-006", "DOC-007", "DOC-008"];

export default function sitemap(): MetadataRoute.Sitemap {
  const staticRoutes = Object.keys(routeHints).map((route) => {
    const hint = routeHints[route];
    return {
      url: `${base}${route}`,
      lastModified: new Date(),
      changeFrequency: hint.changeFrequency,
      priority: hint.priority,
    };
  });
  const taskRoutes = TASK_IDS.map((id) => ({
    url: `${base}/tasks/${id}`,
    lastModified: new Date(),
    changeFrequency: "weekly" as const,
    priority: 0.85,
  }));
  return [...staticRoutes, ...taskRoutes];
}
