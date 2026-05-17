"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError } from "@/lib/api";
import {
  addStructuredPiece,
  buildManifest,
  createCase,
  deleteCase,
  deletePrepared,
  deleteStructuredPiece,
  generateMinutaDraft,
  triggerAnalyze,
  triggerCapture,
  triggerDocx,
  triggerPackets,
  updateParties,
  uploadMinuta,
  uploadPieces,
  uploadPrepared,
  validateResources,
} from "@/lib/cases";
import type { Party, PieceIn, PieceParte, PieceTipo } from "@/lib/cases";

export type CreateCaseState = {
  error?: string;
};

/** Extrai o número CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO) de uma string que pode
 *  vir com prefixo de tipo de recurso (ex.: "Ag-AIRR - 0012007-...").
 *  Se não encontrar, devolve o valor original trimmed. */
function extractNumeroCnj(raw: string): string {
  const m = raw.match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/);
  return (m ? m[0] : raw).trim();
}

export async function createCaseAction(
  _prev: CreateCaseState,
  formData: FormData,
): Promise<CreateCaseState> {
  const rawNumero = String(formData.get("numero_processo") ?? "").trim();
  const numero = extractNumeroCnj(rawNumero);
  const partiesRaw = String(formData.get("parties_json") ?? "").trim();
  let parties: Party[] = [];
  if (partiesRaw) {
    try {
      const parsed = JSON.parse(partiesRaw);
      if (Array.isArray(parsed)) parties = parsed as Party[];
    } catch {
      return { error: "Lista de partes inválida (JSON malformado)." };
    }
  }
  if (!numero) return { error: "Informe o número do processo." };
  try {
    await createCase({ numero_processo: numero, titulo: null, parties });
  } catch (e) {
    if (e instanceof ApiError && e.status === 422) {
      return { error: "Dados inválidos. Confira o número e as partes." };
    }
    return { error: e instanceof Error ? e.message : "Erro desconhecido." };
  }
  revalidatePath("/cases");
  redirect("/cases");
}

export type UpdatePartiesState = { error?: string; ok?: boolean };

export async function updatePartiesAction(
  _prev: UpdatePartiesState,
  formData: FormData,
): Promise<UpdatePartiesState> {
  const id = String(formData.get("id") ?? "");
  const partiesRaw = String(formData.get("parties_json") ?? "").trim();
  if (!id) return { error: "id ausente" };
  let parties: Party[] = [];
  if (partiesRaw) {
    try {
      const parsed = JSON.parse(partiesRaw);
      if (Array.isArray(parsed)) parties = parsed as Party[];
    } catch {
      return { error: "Lista de partes inválida (JSON malformado)." };
    }
  }
  try {
    await updateParties(id, parties);
  } catch (e) {
    return { error: e instanceof Error ? e.message : "erro" };
  }
  revalidatePath(`/cases/${id}`);
  return { ok: true };
}

export async function deleteCaseAction(formData: FormData): Promise<void> {
  const id = String(formData.get("id") ?? "");
  if (!id) return;
  await deleteCase(id);
  revalidatePath("/cases");
}

export async function captureCaseAction(formData: FormData): Promise<void> {
  const id = String(formData.get("id") ?? "");
  if (!id) return;
  await triggerCapture(id);
  revalidatePath("/cases");
  revalidatePath(`/cases/${id}`);
}

export type AnalyzeState = { error?: string };

export async function analyzeCaseAction(
  _prev: AnalyzeState,
  formData: FormData,
): Promise<AnalyzeState> {
  const id = String(formData.get("id") ?? "");
  if (!id) return { error: "id ausente" };
  try {
    await triggerAnalyze(id);
  } catch (e) {
    return { error: e instanceof Error ? e.message : "erro" };
  }
  revalidatePath("/cases");
  revalidatePath(`/cases/${id}`);
  return {};
}

// -------- Fase B / C --------

export type UploadPiecesState = { error?: string; ok?: boolean };

