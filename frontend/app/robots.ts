import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/login", "/signup"],
        disallow: ["/candidate/", "/admin/", "/api/"],
      },
    ],
    sitemap: "https://vidyamarg-ai.vercel.app/sitemap.xml",
  };
}
