import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function fastApiBase(): string {
  const internal = process.env.FAST_API_INTERNAL_URL?.trim();
  if (internal) return internal.replace(/\/+$/, "");
  const configured = process.env.NEXT_PUBLIC_FAST_API?.trim();
  if (configured) return configured.replace(/\/+$/, "");
  return "http://127.0.0.1:8000";
}

export async function GET(request: NextRequest) {
  const cookie = request.headers.get("cookie") ?? "";
  try {
    const response = await fetch(
      `${fastApiBase()}/api/v1/ppt/scientific/capabilities`,
      {
        method: "GET",
        headers: cookie ? { cookie } : undefined,
        cache: "no-store",
      }
    );
    if (!response.ok) {
      return NextResponse.json(
        {
          available: false,
          source: "backend-unavailable",
          status: response.status,
        },
        { status: 503 }
      );
    }
    const capabilities = await response.json();
    return NextResponse.json({
      ...capabilities,
      available: true,
      source: "fastapi",
    });
  } catch (error) {
    return NextResponse.json(
      {
        available: false,
        source: "backend-unavailable",
        detail: error instanceof Error ? error.message : "unknown error",
      },
      { status: 503 }
    );
  }
}
