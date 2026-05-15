import { notFound } from "next/navigation";

import { getCase, listStructuredPieces } from "@/lib/cases";
import type { DespachoBlueprint, StructuredPiece } from "@/lib/cases";

import { analyzeCaseAction } from "../actions";
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
          <h2 className="text-sm font-medium">Análise (LLM)</h2>
          <p className="text-xs text-muted-foreground">
            Dispara anonimização + análise com Gemini sobre as peças adicionadas
            (esta integração ainda usa o pipeline antigo e deve ser refeita para
            ler structured_pieces).
          </p>
          <form action={analyzeCaseAction}>
            <input type="hidden" name="id" value={c.id} />
            <button
              type="submit"
              disabled={isInFlight}
              className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm font-medium hover:bg-accent disabled:opacity-50"
            >
              {c.status === "ready" ? "Reanalisar" : "Analisar"}
            </button>
          </form>
          {c.analysis_result && (
            <pre className="whitespace-pre-wrap rounded-md border bg-muted/30 p-3 text-sm">
              {c.analysis_result}
            </pre>
          )}
        </section>
      )}
    </div>
  );
}
