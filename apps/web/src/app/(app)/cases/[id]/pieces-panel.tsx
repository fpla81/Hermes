"use client";

import { useActionState, useState } from "react";

import type { StructuredPiece } from "@/lib/cases";

import { addPieceAction, deletePieceAction, type AddPieceState } from "../actions";

const INITIAL: AddPieceState = {};

const TIPO_LABEL: Record<string, string> = {
  despacho_admissibilidade: "Despacho de Admissibilidade",
  recurso_revista: "Recurso de Revista",
  agravo_instrumento: "Agravo de Instrumento",
  agravo_interno: "Agravo Interno",
};

const PARTE_LABEL: Record<string, string> = {
  reclamante: "Reclamante",
  reclamada: "Reclamada",
  reclamantes: "Reclamantes",
  reclamadas: "Reclamadas",
  ministerio_publico: "Ministério Público",
  outro: "Outro",
};

function PieceCard({ caseId, piece }: { caseId: string; piece: StructuredPiece }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <li className="space-y-2 rounded-md border bg-muted/20 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm">
          <span className="font-medium">{TIPO_LABEL[piece.tipo] ?? piece.tipo}</span>
          {piece.parte && (
            <span className="ml-2 text-muted-foreground">
              · {PARTE_LABEL[piece.parte] ?? piece.parte}
            </span>
          )}
          {piece.data && <span className="ml-2 text-muted-foreground">· {piece.data}</span>}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="text-xs underline text-muted-foreground"
          >
            {expanded ? "ocultar texto" : "ver texto"}
          </button>
          <form action={deletePieceAction}>
            <input type="hidden" name="case_id" value={caseId} />
            <input type="hidden" name="piece_id" value={piece.id} />
            <button type="submit" className="text-xs text-destructive hover:underline">
              remover
            </button>
          </form>
        </div>
      </div>
      {expanded && (
        <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded border bg-background p-2 font-mono text-xs">
          {piece.text}
        </pre>
      )}
      {piece.blueprint && (
        <div className="rounded border border-emerald-500/40 bg-emerald-500/5 p-2 text-xs">
          <strong>Blueprint extraído do despacho:</strong>
          {piece.blueprint.note && (
            <p className="text-muted-foreground">{piece.blueprint.note}</p>
          )}
          {piece.blueprint.recursos.length > 0 ? (
            <ul className="mt-1 list-disc pl-4">
              {piece.blueprint.recursos.map((r, i) => (
                <li key={i}>
                  {TIPO_LABEL[r.tipo] ?? r.tipo} · {PARTE_LABEL[r.parte] ?? r.parte} ·{" "}
                  {r.conclusao}: {r.temas.join("; ") || "—"}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-muted-foreground">Nenhum recurso identificado.</p>
          )}
        </div>
      )}
    </li>
  );
}

function AddPieceForm({ caseId }: { caseId: string }) {
  const [state, formAction, pending] = useActionState(addPieceAction, INITIAL);
  const [tipo, setTipo] = useState<string>("recurso_revista");
  const requiresParte = tipo !== "despacho_admissibilidade";

  return (
    <form action={formAction} className="space-y-3 rounded-md border p-3">
      <input type="hidden" name="case_id" value={caseId} />
      <div className="grid gap-2 sm:grid-cols-3">
        <label className="space-y-1">
          <span className="text-xs text-muted-foreground">Tipo</span>
          <select
            name="tipo"
            value={tipo}
            onChange={(e) => setTipo(e.target.value)}
            className="block w-full rounded-md border bg-background px-2 py-1 text-sm"
          >
            <option value="despacho_admissibilidade">Despacho de Admissibilidade</option>
            <option value="recurso_revista">Recurso de Revista</option>
            <option value="agravo_instrumento">Agravo de Instrumento</option>
            <option value="agravo_interno">Agravo Interno</option>
          </select>
        </label>
        {requiresParte && (
          <label className="space-y-1">
            <span className="text-xs text-muted-foreground">Parte recorrente</span>
            <select
              name="parte"
              defaultValue=""
              className="block w-full rounded-md border bg-background px-2 py-1 text-sm"
              required
            >
              <option value="" disabled>
                Selecione…
              </option>
              <option value="reclamante">Reclamante</option>
              <option value="reclamada">Reclamada</option>
              <option value="reclamantes">Reclamantes</option>
              <option value="reclamadas">Reclamadas</option>
              <option value="ministerio_publico">Ministério Público</option>
              <option value="outro">Outro</option>
            </select>
          </label>
        )}
        <label className="space-y-1">
          <span className="text-xs text-muted-foreground">Data (opcional)</span>
          <input
            type="text"
            name="data"
            placeholder="dd/mm/aaaa"
            className="block w-full rounded-md border bg-background px-2 py-1 text-sm"
          />
        </label>
      </div>
      <label className="block space-y-1">
        <span className="text-xs text-muted-foreground">Texto da peça</span>
        <textarea
          name="text"
          rows={8}
          required
          placeholder="Cole aqui o texto integral (anonimizado) da peça."
          className="w-full rounded-md border bg-background p-2 font-mono text-xs"
        />
      </label>
      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={pending}
          className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {pending ? "Adicionando…" : "Adicionar peça"}
        </button>
        {state.error && <span className="text-sm text-destructive">{state.error}</span>}
        {state.ok && <span className="text-sm text-emerald-600">Peça adicionada.</span>}
      </div>
    </form>
  );
}

function BlueprintChecklist({
  blueprint,
  pieces,
}: {
  blueprint: { recursos: { tipo: string; parte: string; temas: string[]; conclusao: string }[]; note?: string };
  pieces: StructuredPiece[];
}) {
  if (!blueprint.recursos.length) {
    return (
      <p className="text-xs text-muted-foreground">
        {blueprint.note ?? "Nenhum recurso esperado identificado no despacho."}
      </p>
    );
  }
  // matching simples: tipo + parte
  const present = (tipo: string, parte: string) =>
    pieces.some((p) => p.tipo === tipo && p.parte === parte);

  return (
    <ul className="space-y-1 text-sm">
      {blueprint.recursos.map((r, i) => {
        const ok = present(r.tipo, r.parte);
        return (
          <li key={i} className="flex items-center gap-2">
            <span className={ok ? "text-emerald-600" : "text-muted-foreground"}>
              {ok ? "✓" : "○"}
            </span>
            <span>
              {TIPO_LABEL[r.tipo] ?? r.tipo} · {PARTE_LABEL[r.parte] ?? r.parte} ·{" "}
              {r.conclusao}: {r.temas.join("; ") || "—"}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export function PiecesPanel({
  caseId,
  pieces,
  blueprint,
}: {
  caseId: string;
  pieces: StructuredPiece[];
  blueprint: { recursos: { tipo: string; parte: string; temas: string[]; conclusao: string }[]; note?: string } | null;
}) {
  return (
    <section className="space-y-4 rounded-md border p-4">
      <header className="space-y-1">
        <h2 className="text-sm font-medium">Peças do processo</h2>
        <p className="text-xs text-muted-foreground">
          Adicione cada peça (Despacho de Admissibilidade, RRs, Agravos) com seu
          texto. Ao adicionar o despacho, o sistema extrai automaticamente o
          blueprint dos recursos esperados.
        </p>
      </header>

      {pieces.length > 0 && (
        <ul className="space-y-2">
          {pieces.map((p) => (
            <PieceCard key={p.id} caseId={caseId} piece={p} />
          ))}
        </ul>
      )}

      <AddPieceForm caseId={caseId} />

      {blueprint && (
        <div className="space-y-2 rounded-md border border-emerald-500/40 bg-emerald-500/5 p-3">
          <h3 className="text-sm font-medium">Recursos esperados (do despacho)</h3>
          <BlueprintChecklist blueprint={blueprint} pieces={pieces} />
        </div>
      )}
    </section>
  );
}
