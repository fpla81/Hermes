import { notFound } from "next/navigation";

import { ApiError, apiFetch } from "@/lib/api";
import { getCase, listPrepared } from "@/lib/cases";

import {
  analyzeCaseAction,
  buildManifestAction,
  deletePreparedAction,
  triggerDocxAction,
  triggerPacketsAction,
  validateResourcesAction,
} from "../actions";
import { CasePolling } from "./polling";
import { MinutaForm, PiecesForm, PreparedUploadForm } from "./pipeline-forms";

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

async function fetchPrepared(caseId: string): Promise<string[] | null> {
  try {
    const { filenames } = await listPrepared(caseId);
    return filenames;
  } catch (e) {
    if (e instanceof ApiError && e.status === 503) return null; // storage não configurado
    return null;
  }
}

async function fetchMinuta(caseId: string): Promise<string> {
  try {
    const res = await apiFetch(`/cases/${caseId}`);
    if (!res.ok) return "";
    // a API não devolve minuta_md em CaseRead; pegamos o flag. Para edição
    // mostramos vazio (server-side não tem acesso ao conteúdo bruto).
    return "";
  } catch {
    return "";
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
  const prepared = await fetchPrepared(id);
  const minutaInitial = await fetchMinuta(id);

  return (
    <div className="space-y-8">
      {isInFlight && <CasePolling />}

      <header>
        <h1 className="font-mono text-xl">{c.numero_processo}</h1>
        {c.titulo && <p className="text-muted-foreground">{c.titulo}</p>}
      </header>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
        <dt className="text-muted-foreground">Status</dt>
        <dd>{STATUS_LABEL[c.status] ?? c.status}</dd>
        <dt className="text-muted-foreground">Capturado em</dt>
        <dd>{c.captured_at ? new Date(c.captured_at).toLocaleString("pt-BR") : "—"}</dd>
        <dt className="text-muted-foreground">Criado em</dt>
        <dd>{new Date(c.created_at).toLocaleString("pt-BR")}</dd>
      </dl>

      {c.last_error && (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm">
          <strong className="font-medium">Último erro:</strong> {c.last_error}
        </div>
      )}

      <section className="space-y-3 rounded-md border p-4">
        <h2 className="text-sm font-medium">1. Importar do Bem-te-vi</h2>
        <p className="text-xs text-muted-foreground">
          {c.captured_at
            ? `Importado em ${new Date(c.captured_at).toLocaleString("pt-BR")}. Para atualizar, abra a página "Peças" no Bem-te-vi e clique o bookmarklet "Enviar pro Hermes".`
            : "Abra a página \"Peças\" do processo no Bem-te-vi e clique o bookmarklet \"Enviar pro Hermes\" (configurado em /settings)."}
        </p>
        <div className="flex flex-wrap gap-2">
          {!isInFlight && (c.status === "captured" || c.status === "ready") && (
            <form action={analyzeCaseAction}>
              <input type="hidden" name="id" value={c.id} />
              <button
                type="submit"
                className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm font-medium hover:bg-accent"
              >
                {c.status === "ready" ? "Reanalisar" : "Analisar (anonimização + LLM)"}
              </button>
            </form>
          )}
          <a
            href="/settings"
            className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm font-medium hover:bg-accent"
          >
            Bookmarklet
          </a>
        </div>
      </section>

      <section className="space-y-3 rounded-md border p-4">
        <h2 className="text-sm font-medium">2. Pieces e manifest</h2>
        <p className="text-xs text-muted-foreground">
          Cole o JSON da tabela ``Peças`` (extraído automaticamente na captura
          ou montado à mão). Depois gere o manifest para o pipeline identificar
          o despacho-âncora.
        </p>
        <PiecesForm caseId={c.id} />
        <form action={buildManifestAction}>
          <input type="hidden" name="id" value={c.id} />
          <button
            type="submit"
            className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm font-medium hover:bg-accent"
          >
            {c.has_manifest ? "Regerar manifest" : "Gerar manifest"}
          </button>
          {c.has_manifest && (
            <span className="ml-2 text-xs text-emerald-600">manifest pronto ✓</span>
          )}
        </form>
      </section>

      <section className="space-y-3 rounded-md border p-4">
        <h2 className="text-sm font-medium">3. Arquivos preparados (anonimizados)</h2>
        <p className="text-xs text-muted-foreground">
          Suba os arquivos das peças após anonimização externa (.txt, .md,
          .html, .pdf, .docx).
        </p>
        <PreparedUploadForm caseId={c.id} />
        {prepared === null ? (
          <p className="text-xs text-muted-foreground">
            Storage S3 não configurado — defina S3_BUCKET no .env.
          </p>
        ) : prepared.length === 0 ? (
          <p className="text-xs text-muted-foreground">Nenhum arquivo enviado.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {prepared.map((name) => (
              <li key={name} className="flex items-center justify-between gap-2 rounded border bg-muted/30 px-2 py-1">
                <span className="font-mono text-xs">{name}</span>
                <form action={deletePreparedAction}>
                  <input type="hidden" name="id" value={c.id} />
                  <input type="hidden" name="filename" value={name} />
                  <button
                    type="submit"
                    className="text-xs text-destructive hover:underline"
                  >
                    remover
                  </button>
                </form>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-3 rounded-md border p-4">
        <h2 className="text-sm font-medium">4. Validação dos recursos</h2>
        <p className="text-xs text-muted-foreground">
          Confere que cada recurso recursal tem texto útil (mínimo 400 chars, 80
          palavras, sem páginas de SSO).
        </p>
        <form action={validateResourcesAction}>
          <input type="hidden" name="id" value={c.id} />
          <button
            type="submit"
            disabled={!c.has_manifest}
            className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm font-medium hover:bg-accent disabled:opacity-50"
          >
            Validar recursos
          </button>
        </form>
      </section>

      <section className="space-y-3 rounded-md border p-4">
        <h2 className="text-sm font-medium">5. Packets de análise</h2>
        <form action={triggerPacketsAction}>
          <input type="hidden" name="id" value={c.id} />
          <button
            type="submit"
            disabled={!c.has_manifest || c.status === "packaging"}
            className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm font-medium hover:bg-accent disabled:opacity-50"
          >
            {c.has_packets ? "Regerar packets" : "Empacotar"}
          </button>
          {c.has_packets && (
            <span className="ml-2 text-xs text-emerald-600">packets prontos ✓</span>
          )}
        </form>
      </section>

      <section className="space-y-3 rounded-md border p-4">
        <h2 className="text-sm font-medium">6. Minuta</h2>
        <p className="text-xs text-muted-foreground">
          Cole o markdown estruturado com marcadores ``[[CORPO]]``,
          ``[[TRANSCRICAO1]]``, etc.
        </p>
        <MinutaForm caseId={c.id} initial={minutaInitial} />
      </section>

      <section className="space-y-3 rounded-md border p-4">
        <h2 className="text-sm font-medium">7. DOCX final</h2>
        <div className="flex flex-wrap items-center gap-2">
          <form action={triggerDocxAction}>
            <input type="hidden" name="id" value={c.id} />
            <button
              type="submit"
              disabled={!c.has_minuta || c.status === "rendering"}
              className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {c.has_docx ? "Regerar DOCX" : "Gerar DOCX"}
            </button>
          </form>
          {c.has_docx && (
            <a
              href={`/cases/${c.id}/docx`}
              className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm font-medium hover:bg-accent"
            >
              Baixar minuta.docx
            </a>
          )}
        </div>
      </section>

      {c.analysis_result && (
        <section className="space-y-2 rounded-md border p-4">
          <h2 className="text-sm font-medium text-muted-foreground">
            Análise (LLM)
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
        <section className="space-y-2 rounded-md border p-4">
          <h2 className="text-sm font-medium text-muted-foreground">HTML capturado</h2>
          <iframe
            src={`/cases/${c.id}/raw`}
            className="h-[600px] w-full rounded-md border bg-background"
            sandbox="allow-scripts"
            title="HTML capturado"
          />
        </section>
      )}
    </div>
  );
}
