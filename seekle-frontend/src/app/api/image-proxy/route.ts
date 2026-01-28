// seekle-frontend/src/app/api/image-proxy/route.ts
import { NextResponse } from "next/server";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const src = searchParams.get("src");

  if (!src) {
    return NextResponse.json({ detail: "src is required" }, { status: 400 });
  }

  let url: URL;
  try {
    url = new URL(src);
  } catch {
    return NextResponse.json({ detail: "Invalid src URL" }, { status: 400 });
  }

  // Guardrail: only allow http(s)
  if (url.protocol !== "https:" && url.protocol !== "http:") {
    return NextResponse.json({ detail: "Invalid protocol" }, { status: 400 });
  }

  try {
    const r = await fetch(url.toString(), {
      // Some CDNs behave better with a UA
      headers: { "User-Agent": "seekle-image-proxy" },
      cache: "no-store",
    });

    if (!r.ok) {
      return NextResponse.json(
        { detail: `Upstream failed: ${r.status}` },
        { status: 502 }
      );
    }

    const contentType = r.headers.get("content-type") || "image/jpeg";
    const buf = await r.arrayBuffer();

    return new NextResponse(buf, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=86400",
      },
    });
  } catch (e: any) {
    return NextResponse.json(
      { detail: e?.message || "proxy failed" },
      { status: 502 }
    );
  }
}
