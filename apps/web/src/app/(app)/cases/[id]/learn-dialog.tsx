"use client";

import { useState, useTransition } from "react";
import { ChevronDown, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { FundamentoExtractedItem } from "@/lib/fundamentos-types";
import { cn } from "@/lib/utils";

import { saveFundamentosAction } from "../actions";

interface Props {
  open: boolean;
  onClose: () => void;
  initial: FundamentoExtractedItem[];
}

interface DraftRow extends FundamentoExtractedItem {
  selected: boolean;
  expanded: boolean;
  tagsText: string;
}

export function LearnFundamentosDialog({ open, onClose, initial }: Props) {
  const [rows, setRows] = useState<DraftRow[]>(() =>
    initial.map((f) => ({
      ...f,
      selected: true,
      expanded: false,
      tagsText: (f.tags ?? []).join(", "),
    })),
  );
  const [saving, startSave] = useTransition();
  const [saved, setSaved] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedCount = rows.filter((r) => r.selected).length;

  const update = (i: number, patch: Partial<DraftRow>) => {
    setRows((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  };

  const handleSave = () => {
    setError(null);
    const items = rows
      .filter((r) => r.selected)
      .map((r) => ({
        tema: r.tema,
        titulo: r.titulo,
        corpo_md: r.corpo_md,
        tags: r.tagsText
          ? r.tagsText.split(",").map((t) => t.trim()).filter(Boolean)
          : [],
        resumo: r.resumo,
        conclusao_provimento: r.conclusao_provimento,
        conclusao_nao_conhecimento: r.conclusao_nao_conhecimento,
        source_case_id: r.source_case_id,
      }));
    startSave(async () => {
      const res = await saveFundamentosAction(items);
      if (res.error) {
        setError(res.error);
      } else {
        setSaved(res.saved ?? 0);
        setTimeout(onClose, 900);
      }
    });
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && !saving && onClose()}>
      <DialogContent className="max-h-[85vh] max-w-3xl overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            Fundamentações extraídas da minuta
          </DialogTitle>
          <DialogDescription>
            Desmarque as que forem específicas demais deste caso e não devem
            entrar na base. Você pode ajustar título e tags antes de salvar.
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[55vh] -mx-2 overflow-y-auto px-2">
          {rows.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">
              Nenhuma fundamentação extraível desta minuta — verifique se a
              minuta está salva e bate com o dossiê.
            </p>
          ) : (
            <ul className="space-y-3 py-2">
              {rows.map((r, i) => (
                <li
                  key={i}
                  className={cn(
                    "space-y-3 rounded-lg border p-4 transition-colors",
                    r.selected ? "bg-card" : "bg-muted/30 opacity-60",
                  )}
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={r.selected}
                      onChange={(e) =>
                        update(i, { selected: e.target.checked })
                      }
                      className="mt-1 h-4 w-4 cursor-pointer"
                    />
                    <div className="flex-1 space-y-2">
                      <Badge variant="muted" className="font-mono">
                        {r.tema}
                      </Badge>
                      <div className="space-y-1">
                        <Label htmlFor={`t-${i}`}>Título</Label>
                        <Input
                          id={`t-${i}`}
                          value={r.titulo}
                          disabled={!r.selected}
                          onChange={(e) => update(i, { titulo: e.target.value })}
                        />
                      </div>
                      {r.resumo && (
                        <p className="text-xs italic text-muted-foreground">
                          {r.resumo}
                        </p>
                      )}
                      <div className="space-y-1">
                        <Label htmlFor={`tag-${i}`}>
                          Tags (separadas por vírgula)
                        </Label>
                        <Input
                          id={`tag-${i}`}
                          value={r.tagsText}
                          disabled={!r.selected}
                          onChange={(e) =>
                            update(i, { tagsText: e.target.value })
                          }
                        />
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => update(i, { expanded: !r.expanded })}
                        className="-ml-3 text-muted-foreground"
                      >
                        <ChevronDown
                          className={cn(
                            "h-3.5 w-3.5 transition-transform",
                            r.expanded && "rotate-180",
                          )}
                        />
                        {r.expanded
                          ? "Ocultar corpo e conclusões"
                          : "Ver corpo e conclusões"}
                      </Button>
                      {r.expanded && (
                        <div className="space-y-3 rounded-md border bg-muted/30 p-3">
                          <div className="space-y-1">
                            <Label className="text-[10px]">
                              Corpo da fundamentação
                            </Label>
                            <pre className="max-h-48 overflow-auto whitespace-pre-wrap text-[11px] leading-relaxed">
                              {r.corpo_md}
                            </pre>
                          </div>
                          {r.conclusao_provimento && (
                            <div className="space-y-1">
                              <Label className="text-[10px]">
                                Conclusão · contrariar → provimento
                              </Label>
                              <Textarea
                                rows={3}
                                value={r.conclusao_provimento}
                                onChange={(e) =>
                                  update(i, {
                                    conclusao_provimento: e.target.value,
                                  })
                                }
                                className="text-xs"
                              />
                            </div>
                          )}
                          {r.conclusao_nao_conhecimento && (
                            <div className="space-y-1">
                              <Label className="text-[10px]">
                                Conclusão · conforme → não conhecer
                              </Label>
                              <Textarea
                                rows={3}
                                value={r.conclusao_nao_conhecimento}
                                onChange={(e) =>
                                  update(i, {
                                    conclusao_nao_conhecimento: e.target.value,
                                  })
                                }
                                className="text-xs"
                              />
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <DialogFooter className="items-center">
          {error && (
            <span className="mr-auto text-xs text-destructive">{error}</span>
          )}
          {saved !== null && (
            <span className="mr-auto text-xs text-success">
              {saved} fundamentação{saved !== 1 ? "ões" : ""} salva{saved !== 1 ? "s" : ""}.
            </span>
          )}
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={saving}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            onClick={handleSave}
            disabled={saving || selectedCount === 0}
          >
            {saving
              ? "Salvando…"
              : `Salvar ${selectedCount} fundamentaç${selectedCount === 1 ? "ão" : "ões"}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
