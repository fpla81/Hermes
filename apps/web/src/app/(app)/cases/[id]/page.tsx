import { notFound } from "next/navigation";

import { getCase } from "@/lib/cases";

import { analyzeCaseAction, captureCaseAction } from "../actions";
import { CasePolling } from "./polling";

interface Params {
  id: string;
}

const STATUS_LABEL: Record<string, string> = {
  draft: "Rascunho",
  capturing: "Capturando",
  captured: "Capturado",
  analyzing: "Analisando",
  ready: "Pronto",
  error: "Erro",
};

export default async function CaseDetailPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { id } = await params;
  const c = await getCase(id);
  if (!c) notFound();

  const isInFlight = c.status === "capturing" || c.status === "analyzing";

  return (
    <div className="space-y-6">
      {isInFlight && <CasePolling />}

      <div>
        <h1 className="font-mono text-xl">{c.numero_processo}</h1>
        {c.titulo && <p className="text-muted-foreground">{c.titulo}</p>}
      </div>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
        <dt className="text-muted-foreground">Status</dt>
        <dd>{STATUS_LABEL[c.status] ?? c.status}</dd>
        <dt className="text-muted-foreground">Capturado em</dt>
        <dd>
          {c.captured_at
            ? new Date(c.captured_at).toLocaleString("pt-BR")
            : "—"}
        </dd>
        <dt className="text-muted-foreground">Criado em</dt>
        <dd>{new Date(c.created_at).toLocaleString("pt-BR")}</dd>
      </dl>

      {c.last_error && (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm">
          <strong className="font-medium">Último erro:</strong> {c.last_error}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {!isInFlight && (
          <form action={captureCaseAction}>
            <input type="hidden" name="id" value={c.id} />
            <button
              type="submit"
              className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              {c.status === "captured" || c.status === "ready"
                ? "Recapturar"
                : "Capturar"}
            </button>
          </form>
        )}
        {!isInFlight && (c.status === "captured" || c.status === "ready") && (
          <form action={analyzeCaseAction}>
            <input type="hidden" name="id" value={c.id} />
            <button
              type="submit"
              className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm font-medium hover:bg-accent"
            >
              {c.status === "ready" ? "Reanalisar" : "Analisar"}
            </button>
          </form>
        )}
      </div>

      {c.analysis_result && (
        <section className="space-y-2">
          <h2 className="text-sm font-medium text-muted-foreground">
            Análise
            {c.analyzed_at && (
              <span className="ml-2 font-normal">
                ({new Date(c.analyzed_at).toLocaleString("pt-BR")})
              </span>
            )}
          </h2>
          <pre className="whitespace-pre-wrap rounded-md border bg-muted/30 p-4 text-sm">
            {c.analysis_result}
          </pre>
        </section>
      )}

      {c.captured_at && (
        <section className="space-y-2">
          <h2 className="text-sm font-medium text-muted-foreground">
            HTML capturado
          </h2>
          <iframe
            src={`/cases/${c.id}/raw`}
            className="h-[600px] w-full rounded-md border bg-background"
            sandbox=""
            title="HTML capturado"
          />
        </section>
      )}
    </div>
  );
}
