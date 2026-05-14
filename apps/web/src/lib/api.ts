import { auth } from "./auth";

const API_URL = process.env.HERMES_API_URL ?? "http://localhost:8000";
const SECRET = process.env.HERMES_INTERNAL_SECRET;

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  if (!SECRET) {
    throw new Error("HERMES_INTERNAL_SECRET não configurado");
  }
  const session = await auth();
  console.log("[apiFetch] session:", JSON.stringify(session));
  const userKey = session?.user?.id ?? session?.user?.email;
  if (!userKey) {
    throw new ApiError(401, "Sessão ausente");
  }
  const headers = new Headers(init.headers);
  headers.set("X-Hermes-Secret", SECRET);
  headers.set("X-Hermes-User-Id", userKey);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });
  return res;
}

export async function apiJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await apiFetch(path, init);
  if (!res.ok) {
    throw new ApiError(res.status, await res.text());
  }
  return res.json() as Promise<T>;
}
