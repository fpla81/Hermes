"use client";

import { useActionState, useEffect, useState } from "react";

import { MinutaTiptap } from "../cases/[id]/minuta-tiptap";

import { updateFundamentoAction, type UpdateState } from "./actions";
import type { Fundamento } from "@/lib/fundamentos-types";

const INITIAL: UpdateState = {};

const inputClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

interface Props {
  open: boolean;
  onClose: () => void;
  fundamento: Fundamento;
}

export function FundamentoEditorDialog({ open, onClose, fundamento }: Props) {
  const [tema, setTema] = useState(fundamento.tema);
  const [titulo, setTitulo] = useState(fundamento.titulo);
  const [resumo, setResumo] = useState(fundamento.resumo ?? "");
  const [tags, setTags] = useState((fundamento.tags ?? []).join(", "));
  const [corpo, setCorpo] = useState(fundamento.corpo_md);
  const [state, formAction, pending] = useActionState(
    updateFundamentoAction,
    INITIAL,
  );

  useEffect(() => {
    if (state.ok) {
      const t = setTimeout(onClose, 600);
      return () => clearTimeout(t);
    }
  }, [state.ok, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="my-8 w-full max-w-4xl space-y-4 rounded-md border bg-background p-6 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-start justify-between">
          <h2 className="text-base font-semibold">Editar fundamentação</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            ✕
          </button>
        </header>

        <form action={formAction} className="space-y-4">
          <input type="hidden" name="id" value={fundamento.id} />
          <input type="hidden" name="corpo_md" value={corpo} />

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Tema</label>
              <input
                name="tema"
                className={`${inputClass} font-mono uppercase`}
                value={tema}
                onChange={(e) => setTema(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Título</label>
              <input
                name="titulo"
                className={inputClass}
                value={titulo}
                onChange={(e) => setTitulo(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">
              Tags (separadas por vírgula)
            </label>
            <input
              name="tags"
              className={inputClass}
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="dano moral, quantum, art 944 CC"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">
              Resumo (vai pro índice de busca)
            </label>
            <textarea
              name="resumo"
              rows={2}
              className="w-full resize-none rounded-md border bg-background p-2 text-sm"
              value={resumo}
              onChange={(e) => setResumo(e.target.value)}
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Corpo da fundamentação</label>
            <MinutaTiptap value={corpo} onChange={setCorpo} />
          </div>

          <div className="flex items-center justify-end gap-2">
            {state.ok && (
              <span className="text-xs text-emerald-600">Salvo.</span>
            )}
            {state.error && (
              <span className="text-xs text-destructive">{state.error}</span>
            )}
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm hover:bg-accent"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={pending}
              className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {pending ? "Salvando…" : "Salvar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
