import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://seekle.io";

  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [
          "/api/",
          "/dashboard/",
          "/account/",
          "/settings/",
          "/admin/",
          "/_next/",
        ],
      },
    ],
    sitemap: `${baseUrl}/sitemap.xml`,
  };
}
