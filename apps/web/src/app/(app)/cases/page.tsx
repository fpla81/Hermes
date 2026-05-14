import Link from "next/link";

import { listCases } from "@/lib/cases";
import { deleteCaseAction } from "./actions";

export default async function CasesPage() {
  const cases = await listCases();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Casos</h1>
        <Link
          href="/cases/new"
          className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Novo caso
        </Link>
      </div>

      {cases.length === 0 ? (
        <p className="text-muted-foreground">
          Nenhum caso ainda. Crie o primeiro para começar.
        </p>
      ) : (
        <div className="rounded-md border">
          <table className="w-full text-sm">
            <thead className="border-b bg-muted/40 text-left text-muted-foreground">
              <tr>
                <th className="px-4 py-2 font-medium">Processo</th>
                <th className="px-4 py-2 font-medium">Título</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Criado em</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.id} className="border-b last:border-b-0">
                  <td className="px-4 py-2 font-mono text-xs">
                    {c.numero_processo}
                  </td>
                  <td className="px-4 py-2">{c.titulo ?? "—"}</td>
                  <td className="px-4 py-2">{c.status}</td>
                  <td className="px-4 py-2">
                    {new Date(c.created_at).toLocaleString("pt-BR")}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <form action={deleteCaseAction}>
                      <input type="hidden" name="id" value={c.id} />
                      <button
                        type="submit"
                        className="text-xs text-muted-foreground hover:text-destructive"
                      >
                        Excluir
                      </button>
                    </form>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
