import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    BACKEND_URL: process.env.BACKEND_URL ?? null,
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL ?? null,
    resolved_backend_url:
      process.env.BACKEND_URL ||
      process.env.NEXT_PUBLIC_BACKEND_URL ||
      "https://askeveryone.onrender.com",
  });
}
