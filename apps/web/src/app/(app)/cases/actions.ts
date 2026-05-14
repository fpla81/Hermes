"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError } from "@/lib/api";
import { createCase, deleteCase, triggerCapture } from "@/lib/cases";

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
}
