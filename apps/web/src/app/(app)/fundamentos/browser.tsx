"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { deleteFundamento, type Fundamento } from "@/lib/fundamentos";

const inputClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

export function FundamentosBrowser({
  initialQuery,
  initialTema,
  items,
}: {
  initialQuery: string;
  initialTema: string;
  items: Fundamento[];
}) {
  const router = useRouter();
  const [q, setQ] = useState(initialQuery);
  const [tema, setTema] = useState(initialTema);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [removing, setRemoving] = useState<string | null>(null);
  const [, startTransition] = useTransition();

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams();
    if (q.trim()) params.set("q", q.trim());
    if (tema.trim()) params.set("tema", tema.trim());
    const qs = params.toString();
    startTransition(() => {
      router.push(qs ? `/fundamentos?${qs}` : "/fundamentos");
    });
  };

  const onDelete = async (id: string) => {
    if (!confirm("Remover esta fundamentação?")) return;
    setRemoving(id);
    try {
      await deleteFundamento(id);
      startTransition(() => router.refresh());
    } finally {
      setRemoving(null);
    }
  };

  return (
    <div className="space-y-4">
      <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-2">
        <div className="flex-1 space-y-1 min-w-[180px]">
          <label className="text-xs text-muted-foreground">Buscar (título, resumo, tema)</label>
          <input className={inputClass} value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="flex-1 space-y-1 min-w-[180px]">
          <label className="text-xs text-muted-foreground">Filtrar por tema</label>
          <input
            className={inputClass}
            value={tema}
            onChange={(e) => setTema(e.target.value)}
            placeholder="Ex.: DANO MORAL"
          />
        </div>
        <button
          type="submit"
          className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Filtrar
        </button>
      </form>

      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Nenhuma fundamentação registrada. Use o botão &quot;Aprender fundamentação&quot;
          ao final de uma minuta para começar a base.
        </p>
      ) : (
        <ul className="space-y-3">
          {items.map((f) => (
            <li key={f.id} className="space-y-2 rounded-md border bg-background p-4">
              <header className="flex flex-wrap items-start justify-between gap-2">
                <div className="space-y-1">
                  <h3 className="text-sm font-semibold">{f.titulo}</h3>
                  <p className="text-xs font-mono uppercase text-muted-foreground">
                    {f.tema}
                  </p>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>usos: {f.usage_count}</span>
                  <button
                    type="button"
                    onClick={() => onDelete(f.id)}
                    disabled={removing === f.id}
                    className="rounded border px-2 py-0.5 text-xs hover:bg-accent disabled:opacity-50"
                  >
                    {removing === f.id ? "Removendo…" : "Remover"}
                  </button>
                </div>
              </header>
              {f.resumo && <p className="text-sm">{f.resumo}</p>}
              {f.tags && f.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {f.tags.map((t, i) => (
                    <span
                      key={i}
                      className="rounded-full bg-muted px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              )}
              <button
                type="button"
                onClick={() =>
                  setExpanded((e) => ({ ...e, [f.id]: !e[f.id] }))
                }
                className="text-xs text-primary underline"
              >
                {expanded[f.id] ? "ocultar corpo" : "ver corpo da fundamentação"}
              </button>
              {expanded[f.id] && (
                <pre className="overflow-auto rounded border bg-muted/30 p-3 text-xs whitespace-pre-wrap">
                  {f.corpo_md}
                </pre>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
