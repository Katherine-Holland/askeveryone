// src/app/api/diagnostics/config/route.ts
import { NextResponse } from "next/server";

function resolveBackendUrl() {
  const raw =
    (process.env.NODE_ENV !== "production" ? process.env.BACKEND_URL_DEV : undefined) ||
    process.env.BACKEND_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    "https://askeveryone.onrender.com";

  return raw;
}

export async function GET() {
  const resolved = resolveBackendUrl();

  return NextResponse.json({
    NODE_ENV: process.env.NODE_ENV ?? null,

    // raw envs
    BACKEND_URL_DEV: process.env.BACKEND_URL_DEV ?? null,
    BACKEND_URL: process.env.BACKEND_URL ?? null,
    NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL ?? null,

    // what the server route will actually use
    resolved_backend_url: resolved,
  });
}
