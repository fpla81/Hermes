"use client";

import { useActionState, useEffect, useState } from "react";

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
import type { Fundamento } from "@/lib/fundamentos-types";

import { MinutaTiptap } from "../cases/[id]/minuta-tiptap";

import { updateFundamentoAction, type UpdateState } from "./actions";

const INITIAL: UpdateState = {};

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

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>Editar fundamentação</DialogTitle>
          <DialogDescription>
            Ajuste tema, título, tags e corpo. As alterações entram em vigor
            imediatamente nas próximas minutas geradas.
          </DialogDescription>
        </DialogHeader>

        <form action={formAction} className="space-y-5">
          <input type="hidden" name="id" value={fundamento.id} />
          <input type="hidden" name="corpo_md" value={corpo} />

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="ed-tema">Tema</Label>
              <Input
                id="ed-tema"
                name="tema"
                className="font-mono uppercase"
                value={tema}
                onChange={(e) => setTema(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="ed-titulo">Título</Label>
              <Input
                id="ed-titulo"
                name="titulo"
                value={titulo}
                onChange={(e) => setTitulo(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="ed-tags">Tags (separadas por vírgula)</Label>
            <Input
              id="ed-tags"
              name="tags"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="dano moral, quantum, art 944 CC"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="ed-resumo">Resumo (vai pro índice de busca)</Label>
            <Textarea
              id="ed-resumo"
              name="resumo"
              rows={2}
              value={resumo}
              onChange={(e) => setResumo(e.target.value)}
              className="resize-none"
            />
          </div>

          <div className="space-y-1.5">
            <Label>Corpo da fundamentação</Label>
            <MinutaTiptap value={corpo} onChange={setCorpo} />
          </div>

          <DialogFooter className="items-center">
            {state.ok && (
              <span className="mr-auto text-xs text-success">Salvo com sucesso.</span>
            )}
            {state.error && (
              <span className="mr-auto text-xs text-destructive">{state.error}</span>
            )}
            <Button type="button" variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" disabled={pending}>
              {pending ? "Salvando…" : "Salvar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
