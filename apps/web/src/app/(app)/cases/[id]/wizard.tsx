"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useTransition } from "react";

import type { AnalysisDossie, Case, Party, StructuredPiece } from "@/lib/cases";
import type { DespachoBlueprint } from "@/lib/cases";

import { AnalyzeButton } from "./analyze-button";
import { DossiePanel } from "./dossie-panel";
import { MinutaEditor } from "./minuta-editor";
import { PartiesPanel } from "./parties-panel";
import { PiecesPanel } from "./pieces-panel";

type StepKey = "parties" | "pieces" | "analysis" | "minuta";

interface Props {
  caseId: string;
  caseData: Case;
  pieces: StructuredPiece[];
  blueprint: DespachoBlueprint | null;
}

interface StepDef {
  key: StepKey;
  label: string;
  short: string;
  unlocked: (ctx: Ctx) => boolean;
  complete: (ctx: Ctx) => boolean;
}

interface Ctx {
  parties: Party[];
  pieces: StructuredPiece[];
  hasDespacho: boolean;
  dossie: AnalysisDossie | null;
  minutaMd: string | null;
}

const STEPS: StepDef[] = [
  {
    key: "parties",
    label: "1. Partes",
    short: "Partes",
    unlocked: () => true,
    complete: (c) => c.parties.length > 0,
  },
  {
    key: "pieces",
    label: "2. Peças",
    short: "Peças",
    unlocked: (c) => c.parties.length > 0,
    complete: (c) => c.pieces.length > 0 && c.hasDespacho,
  },
  {
    key: "analysis",
    label: "3. Análise",
    short: "Análise",
    unlocked: (c) => c.pieces.length > 0 && c.hasDespacho,
    complete: (c) => Boolean(c.dossie),
  },
  {
    key: "minuta",
    label: "4. Minuta",
    short: "Minuta",
    unlocked: (c) => Boolean(c.dossie),
    complete: (c) => Boolean(c.minutaMd && c.minutaMd.trim()),
  },
];

function pickInitialStep(ctx: Ctx, fromUrl: StepKey | null): StepKey {
  if (fromUrl && STEPS.find((s) => s.key === fromUrl)?.unlocked(ctx)) return fromUrl;
  // primeira etapa não-completa
  for (const s of STEPS) {
    if (!s.complete(ctx)) return s.unlocked(ctx) ? s.key : "parties";
  }
  return "minuta";
}

export function CaseWizard({ caseId, caseData, pieces, blueprint }: Props) {
  const router = useRouter();
  const search = useSearchParams();
  const [, startTransition] = useTransition();

  const ctx: Ctx = useMemo(
    () => ({
      parties: caseData.parties ?? [],
      pieces,
      hasDespacho: pieces.some((p) => p.tipo === "despacho_admissibilidade"),
      dossie: caseData.analysis_dossie ?? null,
      minutaMd: caseData.minuta_md ?? null,
    }),
    [caseData, pieces],
  );

  const stepFromUrl = (search.get("step") as StepKey | null) ?? null;
  const current = pickInitialStep(ctx, stepFromUrl);

  const goTo = (key: StepKey) => {
    const params = new URLSearchParams(search.toString());
    params.set("step", key);
    startTransition(() => {
      router.push(`?${params.toString()}`, { scroll: false });
    });
  };

  const currentIdx = STEPS.findIndex((s) => s.key === current);

  return (
    <div className="space-y-6">
      <ol className="flex flex-wrap items-center gap-2">
        {STEPS.map((s, i) => {
          const isCurrent = s.key === current;
          const isComplete = s.complete(ctx);
          const isUnlocked = s.unlocked(ctx);
          return (
            <li key={s.key} className="flex items-center gap-2">
              <button
                type="button"
                disabled={!isUnlocked && !isCurrent}
                onClick={() => goTo(s.key)}
                className={[
                  "inline-flex h-9 items-center gap-2 rounded-md border px-3 text-sm transition",
                  isCurrent
                    ? "border-primary bg-primary text-primary-foreground"
                    : isComplete
                      ? "border-emerald-400/60 bg-emerald-50 text-emerald-900 hover:bg-emerald-100"
                      : isUnlocked
                        ? "bg-background hover:bg-accent"
                        : "cursor-not-allowed opacity-50",
                ].join(" ")}
              >
                <span
                  className={[
                    "flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold",
                    isCurrent
                      ? "bg-primary-foreground/20"
                      : isComplete
                        ? "bg-emerald-500 text-white"
                        : "bg-muted",
                  ].join(" ")}
                >
                  {isComplete ? "✓" : i + 1}
                </span>
                <span>{s.label}</span>
              </button>
              {i < STEPS.length - 1 && (
                <span className="text-muted-foreground">›</span>
              )}
            </li>
          );
        })}
      </ol>

      <div className="rounded-md border bg-background">
        {current === "parties" && (
          <div className="p-4">
            <PartiesPanel caseId={caseId} parties={caseData.parties} />
          </div>
        )}
        {current === "pieces" && (
          <div className="p-4">
            <PiecesPanel caseId={caseId} pieces={pieces} blueprint={blueprint} />
          </div>
        )}
        {current === "analysis" && (
          <section className="space-y-3 p-4">
            <header className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-sm font-medium">Análise jurídica</h2>
                <p className="text-xs text-muted-foreground">
                  Anonimiza as peças com as partes cadastradas e gera o dossiê
                  temático.
                </p>
              </div>
              <AnalyzeButton
                caseId={caseId}
                alreadyAnalyzed={
                  Boolean(caseData.analyzed_at) || caseData.status === "ready"
                }
                inFlight={caseData.status === "analyzing"}
                lastError={caseData.last_error}
              />
            </header>
            {caseData.status === "analyzing" && (
              <p className="animate-pulse text-sm text-amber-600">
                Examinando o processo… (pode levar alguns minutos)
              </p>
            )}
            {caseData.analyzed_at && (
              <p className="text-xs text-muted-foreground">
                Última análise:{" "}
                {new Date(caseData.analyzed_at).toLocaleString("pt-BR")}
              </p>
            )}
            {caseData.analysis_dossie ? (
              <DossiePanel dossie={caseData.analysis_dossie} />
            ) : caseData.analysis_result ? (
              <pre className="whitespace-pre-wrap rounded-md border bg-muted/30 p-3 text-sm">
                {caseData.analysis_result}
              </pre>
            ) : (
              <p className="text-sm text-muted-foreground">
                Ainda sem análise — clique em &quot;Analisar&quot;.
              </p>
            )}
          </section>
        )}
        {current === "minuta" && (
          <div className="p-4">
            <MinutaEditor
              caseId={caseId}
              initial={caseData.minuta_md ?? ""}
              hasMinuta={caseData.has_minuta}
              hasDocx={caseData.has_docx}
            />
          </div>
        )}
      </div>

      <div className="flex items-center justify-between">
        <button
          type="button"
          disabled={currentIdx <= 0}
          onClick={() => goTo(STEPS[currentIdx - 1].key)}
          className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm hover:bg-accent disabled:opacity-40"
        >
          ← Anterior
        </button>
        <button
          type="button"
          disabled={
            currentIdx >= STEPS.length - 1 ||
            !STEPS[currentIdx + 1]?.unlocked(ctx)
          }
          onClick={() => goTo(STEPS[currentIdx + 1].key)}
          className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-40"
        >
          Próximo →
        </button>
      </div>
    </div>
  );
}
