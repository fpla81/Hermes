import { BookmarkletPanel } from "./bookmarklet";

export default function SettingsPage() {
  const webBaseUrl = process.env.NEXTAUTH_URL ?? "http://localhost:3100";
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
      <BookmarkletPanel webBaseUrl={webBaseUrl} />
    </div>
  );
}
