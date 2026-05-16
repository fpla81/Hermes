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
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Fundamentos</h1>
        <p className="text-sm text-muted-foreground">
          Fundamentações jurídicas aprendidas a partir das minutas finais.
          Reusadas automaticamente como modelo na geração de novas minutas.
        </p>
      </header>

      <FundamentosBrowser
        initialQuery={sp.q ?? ""}
        initialTema={sp.tema ?? ""}
        items={items}
        canEdit={canEdit}
      />
    </div>
  );
}
