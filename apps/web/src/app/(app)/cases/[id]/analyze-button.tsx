"use client";

import { useActionState } from "react";

import { analyzeCaseAction, type AnalyzeState } from "../actions";

const INITIAL: AnalyzeState = {};

interface Props {
  caseId: string;
  alreadyAnalyzed: boolean;
  /** Worker está rodando a task (status do case == "analyzing"). */
  inFlight: boolean;
  /** Erro persistido no caso após análise anterior. */
  lastError: string | null;
}

export function AnalyzeButton({ caseId, alreadyAnalyzed, inFlight, lastError }: Props) {
  const [state, formAction, pending] = useActionState(analyzeCaseAction, INITIAL);
  const examining = pending || inFlight;
  return (
    <div className="flex flex-col items-end gap-2">
      <form action={formAction}>
        <input type="hidden" name="id" value={caseId} />
        <button
          type="submit"
          disabled={examining}
          className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm font-medium hover:bg-accent disabled:opacity-50"
        >
          {examining ? (
            <span className="animate-pulse">Examinando…</span>
          ) : alreadyAnalyzed ? (
            "Reanalisar"
          ) : (
            "Analisar"
          )}
        </button>
      </form>
      {state.error && (
        <p className="text-xs text-destructive">Erro: {state.error}</p>
      )}
      {!state.error && lastError && !examining && (
        <p className="text-xs text-destructive">Último erro: {lastError}</p>
      )}
    </div>
  );
}
