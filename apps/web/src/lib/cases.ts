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

export interface RepetitivoMatch {
  numero: number;
  descricao: string;
  situacao: string;
  tese: string | null;
  confidence: number;
  kind: "alta" | "media";
  justificativa: string | null;
}

export interface AnalysisTema {
  nome: string;
  blueprint_temas?: string[];
  /** @deprecated mantido para compatibilidade com dossiês antigos */
  blueprint_tema?: string | null;
  fundamentos_argumentativos: string[];
  permissivos_invocados: string[];
  obices_aplicaveis: string[];
  jurisprudencia_citada: string[];
  conclusao_sugerida: string;
  transcricao_rr_status?: "ok" | "ausente" | "parcial" | "nao_aplicavel";
  transcricao_rr_alerta?: string | null;
  repetitivos_matches?: RepetitivoMatch[];
}

export interface AnalysisRecurso {
  tipo: string;
  parte: string;
  temas: AnalysisTema[];
}

export interface AnalysisDossie {
  recursos: AnalysisRecurso[];
  observacoes?: string;
}

export type PartyRole = "reclamante" | "reclamada" | "ministerio_publico";

export interface Party {
  role: PartyRole;
  ordinal: number;
  name: string;
  aliases: string[];
}

export interface Case {
  id: string;
  numero_processo: string;
  titulo: string | null;
  status: CaseStatus;
  last_error: string | null;
  captured_at: string | null;
  analyzed_at: string | null;
  analysis_result: string | null;
  analysis_dossie: AnalysisDossie | null;
  parties: Party[] | null;
  minuta_md: string | null;
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
  parties?: Party[];
}): Promise<Case> {
  return apiJson<Case>("/cases", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function updateParties(id: string, parties: Party[]): Promise<Case> {
  return apiJson<Case>(`/cases/${id}/parties`, {
    method: "PUT",
    body: JSON.stringify({ parties }),
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

export async function generateMinutaDraft(id: string): Promise<{ text: string }> {
  return apiJson<{ text: string }>(`/cases/${id}/minuta-draft`, { method: "POST" });
}

export async function triggerDocx(id: string): Promise<void> {
  const res = await apiFetch(`/cases/${id}/docx`, { method: "POST" });
  if (!res.ok) throw new Error(`docx falhou: ${res.status}`);
}

// -------- Structured pieces (add peça flow) --------

export type PieceTipo =
  | "acordao_regional"
  | "acordao_embargos_declaracao"
  | "despacho_admissibilidade"
  | "recurso_revista"
  | "agravo_instrumento"
  | "agravo_interno";

export type PieceParte =
  | "reclamante"
  | "reclamada"
  | "reclamantes"
  | "reclamadas"
  | "ministerio_publico"
  | "outro";

export interface BlueprintRecurso {
  tipo: string;
  parte: string;
  temas: string[];
  conclusao: string;
}

export interface DespachoBlueprint {
  recursos: BlueprintRecurso[];
  note?: string;
}

export interface StructuredPiece {
  id: string;
  tipo: PieceTipo;
  parte: PieceParte | null;
  data: string | null;
  text: string;
  created_at: string;
  blueprint: DespachoBlueprint | null;
}

export async function listStructuredPieces(caseId: string): Promise<StructuredPiece[]> {
  return apiJson<StructuredPiece[]>(`/cases/${caseId}/structured-pieces`);
}

export async function addStructuredPiece(
  caseId: string,
  input: {
    tipo: PieceTipo;
    parte: PieceParte | null;
    data: string | null;
    text: string;
  },
): Promise<StructuredPiece> {
  return apiJson<StructuredPiece>(`/cases/${caseId}/structured-pieces`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function deleteStructuredPiece(
  caseId: string,
  pieceId: string,
): Promise<void> {
  const res = await apiFetch(
    `/cases/${caseId}/structured-pieces/${pieceId}`,
    { method: "DELETE" },
  );
  if (!res.ok) throw new Error(`delete falhou: ${res.status}`);
}

export interface AnonymizedPiecePreview {
  index: number;
  tipo: string;
  parte: string | null;
  data: string | null;
  original_chars: number;
  anonimizado_chars: number;
  anonimizado: string;
  substitutions: number;
  mapping_sample: Record<string, string>;
}

export interface AnonymizedPreview {
  case_id: string;
  parties: Party[];
  pieces: AnonymizedPiecePreview[];
  aggregate_mapping_size: number;
}

export async function fetchAnonymizedPreview(
  caseId: string,
): Promise<AnonymizedPreview> {
  return apiJson<AnonymizedPreview>(`/cases/${caseId}/anonymized-preview`);
}
