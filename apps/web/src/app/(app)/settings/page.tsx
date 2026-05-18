import { PageHeader } from "@/components/layout/page-header";

import { BookmarkletPanel } from "./bookmarklet";

export default function SettingsPage() {
  const webBaseUrl = process.env.NEXTAUTH_URL ?? "http://localhost:3100";
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Conta"
        title="Ajustes"
        description="Configurações pessoais e ferramentas auxiliares."
      />
      <BookmarkletPanel webBaseUrl={webBaseUrl} />
    </div>
  );
}
