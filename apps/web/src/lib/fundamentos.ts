import { apiFetch, apiJson } from "./api";

export interface Fundamento {
  id: string;
  tema: string;
  titulo: string;
  corpo_md: string;
  tags: string[] | null;
  resumo: string | null;
  source_case_id: string | null;
  usage_count: number;
  created_at: string;
}

export interface LearnResult {
  learned: number;
  fundamentos: Array<{
    id: string;
    tema: string;
    titulo: string;
    resumo: string | null;
  }>;
}

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

export async function learnFundamentos(caseId: string): Promise<LearnResult> {
  return apiJson<LearnResult>(`/cases/${caseId}/learn-fundamentos`, {
    method: "POST",
  });
}
