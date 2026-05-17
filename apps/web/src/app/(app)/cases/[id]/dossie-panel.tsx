import { AlertTriangle, CheckCircle2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalysisDossie } from "@/lib/cases";

const TIPO_LABEL: Record<string, string> = {
  recurso_revista: "Recurso de Revista",
  agravo_instrumento: "Agravo de Instrumento",
  agravo_interno: "Agravo Interno",
};

const PARTE_LABEL: Record<string, string> = {
  reclamante: "Reclamante",
  reclamada: "Reclamada",
  reclamantes: "Reclamantes",
  reclamadas: "Reclamadas",
  ministerio_publico: "Ministério Público",
};

function ListBlock({ label, items }: { label: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div className="space-y-1.5">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
      <ul className="ml-4 list-disc space-y-1 text-sm leading-relaxed">
        {items.map((it, i) => (
          <li key={i}>{it}</li>
        ))}
      </ul>
    </div>
  );
}

export function DossiePanel({ dossie }: { dossie: AnalysisDossie }) {
  if (!dossie.recursos?.length) {
    return (
      <p className="text-sm text-muted-foreground">
        {dossie.observacoes ?? "Dossiê ainda não disponível."}
      </p>
    );
  }
  const obs = dossie.observacoes ?? "";
  const hasAlignmentWarning = obs.startsWith("Alinhamento com o despacho");
  return (
    <div className="space-y-6">
      {hasAlignmentWarning && (
        <div className="rounded-lg border border-warning/30 bg-warning/10 p-4">
          <p className="text-sm font-semibold text-warning">
            Atenção ao alinhamento com o despacho
          </p>
          <p className="mt-1 whitespace-pre-wrap text-xs text-warning/90">
            {obs}
          </p>
        </div>
      )}
      {dossie.recursos.map((r, i) => (
        <Card key={i}>
          <CardHeader className="border-b">
            <CardTitle className="text-base">
              {TIPO_LABEL[r.tipo] ?? r.tipo}
              <span className="ml-2 font-sans text-sm font-normal text-muted-foreground">
                · {PARTE_LABEL[r.parte] ?? r.parte}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-6">
            {(r.temas || []).map((t, j) => {
              const refs =
                t.blueprint_temas ?? (t.blueprint_tema ? [t.blueprint_tema] : []);
              const status = t.transcricao_rr_status;
              const isRR = r.tipo === "recurso_revista";
              return (
                <section
                  key={j}
                  className="space-y-3 rounded-lg border bg-muted/20 p-4"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <h4 className="font-serif text-sm font-semibold uppercase tracking-wide">
                      {t.nome}
                    </h4>
                    {refs.length === 0 && (
                      <Badge variant="warning">fora do despacho</Badge>
                    )}
                    {refs.length > 1 && (
                      <Badge variant="secondary">
                        agrupa {refs.length} temas
                      </Badge>
                    )}
                    {isRR && status === "ok" && (
                      <Badge variant="success" className="gap-1">
                        <CheckCircle2 className="h-3 w-3" />
                        Transcrição OK
                      </Badge>
                    )}
                  </div>

                  {isRR &&
                    (status === "ausente" || status === "parcial") &&
                    t.transcricao_rr_alerta && (
                      <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-3">
                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                        <div className="space-y-1">
                          <p className="text-xs font-semibold text-destructive">
                            Risco de admissibilidade — art. 896, § 1º-A, I, CLT
                          </p>
                          <p className="text-xs text-destructive/90">
                            {t.transcricao_rr_alerta}
                          </p>
                        </div>
                      </div>
                    )}

                  {(t.repetitivos_matches ?? []).map((m) => (
                    <div
                      key={m.numero}
                      className={
                        m.kind === "alta"
                          ? "flex items-start gap-2 rounded-md border border-success/40 bg-success/10 p-3"
                          : "flex items-start gap-2 rounded-md border border-warning/40 bg-warning/10 p-3"
                      }
                    >
                      <CheckCircle2
                        className={
                          m.kind === "alta"
                            ? "mt-0.5 h-4 w-4 shrink-0 text-success"
                            : "mt-0.5 h-4 w-4 shrink-0 text-warning"
                        }
                      />
                      <div className="space-y-1">
                        <p
                          className={
                            m.kind === "alta"
                              ? "text-xs font-semibold text-success"
                              : "text-xs font-semibold text-warning"
                          }
                        >
                          {m.kind === "media" && "Possível aderência · "}
                          Tema {m.numero} do TST · {m.situacao === "suspenso" ? "suspenso" : m.situacao === "decidido" ? "decidido" : m.situacao}
                        </p>
                        <p className="text-xs text-foreground/85">{m.descricao}</p>
                        {m.tese && (
                          <p className="text-xs italic text-foreground/70">
                            <strong className="font-medium">Tese firmada:</strong>{" "}
                            {m.tese}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}

                  <ListBlock
                    label="Fundamentos argumentativos"
                    items={t.fundamentos_argumentativos}
                  />
                  <ListBlock
                    label="Permissivos invocados"
                    items={t.permissivos_invocados}
                  />
                  <ListBlock label="Óbices aplicáveis" items={t.obices_aplicaveis} />
                  <ListBlock
                    label="Jurisprudência citada"
                    items={t.jurisprudencia_citada}
                  />
                  {t.conclusao_sugerida && (
                    <p className="rounded-md bg-card px-3 py-2 text-sm">
                      <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                        Conclusão sugerida ·{" "}
                      </span>
                      {t.conclusao_sugerida}
                    </p>
                  )}
                </section>
              );
            })}
          </CardContent>
        </Card>
      ))}
      {obs && !hasAlignmentWarning && (
        <p className="text-xs text-muted-foreground">
          <strong className="font-medium">Observações:</strong> {obs}
        </p>
      )}
    </div>
  );
}
