import { NextResponse } from "next/server";

export async function GET(req: Request) {
  const h = new Headers(req.headers);

  return NextResponse.json({
    client_host: h.get("x-forwarded-for") ?? null,
    cf_connecting_ip: h.get("cf-connecting-ip") ?? null,
    true_client_ip: h.get("true-client-ip") ?? null,
    x_real_ip: h.get("x-real-ip") ?? null,
    x_forwarded_for: h.get("x-forwarded-for") ?? null,
    user_agent: h.get("user-agent") ?? null,
  });
}