export async function uploadPiecesAction(
  _prev: UploadPiecesState,
  formData: FormData,
): Promise<UploadPiecesState> {
  const id = String(formData.get("id") ?? "");
  const json = String(formData.get("pieces_json") ?? "").trim();
  if (!id) return { error: "id ausente" };
  if (!json) return { error: "cole o pieces.json antes de enviar" };
  let parsed: unknown;
  try {
    parsed = JSON.parse(json);
  } catch (e) {
    return { error: `JSON inválido: ${e instanceof Error ? e.message : "erro"}` };
  }
  const pieces = Array.isArray(parsed) ? parsed : (parsed as { pieces?: PieceIn[] })?.pieces;
  if (!Array.isArray(pieces)) {
    return { error: "esperado array de peças ou objeto { pieces: [...] }" };
  }
  try {
    await uploadPieces(id, pieces as PieceIn[]);
  } catch (e) {
    return { error: e instanceof Error ? e.message : "erro" };
  }
  revalidatePath(`/cases/${id}`);
  return { ok: true };
}

export async function buildManifestAction(formData: FormData): Promise<void> {
  const id = String(formData.get("id") ?? "");
  if (!id) return;
  await buildManifest(id);
  revalidatePath(`/cases/${id}`);
}

export type UploadPreparedState = { error?: string; ok?: boolean };

export async function uploadPreparedAction(
  _prev: UploadPreparedState,
  formData: FormData,
): Promise<UploadPreparedState> {
  const id = String(formData.get("id") ?? "");
  const file = formData.get("file");
  if (!id) return { error: "id ausente" };
  if (!(file instanceof File) || file.size === 0) {
    return { error: "selecione um arquivo" };
  }
  try {
    await uploadPrepared(id, file);
  } catch (e) {
    return { error: e instanceof Error ? e.message : "erro" };
  }
  revalidatePath(`/cases/${id}`);
  return { ok: true };
}

export async function deletePreparedAction(formData: FormData): Promise<void> {
  const id = String(formData.get("id") ?? "");
  const filename = String(formData.get("filename") ?? "");
  if (!id || !filename) return;
  await deletePrepared(id, filename);
  revalidatePath(`/cases/${id}`);
}

export async function validateResourcesAction(formData: FormData): Promise<void> {
  const id = String(formData.get("id") ?? "");
  if (!id) return;
  await validateResources(id);
  revalidatePath(`/cases/${id}`);
}

export async function triggerPacketsAction(formData: FormData): Promise<void> {
  const id = String(formData.get("id") ?? "");
  if (!id) return;
  await triggerPackets(id);
  revalidatePath(`/cases/${id}`);
}

export type UploadMinutaState = { error?: string; ok?: boolean };

export async function uploadMinutaAction(
  _prev: UploadMinutaState,
  formData: FormData,
): Promise<UploadMinutaState> {
  const id = String(formData.get("id") ?? "");
  const text = String(formData.get("text") ?? "");
  if (!id) return { error: "id ausente" };
  if (!text.trim()) return { error: "minuta vazia" };
  try {
    await uploadMinuta(id, text);
  } catch (e) {
    return { error: e instanceof Error ? e.message : "erro" };
  }
  revalidatePath(`/cases/${id}`);
  return { ok: true };
}

export async function triggerDocxAction(formData: FormData): Promise<void> {
  const id = String(formData.get("id") ?? "");
  if (!id) return;
  await triggerDocx(id);
  revalidatePath(`/cases/${id}`);
}

export type MinutaDraftState = { error?: string; text?: string };

export async function generateMinutaDraftAction(
  _prev: MinutaDraftState,
  formData: FormData,
): Promise<MinutaDraftState> {
  const id = String(formData.get("id") ?? "");
  if (!id) return { error: "id ausente" };
  try {
    const { text } = await generateMinutaDraft(id);
    return { text };
  } catch (e) {
    if (e instanceof ApiError && e.status === 412) {
      return { error: "Adicione peças antes de gerar minuta." };
    }
    return { error: e instanceof Error ? e.message : "erro" };
  }
}

