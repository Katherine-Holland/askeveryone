import { NextResponse } from "next/server";

const BACKEND_URL =
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "https://askeveryone.onrender.com";

export async function GET(req: Request) {
  // forward headers so backend can show what it sees
  const headers: Record<string, string> = {};
  const pass = ["x-forwarded-for", "x-real-ip", "cf-connecting-ip", "true-client-ip", "user-agent"];

  for (const h of pass) {
    const v = req.headers.get(h);
    if (v) headers[h] = v;
  }

  const upstream = await fetch(`${BACKEND_URL}/diagnostics/ip`, {
    method: "GET",
    headers,
    cache: "no-store",
  });

  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
  });
}
