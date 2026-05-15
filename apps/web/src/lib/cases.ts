import { apiFetch, apiJson } from "./api";

export type CaseStatus =
  | "draft"
  | "capturing"
  | "captured"
  | "preparing"
  | "analyzing"
  | "ready"
  | "packaging"
  | "rendering"
  | "done"
  | "error";

export interface Case {
  id: string;
  numero_processo: string;
  titulo: string | null;
  status: CaseStatus;
  last_error: string | null;
  captured_at: string | null;
  analyzed_at: string | null;
  analysis_result: string | null;
  has_manifest: boolean;
  has_packets: boolean;
  has_minuta: boolean;
  has_docx: boolean;
  created_at: string;
  updated_at: string;
}

export interface PieceIn {
  tipo?: string | null;
  data?: string | null;
  html_url?: string | null;
  bin_url?: string | null;
  id?: string | null;
  local_path?: string | null;
}

export interface PreparedListing {
  filenames: string[];
}

export async function listCases(): Promise<Case[]> {
  return apiJson<Case[]>("/cases");
}

export async function getCase(id: string): Promise<Case | null> {
  const res = await apiFetch(`/cases/${id}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`get falhou: ${res.status}`);
  return res.json() as Promise<Case>;
}

export async function getCaseHtml(id: string): Promise<Response> {
  return apiFetch(`/cases/${id}/html`);
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

export async function triggerAnalyze(id: string): Promise<void> {
  const res = await apiFetch(`/cases/${id}/analyze`, { method: "POST" });
  if (!res.ok) throw new Error(`analyze falhou: ${res.status}`);
}

export async function uploadPieces(id: string, pieces: PieceIn[]): Promise<Case> {
  return apiJson<Case>(`/cases/${id}/pieces`, {
    method: "POST",
    body: JSON.stringify({ pieces }),
  });
}

export async function buildManifest(id: string): Promise<Case> {
  return apiJson<Case>(`/cases/${id}/manifest`, { method: "POST" });
}

export async function listPrepared(id: string): Promise<PreparedListing> {
  return apiJson<PreparedListing>(`/cases/${id}/prepared`);
}

export async function uploadPrepared(id: string, file: File): Promise<PreparedListing> {
  const form = new FormData();
  form.append("file", file, file.name);
  const res = await apiFetch(`/cases/${id}/prepared`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`upload falhou: ${res.status}`);
  return res.json() as Promise<PreparedListing>;
}

export async function deletePrepared(id: string, filename: string): Promise<void> {
  const res = await apiFetch(
    `/cases/${id}/prepared/${encodeURIComponent(filename)}`,
    { method: "DELETE" },
  );
  if (!res.ok) throw new Error(`delete falhou: ${res.status}`);
}

export async function validateResources(id: string): Promise<Case> {
  return apiJson<Case>(`/cases/${id}/validate-resources`, { method: "POST" });
}

export async function triggerPackets(id: string): Promise<void> {
  const res = await apiFetch(`/cases/${id}/packets`, { method: "POST" });
  if (!res.ok) throw new Error(`packets falhou: ${res.status}`);
}

export async function uploadMinuta(id: string, text: string): Promise<Case> {
  return apiJson<Case>(`/cases/${id}/minuta`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export async function triggerDocx(id: string): Promise<void> {
  const res = await apiFetch(`/cases/${id}/docx`, { method: "POST" });
  if (!res.ok) throw new Error(`docx falhou: ${res.status}`);
}
