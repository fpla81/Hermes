"use server";

import { apiJson } from "@/lib/api";

interface PreviewResult {
  anonymized: string;
  mapping: Record<string, string>;
  substitutions: number;
}

export type AnonymizerState = {
  error?: string;
  result?: PreviewResult;
};

export async function anonymizeAction(
  _prev: AnonymizerState,
  formData: FormData,
): Promise<AnonymizerState> {
  const text = String(formData.get("text") ?? "");
  if (!text.trim()) return { error: "cole um texto pra anonimizar" };
  try {
    const result = await apiJson<PreviewResult>("/debug/anonymize", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    return { result };
  } catch (e) {
    return { error: e instanceof Error ? e.message : "erro" };
  }
}
