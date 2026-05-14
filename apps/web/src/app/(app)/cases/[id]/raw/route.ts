import { NextRequest } from "next/server";

import { getCaseHtml } from "@/lib/cases";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const upstream = await getCaseHtml(id);
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type":
        upstream.headers.get("content-type") ?? "text/html; charset=utf-8",
      "Cache-Control": "no-store",
    },
  });
}
