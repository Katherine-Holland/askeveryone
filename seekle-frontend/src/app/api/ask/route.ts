import { NextResponse } from "next/server";

export async function POST(req: Request) {
  try {
    const backend =
      process.env.BACKEND_URL ||
      process.env.NEXT_PUBLIC_BACKEND_URL ||
      "https://askeveryone.onrender.com";

    const body = await req.json();

    const r = await fetch(`${backend}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      // Don’t cache responses
      cache: "no-store",
    });

    const contentType = r.headers.get("content-type") || "";

    // Pass through status + body as-is (including 402/401/429)
    if (contentType.includes("application/json")) {
      const data = await r.json();
      return NextResponse.json(data, { status: r.status });
    } else {
      const text = await r.text();
      return new NextResponse(text, { status: r.status });
    }
  } catch (e: any) {
    return NextResponse.json(
      { detail: `API proxy error: ${e?.message || "unknown"}` },
      { status: 500 }
    );
  }
}
