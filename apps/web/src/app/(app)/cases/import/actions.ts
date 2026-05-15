"use server";

import { redirect } from "next/navigation";

import { apiJson, ApiError } from "@/lib/api";

interface IngestResult {
  case_id: string;
  pieces_found: number;
  created: boolean;
}

export type ImportState = {
  error?: string;
  result?: IngestResult;
};

export async function importHtmlAction(
  _prev: ImportState,
  formData: FormData,
): Promise<ImportState> {
  const raw = String(formData.get("payload") ?? "").trim();
  if (!raw) return { error: "Cole o conteúdo copiado do Bem-te-vi." };
  let parsed: { numero_processo?: string; html?: string; url?: string };
  try {
    parsed = JSON.parse(raw);
  } catch (e) {
    return { error: `JSON inválido: ${e instanceof Error ? e.message : "erro"}` };
  }
  if (!parsed.numero_processo || !parsed.html) {
    return { error: "JSON precisa conter numero_processo e html." };
  }
  let result: IngestResult;
  try {
    result = await apiJson<IngestResult>("/cases/ingest", {
      method: "POST",
      body: JSON.stringify(parsed),
    });
  } catch (e) {
    if (e instanceof ApiError) {
      return { error: `${e.status}: ${e.message}` };
    }
    return { error: e instanceof Error ? e.message : "erro" };
  }
  redirect(`/cases/${result.case_id}`);
}
