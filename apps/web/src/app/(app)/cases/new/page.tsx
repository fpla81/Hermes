"use client";

import Link from "next/link";
import { useActionState } from "react";

import { createCaseAction, type CreateCaseState } from "../actions";

const initial: CreateCaseState = {};

export default function NewCasePage() {
  const [state, action, pending] = useActionState(createCaseAction, initial);

  return (
    <div className="max-w-lg space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Novo caso</h1>
        <p className="text-sm text-muted-foreground">
          Informe o número do processo TST no formato CNJ.
        </p>
      </div>

      <form action={action} className="space-y-4">
        <div className="space-y-1">
          <label htmlFor="numero_processo" className="text-sm font-medium">
            Número do processo
          </label>
          <input
            id="numero_processo"
            name="numero_processo"
            placeholder="0001234-56.2023.5.10.0001"
            required
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm font-mono shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </div>

        <div className="space-y-1">
          <label htmlFor="titulo" className="text-sm font-medium">
            Título (opcional)
          </label>
          <input
            id="titulo"
            name="titulo"
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </div>

        {state.error && (
          <p className="text-sm text-destructive">{state.error}</p>
        )}

        <div className="flex items-center gap-2">
          <button
            type="submit"
            disabled={pending}
            className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {pending ? "Salvando..." : "Criar"}
          </button>
          <Link
            href="/cases"
            className="inline-flex h-9 items-center rounded-md border px-3 text-sm hover:bg-accent"
          >
            Cancelar
          </Link>
        </div>
      </form>
    </div>
  );
}
