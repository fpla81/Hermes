import { NextRequest } from "next/server";

import { apiFetch } from "@/lib/api";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const upstream = await apiFetch(`/cases/${id}/docx`);
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type":
        upstream.headers.get("content-type") ??
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "Content-Disposition":
        upstream.headers.get("content-disposition") ??
        `attachment; filename="minuta-${id}.docx"`,
      "Cache-Control": "no-store",
    },
  });
}
