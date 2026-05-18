"use client";

import { useActionState } from "react";

import {
  uploadMinutaAction,
  uploadPiecesAction,
  uploadPreparedAction,
  type UploadMinutaState,
  type UploadPiecesState,
  type UploadPreparedState,
} from "../actions";

export function PiecesForm({ caseId }: { caseId: string }) {
  const [state, formAction, pending] = useActionState<UploadPiecesState, FormData>(
    uploadPiecesAction,
    {},
  );
  return (
    <form action={formAction} className="space-y-2">
      <input type="hidden" name="id" value={caseId} />
      <textarea
        name="pieces_json"
        rows={8}
        placeholder='[{"tipo":"Despacho de Admissibilidade do TRT","data":"15/03/2024","id":"12345","html_url":"/pecas/12345/html","bin_url":"/pecas/12345/bin"}]'
        className="w-full rounded-md border bg-background p-2 font-mono text-xs"
      />
      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={pending}
          className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {pending ? "Enviando…" : "Salvar pieces"}
        </button>
        {state.ok && <span className="text-sm text-emerald-600">Salvo.</span>}
        {state.error && <span className="text-sm text-destructive">{state.error}</span>}
      </div>
    </form>
  );
}

export function PreparedUploadForm({ caseId }: { caseId: string }) {
  const [state, formAction, pending] = useActionState<UploadPreparedState, FormData>(
    uploadPreparedAction,
    {},
  );
  return (
    <form action={formAction} className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="id" value={caseId} />
      <input
        type="file"
        name="file"
        accept=".txt,.md,.html,.htm,.pdf,.docx"
        className="text-sm"
      />
      <button
        type="submit"
        disabled={pending}
        className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm font-medium hover:bg-accent disabled:opacity-50"
      >
        {pending ? "Enviando…" : "Subir arquivo"}
      </button>
      {state.error && <span className="text-sm text-destructive">{state.error}</span>}
    </form>
  );
}

export function MinutaForm({ caseId, initial }: { caseId: string; initial: string }) {
  const [state, formAction, pending] = useActionState<UploadMinutaState, FormData>(
    uploadMinutaAction,
    {},
  );
  return (
    <form action={formAction} className="space-y-2">
      <input type="hidden" name="id" value={caseId} />
      <textarea
        name="text"
        rows={14}
        defaultValue={initial}
        placeholder="[[CORPO]]&#10;RECURSO DE REVISTA DA RECLAMADA&#10;&#10;TEMA - HORAS EXTRAS&#10;&#10;Trata-se de recurso interposto…"
        className="w-full rounded-md border bg-background p-2 font-mono text-xs"
      />
      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={pending}
          className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {pending ? "Salvando…" : "Salvar minuta"}
        </button>
        {state.ok && <span className="text-sm text-emerald-600">Salvo.</span>}
        {state.error && <span className="text-sm text-destructive">{state.error}</span>}
      </div>
    </form>
  );
}
