import { NextResponse } from "next/server";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const q = searchParams.get("q") || "";

  // Phase 1 stub: return 200 so the browser doesn't error.
  return NextResponse.json(
    {
      ok: true,
      message: "BETA.",
      query: q,
      results: [], // frontend will fall back to MOCK_RESULTS
    },
    { status: 200 }
  );
}
