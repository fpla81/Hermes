import Link from "next/link";

import { ImportForm } from "./import-form";

export default function ImportPage() {
  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Importar do Bem-te-vi</h1>
        <p className="text-sm text-muted-foreground">
          Cole abaixo o conteúdo copiado pelo snippet de coleta (configurado em{" "}
          <Link href="/settings" className="underline">/settings</Link>).
        </p>
      </header>
      <ImportForm />
    </div>
  );
}
