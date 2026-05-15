"use client";

import { useActionState } from "react";

import { anonymizeAction, type AnonymizerState } from "./actions";

const INITIAL: AnonymizerState = {};

const SAMPLE = `Trata-se de Recurso de Revista interposto por João da Silva Santos (CPF 123.456.789-00), reclamante, contra Acme Indústria Têxtil LTDA (CNPJ 12.345.678/0001-90), com sede na Rua das Flores, 123, Recife/PE.

O reclamante foi admitido em 15/03/2010 e dispensado em 30/06/2023. Email: joao.silva@gmail.com. Telefone: (81) 99999-1234.

Advogado: Dr. Pedro Costa, OAB/PE 45678.`;

export function AnonymizerForm() {
  const [state, formAction, pending] = useActionState(anonymizeAction, INITIAL);
  return (
    <form action={formAction} className="space-y-4">
      <textarea
        name="text"
        rows={10}
        defaultValue={SAMPLE}
        className="w-full rounded-md border bg-background p-3 font-mono text-xs"
      />
      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={pending}
          className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {pending ? "Anonimizando…" : "Anonimizar"}
        </button>
        {state.error && (
          <span className="text-sm text-destructive">{state.error}</span>
        )}
      </div>

      {state.result && (
        <div className="space-y-3">
          <div className="rounded-md border p-3">
            <h2 className="mb-2 text-sm font-medium">
              Texto anonimizado ({state.result.substitutions} substituições)
            </h2>
            <pre className="whitespace-pre-wrap font-mono text-xs">
              {state.result.anonymized}
            </pre>
          </div>
          <div className="rounded-md border p-3">
            <h2 className="mb-2 text-sm font-medium">Mapping</h2>
            {Object.entries(state.result.mapping).length === 0 ? (
              <p className="text-xs text-muted-foreground">Nada substituído.</p>
            ) : (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-muted-foreground">
                    <th className="py-1">Placeholder</th>
                    <th className="py-1">Original</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(state.result.mapping).map(([k, v]) => (
                    <tr key={k} className="border-t">
                      <td className="py-1 font-mono">{k}</td>
                      <td className="py-1 font-mono">{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </form>
  );
}
