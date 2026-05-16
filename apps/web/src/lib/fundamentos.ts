import "server-only";

import { apiFetch, apiJson } from "./api";
import type {
  Fundamento,
  FundamentoUpdate,
  LearnResult,
} from "./fundamentos-types";

export type { Fundamento, FundamentoUpdate, LearnResult } from "./fundamentos-types";

export async function listFundamentos(opts?: {
  q?: string;
  tema?: string;
}): Promise<Fundamento[]> {
  const params = new URLSearchParams();
  if (opts?.q) params.set("q", opts.q);
  if (opts?.tema) params.set("tema", opts.tema);
  const qs = params.toString();
  return apiJson<Fundamento[]>(`/fundamentos${qs ? `?${qs}` : ""}`);
}

export async function deleteFundamento(id: string): Promise<void> {
  const res = await apiFetch(`/fundamentos/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`delete falhou: ${res.status}`);
}

export async function updateFundamento(
  id: string,
  patch: FundamentoUpdate,
): Promise<Fundamento> {
  return apiJson<Fundamento>(`/fundamentos/${id}`, {
    method: "PUT",
    body: JSON.stringify(patch),
  });
}

export async function learnFundamentos(caseId: string): Promise<LearnResult> {
  return apiJson<LearnResult>(`/cases/${caseId}/learn-fundamentos`, {
    method: "POST",
  });
}
