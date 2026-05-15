"use client";

import { useActionState, useState } from "react";

import {
  generateMinutaDraftAction,
  saveMinutaAction,
  triggerDocxAction,
  type MinutaDraftState,
  type SaveMinutaState,
} from "../actions";

const INITIAL_DRAFT: MinutaDraftState = {};
const INITIAL_SAVE: SaveMinutaState = {};

interface Props {
  caseId: string;
  initial: string;
  hasMinuta: boolean;
  hasDocx: boolean;
}

export function MinutaPanel({ caseId, initial, hasMinuta, hasDocx }: Props) {
  const [text, setText] = useState(initial);
  const [draftState, draftFormAction, draftPending] = useActionState(
    generateMinutaDraftAction,
    INITIAL_DRAFT,
  );
  const [saveState, saveFormAction, savePending] = useActionState(
    saveMinutaAction,
    INITIAL_SAVE,
  );

  // Quando o rascunho chega, atualiza a textarea sem perder o que o usuário digitou
  if (draftState.text && draftState.text !== text && !text.trim()) {
    setText(draftState.text);
  }

  return (
    <section className="space-y-3 rounded-md border p-4">
      <header className="space-y-1">
        <h2 className="text-sm font-medium">Minuta</h2>
        <p className="text-xs text-muted-foreground">
          Gere um rascunho a partir do dossiê, ajuste o texto, salve e baixe o
          DOCX.
        </p>
      </header>

      <form action={draftFormAction} className="flex flex-wrap items-center gap-2">
        <input type="hidden" name="id" value={caseId} />
        <button
          type="submit"
          disabled={draftPending}
          className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm font-medium hover:bg-accent disabled:opacity-50"
        >
          {draftPending ? "Gerando…" : "Gerar rascunho"}
        </button>
        {draftState.error && (
          <span className="text-sm text-destructive">{draftState.error}</span>
        )}
        {draftState.text && !draftState.error && (
          <button
            type="button"
            onClick={() => setText(draftState.text!)}
            className="text-xs text-primary underline"
          >
            substituir editor com novo rascunho
          </button>
        )}
      </form>

      <form action={saveFormAction} className="space-y-3">
        <input type="hidden" name="id" value={caseId} />
        <textarea
          name="text"
          rows={20}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="[[CORPO]]&#10;PROCESSO Nº ..."
          className="w-full rounded-md border bg-background p-3 font-mono text-xs"
        />
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="submit"
            disabled={savePending || !text.trim()}
            className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {savePending ? "Salvando…" : "Salvar minuta"}
          </button>
          {saveState.ok && (
            <span className="text-sm text-emerald-600">Salvo.</span>
          )}
          {saveState.error && (
            <span className="text-sm text-destructive">{saveState.error}</span>
          )}
        </div>
      </form>

      <div className="flex flex-wrap items-center gap-2">
        <form action={triggerDocxAction}>
          <input type="hidden" name="id" value={caseId} />
          <button
            type="submit"
            disabled={!hasMinuta}
            className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm font-medium hover:bg-accent disabled:opacity-50"
          >
            {hasDocx ? "Regerar DOCX" : "Gerar DOCX"}
          </button>
        </form>
        {hasDocx && (
          <a
            href={`/cases/${caseId}/docx`}
            className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Baixar DOCX
          </a>
        )}
      </div>
    </section>
  );
}
