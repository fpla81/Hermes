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
  triggerAnalyze,
  triggerCapture,
  triggerDocx,
  triggerPackets,
  uploadMinuta,
  uploadPieces,
  uploadPrepared,
  validateResources,
} from "@/lib/cases";
import type { PieceIn, PieceParte, PieceTipo } from "@/lib/cases";

export type CreateCaseState = {
  error?: string;
};

export async function createCaseAction(
  _prev: CreateCaseState,
  formData: FormData,
): Promise<CreateCaseState> {
  const numero = String(formData.get("numero_processo") ?? "").trim();
  const titulo = String(formData.get("titulo") ?? "").trim() || null;
  if (!numero) return { error: "Informe o número do processo." };
  try {
    await createCase({ numero_processo: numero, titulo });
  } catch (e) {
    if (e instanceof ApiError && e.status === 422) {
      return { error: "Número de processo inválido. Use o formato CNJ." };
    }
    return { error: e instanceof Error ? e.message : "Erro desconhecido." };
  }
  revalidatePath("/cases");
  redirect("/cases");
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

export async function analyzeCaseAction(formData: FormData): Promise<void> {
  const id = String(formData.get("id") ?? "");
  if (!id) return;
  await triggerAnalyze(id);
  revalidatePath("/cases");
  revalidatePath(`/cases/${id}`);
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
  if (tipo !== "despacho_admissibilidade" && !parteRaw) {
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
