"use server";

import { revalidatePath } from "next/cache";

import { deleteFundamento, updateFundamento } from "@/lib/fundamentos";

export interface UpdateState {
  ok?: boolean;
  error?: string;
}

export async function updateFundamentoAction(
  _prev: UpdateState,
  form: FormData,
): Promise<UpdateState> {
  const id = String(form.get("id") ?? "");
  if (!id) return { error: "id ausente" };
  const tagsRaw = String(form.get("tags") ?? "");
  try {
    await updateFundamento(id, {
      tema: String(form.get("tema") ?? "").trim() || undefined,
      titulo: String(form.get("titulo") ?? "").trim() || undefined,
      resumo: String(form.get("resumo") ?? "").trim() || undefined,
      corpo_md: String(form.get("corpo_md") ?? ""),
      tags: tagsRaw
        ? tagsRaw.split(",").map((t) => t.trim()).filter(Boolean)
        : [],
    });
    revalidatePath("/fundamentos");
    return { ok: true };
  } catch (e) {
    return { error: e instanceof Error ? e.message : "erro" };
  }
}

export async function deleteFundamentoAction(
  _prev: UpdateState,
  form: FormData,
): Promise<UpdateState> {
  const id = String(form.get("id") ?? "");
  if (!id) return { error: "id ausente" };
  try {
    await deleteFundamento(id);
    revalidatePath("/fundamentos");
    return { ok: true };
  } catch (e) {
    return { error: e instanceof Error ? e.message : "erro" };
  }
}
