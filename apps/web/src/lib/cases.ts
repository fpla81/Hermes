import { apiFetch, apiJson } from "./api";

export type CaseStatus =
  | "draft"
  | "capturing"
  | "captured"
  | "analyzing"
  | "ready"
  | "error";

export interface Case {
  id: string;
  numero_processo: string;
  titulo: string | null;
  status: CaseStatus;
  last_error: string | null;
  captured_at: string | null;
  created_at: string;
  updated_at: string;
}

export async function listCases(): Promise<Case[]> {
  return apiJson<Case[]>("/cases");
}

export async function createCase(input: {
  numero_processo: string;
  titulo?: string | null;
}): Promise<Case> {
  return apiJson<Case>("/cases", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function deleteCase(id: string): Promise<void> {
  const res = await apiFetch(`/cases/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`delete falhou: ${res.status}`);
}

export async function triggerCapture(id: string): Promise<void> {
  const res = await apiFetch(`/cases/${id}/capture`, { method: "POST" });
  if (!res.ok) throw new Error(`capture falhou: ${res.status}`);
}
