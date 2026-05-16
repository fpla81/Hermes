"use client";

import { useActionState, useState } from "react";

import {
  generateMinutaDraftAction,
  learnFundamentosAction,
  saveMinutaAction,
  triggerDocxAction,
  type LearnState,
  type MinutaDraftState,
  type SaveMinutaState,
} from "../actions";
import { MinutaTiptap } from "./minuta-tiptap";

const INITIAL_DRAFT: MinutaDraftState = {};
const INITIAL_SAVE: SaveMinutaState = {};

interface Props {
  caseId: string;
  initial: string;
  hasMinuta: boolean;
  hasDocx: boolean;
  canLearn: boolean;
}

export function MinutaEditor({
  caseId,
  initial,
  hasMinuta,
  hasDocx,
  canLearn,
}: Props) {
  const [text, setText] = useState(initial);
  const [draftState, draftFormAction, draftPending] = useActionState(
    generateMinutaDraftAction,
    INITIAL_DRAFT,
  );
  const [saveState, saveFormAction, savePending] = useActionState(
    saveMinutaAction,
    INITIAL_SAVE,
  );
  const [learnState, learnFormAction, learning] = useActionState(
    learnFundamentosAction,
    {} as LearnState,
  );
  const [showRaw, setShowRaw] = useState(false);

  // Quando o rascunho chega, oferece substituir
  if (draftState.text && draftState.text !== text && !text.trim()) {
    setText(draftState.text);
  }

  const learnMsg = learnState.ok
    ? learnState.learned && learnState.learned > 0
      ? `${learnState.learned} fundamentação${learnState.learned > 1 ? "ões" : ""} guardada${learnState.learned > 1 ? "s" : ""} na base.`
      : "Nenhuma fundamentação extraída — verifique se a minuta está salva e bate com o dossiê."
    : null;

  return (
    <section className="space-y-3 rounded-md border p-4">
      <header className="space-y-1">
        <h2 className="text-sm font-medium">Minuta</h2>
        <p className="text-xs text-muted-foreground">
          Editor à esquerda, prévia formatada à direita. Salve antes de gerar o
          DOCX ou aprender a fundamentação.
        </p>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        <form action={draftFormAction}>
          <input type="hidden" name="id" value={caseId} />
          <button
            type="submit"
            disabled={draftPending}
            className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm font-medium hover:bg-accent disabled:opacity-50"
          >
            {draftPending ? "Gerando…" : "Gerar rascunho"}
          </button>
        </form>
        {draftState.error && (
          <span className="text-xs text-destructive">{draftState.error}</span>
        )}
        {draftState.text && !draftState.error && (
          <button
            type="button"
            onClick={() => setText(draftState.text!)}
            className="text-xs text-primary underline"
          >
            usar rascunho gerado
          </button>
        )}

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

        {canLearn && (
          <form action={learnFormAction} className="ml-auto">
            <input type="hidden" name="case_id" value={caseId} />
            <button
              type="submit"
              disabled={!hasMinuta || learning}
              title={
                hasMinuta
                  ? "Extrai as fundamentações da minuta e salva na base do gabinete"
                  : "Salve a minuta primeiro"
              }
              className="inline-flex h-9 items-center rounded-md border border-emerald-300 bg-emerald-50 px-3 text-sm font-medium text-emerald-900 hover:bg-emerald-100 disabled:opacity-50"
            >
              {learning ? "Aprendendo…" : "Aprender fundamentação"}
            </button>
          </form>
        )}
      </div>

      {learnMsg && (
        <p className="text-xs text-emerald-700">{learnMsg}</p>
      )}
      {learnState.error && (
        <p className="text-xs text-destructive">{learnState.error}</p>
      )}

      <form action={saveFormAction} className="space-y-3">
        <input type="hidden" name="id" value={caseId} />
        <input type="hidden" name="text" value={text} />

        <div className="flex items-center justify-end">
          <button
            type="button"
            onClick={() => setShowRaw((v) => !v)}
            className="text-xs text-muted-foreground underline hover:text-foreground"
          >
            {showRaw ? "voltar ao editor visual" : "ver código markdown"}
          </button>
        </div>

        {showRaw ? (
          <textarea
            rows={28}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="[[CORPO]]&#10;PROCESSO Nº ..."
            spellCheck={false}
            className="w-full rounded-md border bg-background p-3 font-mono text-xs leading-relaxed"
          />
        ) : (
          <MinutaTiptap value={text} onChange={setText} />
        )}

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="submit"
            disabled={savePending || !text.trim()}
            className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {savePending ? "Salvando…" : "Salvar minuta"}
          </button>
          {saveState.ok && (
            <span className="text-xs text-emerald-600">Salvo.</span>
          )}
          {saveState.error && (
            <span className="text-xs text-destructive">{saveState.error}</span>
          )}
        </div>
      </form>
    </section>
  );
}