export type SaveMinutaState = { error?: string; ok?: boolean };

export async function saveMinutaAction(
  _prev: SaveMinutaState,
  formData: FormData,
): Promise<SaveMinutaState> {
  const id = String(formData.get("id") ?? "");
  const text = String(formData.get("text") ?? "");
  if (!id) return { error: "id ausente" };
  if (!text.trim()) return { error: "minuta vazia" };
  try {
    await uploadMinuta(id, text);
  } catch (e) {
    return { error: e instanceof Error ? e.message : "erro" };
  }
  revalidatePath(`/cases/${id}`);
  return { ok: true };
}

export type AddPieceState = { error?: string; ok?: boolean };

export async function addPieceAction(
  _prev: AddPieceState,
  formData: FormData,
): Promise<AddPieceState> {
  const caseId = String(formData.get("case_id") ?? "");
  const tipo = String(formData.get("tipo") ?? "") as PieceTipo;
  const parteRaw = String(formData.get("parte") ?? "");
  const data = String(formData.get("data") ?? "").trim() || null;
  const text = String(formData.get("text") ?? "");
  if (!caseId) return { error: "case_id ausente" };
  if (!tipo) return { error: "selecione um tipo" };
  if (!text.trim()) return { error: "cole o texto da peça" };
  const TIPOS_SEM_PARTE = new Set([
    "acordao_regional",
    "acordao_embargos_declaracao",
    "despacho_admissibilidade",
  ]);
  if (!TIPOS_SEM_PARTE.has(tipo) && !parteRaw) {
    return { error: "selecione a parte recorrente" };
  }
  const parte = (parteRaw ? (parteRaw as PieceParte) : null);
  try {
    await addStructuredPiece(caseId, { tipo, parte, data, text });
  } catch (e) {
    return { error: e instanceof Error ? e.message : "erro" };
  }
  revalidatePath(`/cases/${caseId}`);
  return { ok: true };
}

export async function deletePieceAction(formData: FormData): Promise<void> {
  const caseId = String(formData.get("case_id") ?? "");
  const pieceId = String(formData.get("piece_id") ?? "");
  if (!caseId || !pieceId) return;
  await deleteStructuredPiece(caseId, pieceId);
  revalidatePath(`/cases/${caseId}`);
}

export interface LearnState {
  ok?: boolean;
  learned?: number;
  error?: string;
}

export async function learnFundamentosAction(
  _prev: LearnState,
  formData: FormData,
): Promise<LearnState> {
  const caseId = String(formData.get("case_id") ?? "");
  if (!caseId) return { error: "case_id ausente" };
  const { learnFundamentos } = await import("@/lib/fundamentos");
  try {
    const res = await learnFundamentos(caseId);
    return { ok: true, learned: res.learned };
  } catch (e) {
    return { error: e instanceof Error ? e.message : "erro" };
  }
}

export interface ExtractState {
  ok?: boolean;
  fundamentos?: import("@/lib/fundamentos-types").FundamentoExtractedItem[];
  error?: string;
}

export async function extractFundamentosAction(
  caseId: string,
): Promise<ExtractState> {
  if (!caseId) return { error: "case_id ausente" };
  const { extractFundamentos } = await import("@/lib/fundamentos");
  try {
    const res = await extractFundamentos(caseId);
    return { ok: true, fundamentos: res.fundamentos };
  } catch (e) {
    return { error: e instanceof Error ? e.message : "erro" };
  }
}

export interface BulkSaveState {
  ok?: boolean;
  saved?: number;
  error?: string;
}

export async function saveFundamentosAction(
  items: import("@/lib/fundamentos-types").FundamentoExtractedItem[],
): Promise<BulkSaveState> {
  if (!items.length) return { ok: true, saved: 0 };
  const { bulkSaveFundamentos } = await import("@/lib/fundamentos");
  try {
    const saved = await bulkSaveFundamentos(items);
    return { ok: true, saved: saved.length };
  } catch (e) {
    return { error: e instanceof Error ? e.message : "erro" };
  }
}
