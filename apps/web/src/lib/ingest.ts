import { apiJson } from "./api";

export async function getMyIngestToken(): Promise<{ token: string }> {
  return apiJson<{ token: string }>("/me/ingest-token");
}
