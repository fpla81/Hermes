import { notFound } from "next/navigation";

import { getCase, listStructuredPieces } from "@/lib/cases";
import type { DespachoBlueprint, StructuredPiece } from "@/lib/cases";

import { AnalyzeButton } from "./analyze-button";
import { DossiePanel } from "./dossie-panel";
import { MinutaPanel } from "./minuta-panel";
import { PiecesPanel } from "./pieces-panel";
import { CasePolling } from "./polling";

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

      <header>
        <h1 className="font-mono text-xl">{c.numero_processo}</h1>
        {c.titulo && <p className="text-muted-foreground">{c.titulo}</p>}
      </header>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
        <dt className="text-muted-foreground">Status</dt>
        <dd>{STATUS_LABEL[c.status] ?? c.status}</dd>
        <dt className="text-muted-foreground">Peças adicionadas</dt>
        <dd>{pieces.length}</dd>
        <dt className="text-muted-foreground">Criado em</dt>
        <dd>{new Date(c.created_at).toLocaleString("pt-BR")}</dd>
      </dl>

      {c.last_error && (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm">
          <strong className="font-medium">Último erro:</strong> {c.last_error}
        </div>
      )}

      <PiecesPanel caseId={id} pieces={pieces} blueprint={blueprint} />

      {pieces.length > 0 && (
        <section className="space-y-3 rounded-md border p-4">
          <header className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-medium">Análise jurídica</h2>
              <p className="text-xs text-muted-foreground">
                Anonimiza as peças e gera um dossiê temático com fundamentos,
                permissivos e óbices por recurso.
              </p>
            </div>
            <AnalyzeButton
              caseId={c.id}
              alreadyAnalyzed={Boolean(c.analyzed_at) || c.status === "ready"}
              inFlight={c.status === "analyzing"}
              lastError={c.last_error}
            />
          </header>
          {c.status === "analyzing" && (
            <p className="animate-pulse text-sm text-amber-600">
              Examinando o processo… (pode levar alguns minutos)
            </p>
          )}
          {c.analyzed_at && (
            <p className="text-xs text-muted-foreground">
              Última análise: {new Date(c.analyzed_at).toLocaleString("pt-BR")}
            </p>
          )}
          {c.analysis_dossie ? (
            <DossiePanel dossie={c.analysis_dossie} />
          ) : c.analysis_result ? (
            <pre className="whitespace-pre-wrap rounded-md border bg-muted/30 p-3 text-sm">
              {c.analysis_result}
            </pre>
          ) : (
            <p className="text-sm text-muted-foreground">
              Ainda sem análise — clique em &quot;Analisar&quot;.
            </p>
          )}
        </section>
      )}

      {pieces.length > 0 && (
        <MinutaPanel
          caseId={id}
          initial={c.minuta_md ?? ""}
          hasMinuta={c.has_minuta}
          hasDocx={c.has_docx}
        />
      )}
    </div>
  );
}
