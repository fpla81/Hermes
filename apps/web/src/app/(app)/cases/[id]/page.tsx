import Link from "next/link";
import { notFound } from "next/navigation";
import { AlertCircle, ChevronLeft } from "lucide-react";

import { CaseStatusBadge } from "@/components/case-status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { auth } from "@/lib/auth";
import { getCase, listStructuredPieces } from "@/lib/cases";
import type { DespachoBlueprint, StructuredPiece } from "@/lib/cases";
import { isManager } from "@/lib/roles";

import { CasePolling } from "./polling";
import { CaseWizard } from "./wizard";

interface Params {
  id: string;
}

const IN_FLIGHT_STATES = new Set([
  "capturing",
  "analyzing",
  "packaging",
  "rendering",
]);

async function fetchPieces(caseId: string): Promise<StructuredPiece[]> {
  try {
    return await listStructuredPieces(caseId);
  } catch {
    return [];
  }
}

export default async function CaseDetailPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { id } = await params;
  const c = await getCase(id);
  if (!c) notFound();

  const isInFlight = IN_FLIGHT_STATES.has(c.status);
  const pieces = await fetchPieces(id);
  const despacho = pieces.find((p) => p.tipo === "despacho_admissibilidade");
  const blueprint: DespachoBlueprint | null = despacho?.blueprint ?? null;
  const session = await auth();
  const canLearn = isManager(session?.user?.role);

  return (
    <div className="space-y-8">
      {isInFlight && <CasePolling />}

      <div className="space-y-4">
        <Button
          asChild
          variant="ghost"
          size="sm"
          className="-ml-3 text-muted-foreground"
        >
          <Link href="/cases">
            <ChevronLeft className="h-4 w-4" />
            Voltar para Casos
          </Link>
        </Button>
        <header className="flex flex-wrap items-start justify-between gap-4 border-b pb-6">
          <div className="space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/80">
              Processo
            </p>
            <h1 className="font-mono text-3xl font-semibold tracking-tight">
              {c.numero_processo}
            </h1>
            <p className="text-xs text-muted-foreground">
              Criado em{" "}
              {new Date(c.created_at).toLocaleDateString("pt-BR", {
                day: "2-digit",
                month: "long",
                year: "numeric",
              })}
            </p>
          </div>
          <CaseStatusBadge status={c.status} />
        </header>
      </div>

      {c.last_error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Erro na última operação</AlertTitle>
          <AlertDescription>{c.last_error}</AlertDescription>
        </Alert>
      )}

      <CaseWizard
        caseId={id}
        caseData={c}
        pieces={pieces}
        blueprint={blueprint}
        canLearn={canLearn}
      />
    </div>
  );
}
