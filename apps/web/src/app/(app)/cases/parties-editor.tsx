"use client";

import { useState } from "react";

import type { Party, PartyRole } from "@/lib/cases";

interface Props {
  initial?: Party[];
  hiddenInputName?: string;
}

interface PartyDraft {
  role: PartyRole;
  name: string;
  aliasesText: string;
}

const ROLE_LABEL: Record<PartyRole, string> = {
  reclamante: "Reclamante",
  reclamada: "Reclamada",
  ministerio_publico: "Ministério Público",
};

function makeDraft(role: PartyRole, name = "", aliases: string[] = []): PartyDraft {
  return { role, name, aliasesText: aliases.join(", ") };
}

function fromInitial(parties: Party[] | undefined): {
  reclamantes: PartyDraft[];
  reclamadas: PartyDraft[];
  mpt: PartyDraft | null;
} {
  const rec = (parties ?? [])
    .filter((p) => p.role === "reclamante")
    .sort((a, b) => a.ordinal - b.ordinal)
    .map((p) => makeDraft("reclamante", p.name, p.aliases));
  const rd = (parties ?? [])
    .filter((p) => p.role === "reclamada")
    .sort((a, b) => a.ordinal - b.ordinal)
    .map((p) => makeDraft("reclamada", p.name, p.aliases));
  const m = (parties ?? []).find((p) => p.role === "ministerio_publico");
  return {
    reclamantes: rec.length ? rec : [makeDraft("reclamante")],
    reclamadas: rd.length ? rd : [makeDraft("reclamada")],
    mpt: m ? makeDraft("ministerio_publico", m.name, m.aliases) : null,
  };
}

function serializeParties(drafts: {
  reclamantes: PartyDraft[];
  reclamadas: PartyDraft[];
  mpt: PartyDraft | null;
}): Party[] {
  const result: Party[] = [];
  drafts.reclamantes.forEach((d, i) => {
    if (d.name.trim()) {
      result.push({
        role: "reclamante",
        ordinal: i + 1,
        name: d.name.trim(),
        aliases: d.aliasesText
          .split(",")
          .map((a) => a.trim())
          .filter(Boolean),
      });
    }
  });
  drafts.reclamadas.forEach((d, i) => {
    if (d.name.trim()) {
      result.push({
        role: "reclamada",
        ordinal: i + 1,
        name: d.name.trim(),
        aliases: d.aliasesText
          .split(",")
          .map((a) => a.trim())
          .filter(Boolean),
      });
    }
  });
  if (drafts.mpt && drafts.mpt.name.trim()) {
    result.push({
      role: "ministerio_publico",
      ordinal: 1,
      name: drafts.mpt.name.trim(),
      aliases: [],
    });
  }
  return result;
}

const inputClass =
  "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

function PartyRow({
  draft,
  onChange,
  onRemove,
  showRemove,
  rolePrefix,
}: {
  draft: PartyDraft;
  onChange: (d: PartyDraft) => void;
  onRemove?: () => void;
  showRemove: boolean;
  rolePrefix: string;
}) {
  return (
    <div className="space-y-1 rounded border bg-muted/20 p-3">
      <div className="flex items-end gap-2">
        <div className="flex-1 space-y-1">
          <label className="text-xs text-muted-foreground">{rolePrefix} — nome completo</label>
          <input
            className={inputClass}
            value={draft.name}
            onChange={(e) => onChange({ ...draft, name: e.target.value })}
            placeholder="Ex.: Maria José Silva ou Porto do Recife S/A"
          />
        </div>
        {showRemove && onRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="inline-flex h-9 items-center rounded-md border px-3 text-sm hover:bg-accent"
            aria-label="Remover parte"
          >
            ×
          </button>
        )}
      </div>
      <div className="space-y-1">
        <label className="text-xs text-muted-foreground">
          Aliases (opcional, separados por vírgula)
        </label>
        <input
          className={inputClass}
          value={draft.aliasesText}
          onChange={(e) => onChange({ ...draft, aliasesText: e.target.value })}
          placeholder="Ex.: Porto do Recife, PORTO"
        />
      </div>
    </div>
  );
}

