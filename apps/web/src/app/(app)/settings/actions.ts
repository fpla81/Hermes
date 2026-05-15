"use server";

import { revalidatePath } from "next/cache";

import { ApiError } from "@/lib/api";
import {
  cancelBemTeViLogin,
  completeBemTeViLogin,
  startBemTeViLogin,
  type LoginStartResult,
} from "@/lib/bemtevi";

export type StartLoginState = {
  error?: string;
  session?: LoginStartResult;
};

export async function startLoginAction(
  _prev: StartLoginState,
): Promise<StartLoginState> {
  try {
    const session = await startBemTeViLogin();
    revalidatePath("/settings");
    return { session };
  } catch (e) {
    if (e instanceof ApiError && e.status === 503) {
      return {
        error:
          "O serviço Playwright não tem display disponível — rode-o no seu Mac (não em Docker headless) e tente de novo.",
      };
    }
    return { error: e instanceof Error ? e.message : "erro" };
  }
}

export type CompleteLoginState = { error?: string; ok?: boolean };

export async function completeLoginAction(
  _prev: CompleteLoginState,
  formData: FormData,
): Promise<CompleteLoginState> {
  const sid = String(formData.get("session_id") ?? "");
  if (!sid) return { error: "session_id ausente" };
  try {
    await completeBemTeViLogin(sid);
  } catch (e) {
    return { error: e instanceof Error ? e.message : "erro" };
  }
  revalidatePath("/settings");
  return { ok: true };
}

export async function cancelLoginAction(formData: FormData): Promise<void> {
  const sid = String(formData.get("session_id") ?? "");
  if (!sid) return;
  try {
    await cancelBemTeViLogin(sid);
  } catch {
    // tolera erro — sessão pode já ter sumido
  }
  revalidatePath("/settings");
}
