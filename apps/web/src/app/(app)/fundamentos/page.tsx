import { PageHeader } from "@/components/layout/page-header";
import { auth } from "@/lib/auth";
import { listFundamentos } from "@/lib/fundamentos";
import { isManager } from "@/lib/roles";

import { FundamentosBrowser } from "./browser";

interface SearchParams {
  q?: string;
  tema?: string;
}

export default async function FundamentosPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const session = await auth();
  const items = await listFundamentos({ q: sp.q, tema: sp.tema });
  const canEdit = isManager(session?.user?.role);

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Base do gabinete"
        title="Fundamentos"
        description="Fundamentações jurídicas aprendidas a partir das minutas finais. Reaproveitadas automaticamente como modelo na geração de novas minutas."
      />

      <FundamentosBrowser
        initialQuery={sp.q ?? ""}
        initialTema={sp.tema ?? ""}
        items={items}
        canEdit={canEdit}
      />
    </div>
  );
}
