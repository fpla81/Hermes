import { notFound } from "next/navigation";

import { getCase, listStructuredPieces } from "@/lib/cases";
import type { DespachoBlueprint, StructuredPiece } from "@/lib/cases";

import { CasePolling } from "./polling";
import { CaseWizard } from "./wizard";

interface Params {
  id: string;
}

const STATUS_LABEL: Record<string, string> = {
  draft: "Rascunho",
  capturing: "Capturando",
  captured: "Capturado",
  preparing: "Preparando",
  analyzing: "Analisando",
  ready: "Pronto",
  packaging: "Empacotando",
  rendering: "Renderizando",
  done: "Concluído",
  error: "Erro",
};

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

  return (
    <div className="space-y-6">
      {isInFlight && <CasePolling />}

      <header className="space-y-1">
        <h1 className="font-mono text-xl">{c.numero_processo}</h1>
        {c.titulo && <p className="text-muted-foreground">{c.titulo}</p>}
        <p className="text-xs text-muted-foreground">
          Status: <span className="font-medium">{STATUS_LABEL[c.status] ?? c.status}</span>
          {" · "}
          Criado em {new Date(c.created_at).toLocaleString("pt-BR")}
        </p>
      </header>

      {c.last_error && (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm">
          <strong className="font-medium">Último erro:</strong> {c.last_error}
        </div>
      )}

      <CaseWizard
        caseId={id}
        caseData={c}
        pieces={pieces}
        blueprint={blueprint}
      />
    </div>
  );
}
