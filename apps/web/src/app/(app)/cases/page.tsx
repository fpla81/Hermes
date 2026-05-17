import Link from "next/link";
import type { Route } from "next";
import { FileText, Plus, Trash2, Download } from "lucide-react";

import { CaseStatusBadge } from "@/components/case-status-badge";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { listCases } from "@/lib/cases";

import { captureCaseAction, deleteCaseAction } from "./actions";
import { CasesAutoRefresh } from "./refresh";

export default async function CasesPage() {
  const cases = await listCases();
  const inFlight = cases.some(
    (c) => c.status === "capturing" || c.status === "analyzing",
  );

  return (
    <div className="space-y-8">
      {inFlight && <CasesAutoRefresh />}

      <PageHeader
        eyebrow="Sala de trabalho"
        title="Casos"
        description="Cada caso reúne o despacho, as peças e o dossiê temático necessário para produzir a minuta final."
        actions={
          <Button asChild>
            <Link href="/cases/new">
              <Plus className="h-4 w-4" />
              Novo caso
            </Link>
          </Button>
        }
      />

      {cases.length === 0 ? (
        <Card className="bg-editorial border-dashed">
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <div className="grid h-12 w-12 place-items-center rounded-full bg-primary/10 text-primary">
              <FileText className="h-5 w-5" />
            </div>
            <div className="space-y-1">
              <h3 className="font-serif text-lg font-semibold">
                Nenhum caso ainda
              </h3>
              <p className="max-w-sm text-sm text-muted-foreground">
                Crie o primeiro caso para começar a montar o dossiê e gerar
                minutas.
              </p>
            </div>
            <Button asChild>
              <Link href="/cases/new">
                <Plus className="h-4 w-4" />
                Criar primeiro caso
              </Link>
            </Button>
          </div>
        </Card>
      ) : (
        <ul className="grid grid-cols-1 gap-3 lg:grid-cols-2">
          {cases.map((c) => (
            <li key={c.id}>
              <Card className="group relative overflow-hidden transition-shadow hover:shadow-md">
                <Link
                  href={`/cases/${c.id}` as Route}
                  className="block p-5 pb-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1 space-y-2">
                      <p className="font-mono text-xs text-muted-foreground">
                        {c.numero_processo}
                      </p>
                      <h3 className="line-clamp-2 font-serif text-lg font-semibold leading-snug text-foreground transition-colors group-hover:text-primary">
                        {c.titulo || "Sem título"}
                      </h3>
                    </div>
                    <CaseStatusBadge status={c.status} />
                  </div>
                </Link>
                <div className="flex items-center justify-between border-t bg-card/40 px-5 py-2.5 text-xs text-muted-foreground">
                  <span>
                    Criado em{" "}
                    {new Date(c.created_at).toLocaleDateString("pt-BR", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })}
                  </span>
                  <div className="flex items-center gap-1">
                    {c.status !== "capturing" && c.status !== "analyzing" && (
                      <form action={captureCaseAction}>
                        <input type="hidden" name="id" value={c.id} />
                        <Button
                          type="submit"
                          variant="ghost"
                          size="sm"
                          className="h-7 px-2 text-xs"
                        >
                          <Download className="h-3 w-3" /> Capturar
                        </Button>
                      </form>
                    )}
                    <form action={deleteCaseAction}>
                      <input type="hidden" name="id" value={c.id} />
                      <Button
                        type="submit"
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-xs hover:text-destructive"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </form>
                  </div>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
