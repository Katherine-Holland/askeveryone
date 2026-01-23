import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q") ?? "";

  return NextResponse.json(
    {
      ok: false,
      message: "Shop search is not connected yet (Phase 1 stub).",
      query: q,
      results: [],
    },
    { status: 501 }
  );
}
