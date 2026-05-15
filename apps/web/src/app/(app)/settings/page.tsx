import { getMyIngestToken } from "@/lib/ingest";

import { BookmarkletPanel } from "./bookmarklet";

async function fetchToken(): Promise<string | null> {
  try {
    const { token } = await getMyIngestToken();
    return token;
  } catch {
    return null;
  }
}

export default async function SettingsPage() {
  const token = await fetchToken();
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const webBaseUrl = process.env.NEXTAUTH_URL ?? "http://localhost:3100";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
      {token ? (
        <BookmarkletPanel
          token={token}
          apiBaseUrl={apiBaseUrl}
          webBaseUrl={webBaseUrl}
        />
      ) : (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm">
          Não consegui gerar o token de ingestão. Confira{" "}
          <code>HERMES_INTERNAL_SECRET</code> no servidor.
        </div>
      )}
    </div>
  );
}
