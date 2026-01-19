import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://seekle.io";
  const now = new Date();

  const routes = [
    "",
    "/about",
    "/contact",
    "/terms",
    "/privacy",
    "/ai-policy",
    "/.well-known/ai.json"
  ];

  return routes.map((path) => ({
    url: `${baseUrl}${path}`,
    lastModified: now,
    changeFrequency: "weekly",
    priority: path === "" ? 1 : 0.6,
  }));
}

