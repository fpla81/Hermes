import { listBemTeViSessions } from "@/lib/bemtevi";

import { BemTeViLoginPanel } from "./bemtevi-login";

async function getActiveSessionId(): Promise<string | null> {
  try {
    const { sessions } = await listBemTeViSessions();
    return sessions[0]?.session_id ?? null;
  } catch {
    return null;
  }
}

export default async function SettingsPage() {
  const activeSessionId = await getActiveSessionId();
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
      <BemTeViLoginPanel activeSessionId={activeSessionId} />
    </div>
  );
}
