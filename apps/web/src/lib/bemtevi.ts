import { apiJson } from "./api";

export interface LoginStartResult {
  session_id: string;
  login_url: string;
  profile_dir: string;
  reused: boolean;
}

export interface LoginSession {
  session_id: string;
  started_at: string;
  profile_dir: string;
}

export async function startBemTeViLogin(): Promise<LoginStartResult> {
  return apiJson<LoginStartResult>("/bemtevi/login/start", { method: "POST" });
}

export async function completeBemTeViLogin(sessionId: string): Promise<void> {
  await apiJson<unknown>("/bemtevi/login/complete", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function cancelBemTeViLogin(sessionId: string): Promise<void> {
  await apiJson<unknown>("/bemtevi/login/cancel", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId }),
  });
}

export async function listBemTeViSessions(): Promise<{ sessions: LoginSession[] }> {
  return apiJson<{ sessions: LoginSession[] }>("/bemtevi/login/status");
}