export function PartiesEditor({ initial, hiddenInputName = "parties_json" }: Props) {
  const [state, setState] = useState(() => fromInitial(initial));

  const updateAt = (
    list: PartyDraft[],
    index: number,
    next: PartyDraft,
  ): PartyDraft[] => list.map((d, i) => (i === index ? next : d));
  const removeAt = (list: PartyDraft[], index: number): PartyDraft[] =>
    list.filter((_, i) => i !== index);

  const serialized = JSON.stringify(serializeParties(state));

  return (
    <div className="space-y-4">
      <input type="hidden" name={hiddenInputName} value={serialized} />

      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium">Reclamantes</h3>
          <button
            type="button"
            onClick={() =>
              setState((s) => ({
                ...s,
                reclamantes: [...s.reclamantes, makeDraft("reclamante")],
              }))
            }
            className="inline-flex h-7 items-center rounded-md border px-2 text-xs hover:bg-accent"
          >
            + adicionar reclamante
          </button>
        </div>
        {state.reclamantes.map((d, i) => (
          <PartyRow
            key={`rec-${i}`}
            draft={d}
            rolePrefix={`Reclamante ${i + 1}`}
            showRemove={state.reclamantes.length > 1}
            onChange={(next) =>
              setState((s) => ({ ...s, reclamantes: updateAt(s.reclamantes, i, next) }))
            }
            onRemove={() =>
              setState((s) => ({ ...s, reclamantes: removeAt(s.reclamantes, i) }))
            }
          />
        ))}
      </section>

      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium">Reclamadas</h3>
          <button
            type="button"
            onClick={() =>
              setState((s) => ({
                ...s,
                reclamadas: [...s.reclamadas, makeDraft("reclamada")],
              }))
            }
            className="inline-flex h-7 items-center rounded-md border px-2 text-xs hover:bg-accent"
          >
            + adicionar reclamada
          </button>
        </div>
        {state.reclamadas.map((d, i) => (
          <PartyRow
            key={`rd-${i}`}
            draft={d}
            rolePrefix={`Reclamada ${i + 1}`}
            showRemove={state.reclamadas.length > 1}
            onChange={(next) =>
              setState((s) => ({ ...s, reclamadas: updateAt(s.reclamadas, i, next) }))
            }
            onRemove={() =>
              setState((s) => ({ ...s, reclamadas: removeAt(s.reclamadas, i) }))
            }
          />
        ))}
      </section>

      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium">Ministério Público (opcional)</h3>
          {!state.mpt ? (
            <button
              type="button"
              onClick={() =>
                setState((s) => ({
                  ...s,
                  mpt: makeDraft("ministerio_publico", "Ministério Público do Trabalho"),
                }))
              }
              className="inline-flex h-7 items-center rounded-md border px-2 text-xs hover:bg-accent"
            >
              + adicionar MPT
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setState((s) => ({ ...s, mpt: null }))}
              className="inline-flex h-7 items-center rounded-md border px-2 text-xs hover:bg-accent"
            >
              remover MPT
            </button>
          )}
        </div>
        {state.mpt && (
          <div className="rounded border bg-muted/20 p-3 space-y-1">
            <label className="text-xs text-muted-foreground">
              Designação ({ROLE_LABEL.ministerio_publico} — não entra na substituição)
            </label>
            <input
              className={inputClass}
              value={state.mpt.name}
              onChange={(e) =>
                setState((s) => ({
                  ...s,
                  mpt: s.mpt ? { ...s.mpt, name: e.target.value } : null,
                }))
              }
              placeholder="Ministério Público do Trabalho"
            />
          </div>
        )}
      </section>
    </div>
  );
}
