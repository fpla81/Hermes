"use client";

import { useActionState } from "react";

import { updatePartiesAction, type UpdatePartiesState } from "../actions";
import { PartiesEditor } from "../parties-editor";
import type { Party } from "@/lib/cases";

const initial: UpdatePartiesState = {};

export function PartiesPanel({
  caseId,
  parties,
}: {
  caseId: string;
  parties: Party[] | null;
}) {
  const [state, action, pending] = useActionState(updatePartiesAction, initial);
  return (
    <section className="space-y-3 rounded-md border p-4">
      <header>
        <h2 className="text-sm font-medium">Partes do processo</h2>
        <p className="text-xs text-muted-foreground">
          Edite antes de analisar — após o &quot;Analisar&quot;, os nomes daqui
          serão substituídos nos textos das peças antes do LLM ler.
        </p>
      </header>
      <form action={action} className="space-y-4">
        <input type="hidden" name="id" value={caseId} />
        <PartiesEditor initial={parties ?? []} />
        <div className="flex items-center gap-2">
          <button
            type="submit"
            disabled={pending}
            className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {pending ? "Salvando..." : "Salvar partes"}
          </button>
          {state.ok && <span className="text-xs text-emerald-600">Salvo.</span>}
          {state.error && (
            <span className="text-xs text-destructive">{state.error}</span>
          )}
        </div>
      </form>
    </section>
  );
}
