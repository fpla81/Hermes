"use client";

import { useActionState } from "react";

import { importHtmlAction, type ImportState } from "./actions";

const INITIAL: ImportState = {};

export function ImportForm() {
  const [state, formAction, pending] = useActionState(importHtmlAction, INITIAL);
  return (
    <form action={formAction} className="space-y-3">
      <textarea
        name="payload"
        rows={16}
        placeholder='{"numero_processo":"0001234-56.2023.5.06.0020","html":"<html>...","url":"https://..."}'
        className="w-full rounded-md border bg-background p-3 font-mono text-xs"
        required
      />
      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={pending}
          className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {pending ? "Importando…" : "Importar"}
        </button>
        {state.error && <span className="text-sm text-destructive">{state.error}</span>}
      </div>
    </form>
  );
}
