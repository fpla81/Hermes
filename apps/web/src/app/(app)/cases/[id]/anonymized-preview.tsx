"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import { Eye, Shield } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { AnonymizedPreview } from "@/lib/cases";

import { getAnonymizedPreviewAction } from "../actions";

interface Props {
  caseId: string;
}

const TIPO_LABEL: Record<string, string> = {
  despacho_admissibilidade: "Despacho de Admissibilidade",
  recurso_revista: "Recurso de Revista",
  agravo_instrumento: "Agravo de Instrumento",
  agravo_interno: "Agravo Interno",
  embargos_declaracao: "Embargos de Declaração",
  acordao_regional: "Acórdão Regional",
};

const PARTE_LABEL: Record<string, string> = {
  reclamante: "Reclamante",
  reclamada: "Reclamada",
  reclamantes: "Reclamantes",
  reclamadas: "Reclamadas",
};

const PLACEHOLDER_RE = /\b(?:RECLAMANTE_\d+|RECLAMADA_\d+)\b|<(?:CPF|CNPJ|OAB|EMAIL|PHONE)_\d+>/g;

function highlightPlaceholders(text: string): { __html: string } {
  // escape HTML primeiro
  const esc = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  const html = esc.replace(PLACEHOLDER_RE, (m) =>
    `<mark class="rounded bg-success/20 px-0.5 font-mono text-success">${m}</mark>`,
  );
  return { __html: html };
}

export function AnonymizedPreviewButton({ caseId }: Props) {
  const [open, setOpen] = useState(false);
  const [preview, setPreview] = useState<AnonymizedPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, startLoad] = useTransition();

  useEffect(() => {
    if (!open || preview || loading) return;
    setError(null);
    startLoad(async () => {
      const res = await getAnonymizedPreviewAction(caseId);
      if (res.error) setError(res.error);
      else setPreview(res.preview ?? null);
    });
  }, [open, preview, loading, caseId]);

  const total = useMemo(() => {
    if (!preview) return 0;
    return preview.pieces.reduce((acc, p) => acc + p.substitutions, 0);
  }, [preview]);

  return (
    <>
      <Button type="button" variant="outline" onClick={() => setOpen(true)}>
        <Eye className="h-4 w-4" />
        Ver input anonimizado
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="flex max-h-[90vh] max-w-5xl flex-col gap-0 p-0">
          <DialogHeader className="border-b p-6 pb-4">
            <DialogTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              Input que vai pro LLM
            </DialogTitle>
            <DialogDescription>
              Texto de cada peça já com substituições de partes, CPF, CNPJ,
              OAB, email e telefone. É exatamente isto que sai do servidor.
              Destacado em verde = trecho mascarado.
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto p-6">
            {loading && (
              <p className="text-sm text-muted-foreground">
                Anonimizando…
              </p>
            )}
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            {preview && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-2 rounded-md border bg-muted/30 p-3 text-xs">
                  <span className="font-medium">
                    {preview.pieces.length} peça
                    {preview.pieces.length !== 1 && "s"} ·
                  </span>
                  <span>{total} substituição{total !== 1 && "ões"} total</span>
                  <span className="text-muted-foreground">·</span>
                  <span>
                    {preview.parties.length} parte
                    {preview.parties.length !== 1 && "s"} cadastrada
                    {preview.parties.length !== 1 && "s"}
                  </span>
                </div>

                {preview.pieces.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    Este caso ainda não tem peças. Vá ao step Peças e cadastre
                    pelo menos uma antes de analisar.
                  </p>
                )}

                {preview.pieces.map((p) => (
                  <section
                    key={p.index}
                    className="space-y-2 rounded-lg border bg-card"
                  >
                    <header className="flex flex-wrap items-center justify-between gap-2 border-b bg-muted/20 px-4 py-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">
                          {TIPO_LABEL[p.tipo] ?? p.tipo}
                        </Badge>
                        {p.parte && (
                          <Badge variant="muted">
                            {PARTE_LABEL[p.parte] ?? p.parte}
                          </Badge>
                        )}
                        {p.data && (
                          <span className="text-xs text-muted-foreground">
                            {p.data}
                          </span>
                        )}
                      </div>
                      <span className="text-[10px] text-muted-foreground">
                        {p.anonimizado_chars.toLocaleString("pt-BR")} chars ·{" "}
                        {p.substitutions} substituiç
                        {p.substitutions === 1 ? "ão" : "ões"}
                      </span>
                    </header>
                    <pre
                      className="max-h-96 overflow-auto whitespace-pre-wrap break-words px-4 py-3 text-[11px] leading-relaxed"
                      dangerouslySetInnerHTML={highlightPlaceholders(
                        p.anonimizado,
                      )}
                    />
                    {Object.keys(p.mapping_sample).length > 0 && (
                      <details className="border-t bg-muted/10 px-4 py-2 text-xs">
                        <summary className="cursor-pointer text-muted-foreground">
                          Mostrar amostra do mapa de substituições (primeiros 20)
                        </summary>
                        <table className="mt-2 w-full text-[11px]">
                          <tbody>
                            {Object.entries(p.mapping_sample).map(([k, v]) => (
                              <tr key={k} className="border-b last:border-b-0">
                                <td className="py-1 pr-3 font-mono text-success">
                                  {k}
                                </td>
                                <td className="py-1 text-muted-foreground">
                                  → {v}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </details>
                    )}
                  </section>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
