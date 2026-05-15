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
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <ul className="ml-4 list-disc space-y-1 text-sm">
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
  return (
    <div className="space-y-6">
      {dossie.recursos.map((r, i) => (
        <article key={i} className="space-y-3 rounded-md border p-4">
          <header>
            <h3 className="text-sm font-medium">
              {TIPO_LABEL[r.tipo] ?? r.tipo} · {PARTE_LABEL[r.parte] ?? r.parte}
            </h3>
          </header>
          {(r.temas || []).map((t, j) => (
            <section key={j} className="space-y-2 rounded border bg-muted/20 p-3">
              <h4 className="text-sm font-semibold">{t.nome}</h4>
              <ListBlock label="Fundamentos argumentativos" items={t.fundamentos_argumentativos} />
              <ListBlock label="Permissivos invocados" items={t.permissivos_invocados} />
              <ListBlock label="Óbices aplicáveis" items={t.obices_aplicaveis} />
              <ListBlock label="Jurisprudência citada" items={t.jurisprudencia_citada} />
              {t.conclusao_sugerida && (
                <p className="text-sm">
                  <span className="font-medium">Conclusão sugerida: </span>
                  {t.conclusao_sugerida}
                </p>
              )}
            </section>
          ))}
        </article>
      ))}
      {dossie.observacoes && (
        <p className="text-xs text-muted-foreground">
          <strong>Observações:</strong> {dossie.observacoes}
        </p>
      )}
    </div>
  );
}
