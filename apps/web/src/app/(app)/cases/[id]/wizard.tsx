"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useTransition } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  FileSearch,
  FileText,
  Sparkles,
  Users,
  type LucideIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalysisDossie, Case, Party, StructuredPiece } from "@/lib/cases";
import type { DespachoBlueprint } from "@/lib/cases";
import { cn } from "@/lib/utils";

import { AnalyzeButton } from "./analyze-button";
import { AnonymizedPreviewButton } from "./anonymized-preview";
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
  canLearn: boolean;
}

interface StepDef {
  key: StepKey;
  label: string;
  description: string;
  icon: LucideIcon;
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
    label: "Partes",
    description: "Cadastre Reclamante, Reclamada e demais partes do processo.",
    icon: Users,
    unlocked: () => true,
    complete: (c) => c.parties.length > 0,
  },
  {
    key: "pieces",
    label: "Peças",
    description: "Despacho de admissibilidade e recursos analisados.",
    icon: FileText,
    unlocked: (c) => c.parties.length > 0,
    complete: (c) => c.pieces.length > 0 && c.hasDespacho,
  },
  {
    key: "analysis",
    label: "Análise",
    description: "Dossiê temático anonimizado, com permissivos e divergências.",
    icon: FileSearch,
    unlocked: (c) => c.pieces.length > 0 && c.hasDespacho,
    complete: (c) => Boolean(c.dossie),
  },
  {
    key: "minuta",
    label: "Minuta",
    description: "Editor da minuta, com modelos sugeridos por tema.",
    icon: Sparkles,
    unlocked: (c) => Boolean(c.dossie),
    complete: (c) => Boolean(c.minutaMd && c.minutaMd.trim()),
  },
];

function pickInitialStep(ctx: Ctx, fromUrl: StepKey | null): StepKey {
  if (fromUrl && STEPS.find((s) => s.key === fromUrl)?.unlocked(ctx)) return fromUrl;
  for (const s of STEPS) {
    if (!s.complete(ctx)) return s.unlocked(ctx) ? s.key : "parties";
  }
  return "minuta";
}

export function CaseWizard({
  caseId,
  caseData,
  pieces,
  blueprint,
  canLearn,
}: Props) {
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
  const currentIdx = STEPS.findIndex((s) => s.key === current);
  const currentStep = STEPS[currentIdx];

  const goTo = (key: StepKey) => {
    const params = new URLSearchParams(search.toString());
    params.set("step", key);
    startTransition(() => {
      router.push(`?${params.toString()}`, { scroll: false });
    });
  };

  return (
    <div className="space-y-8">
      {/* Stepper */}
      <ol className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {STEPS.map((s, i) => {
          const isCurrent = s.key === current;
          const isComplete = s.complete(ctx);
          const isUnlocked = s.unlocked(ctx);
          const Icon = s.icon;
          return (
            <li key={s.key}>
              <button
                type="button"
                disabled={!isUnlocked && !isCurrent}
                onClick={() => goTo(s.key)}
                className={cn(
                  "group relative w-full overflow-hidden rounded-xl border bg-card p-4 text-left transition-all",
                  isCurrent && "border-primary shadow-sm",
                  !isCurrent && isUnlocked && "hover:border-foreground/30",
                  !isUnlocked && !isCurrent && "cursor-not-allowed opacity-50",
                )}
              >
                <div className="flex items-center gap-3">
                  <span
                    className={cn(
                      "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold transition-colors",
                      isComplete
                        ? "bg-success text-success-foreground"
                        : isCurrent
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground",
                    )}
                  >
                    {isComplete ? <Check className="h-4 w-4" /> : i + 1}
                  </span>
                  <div className="min-w-0">
                    <p className="font-serif text-sm font-semibold leading-tight">
                      {s.label}
                    </p>
                    <p className="mt-0.5 hidden text-[11px] text-muted-foreground sm:block">
                      {s.description.length > 38
                        ? s.description.slice(0, 35) + "…"
                        : s.description}
                    </p>
                  </div>
                </div>
                {isCurrent && (
                  <Icon className="absolute -bottom-2 -right-2 h-16 w-16 text-primary/5" />
                )}
              </button>
            </li>
          );
        })}
      </ol>

      {/* Current step content */}
      <Card>
        <CardHeader className="border-b">
          <div className="flex items-center gap-3">
            {currentStep && <currentStep.icon className="h-5 w-5 text-primary" />}
            <CardTitle className="text-xl">{currentStep?.label}</CardTitle>
          </div>
          <CardDescription>{currentStep?.description}</CardDescription>
        </CardHeader>
        <CardContent className="pt-6">
          {current === "parties" && (
            <PartiesPanel caseId={caseId} parties={caseData.parties} />
          )}
          {current === "pieces" && (
            <PiecesPanel caseId={caseId} pieces={pieces} blueprint={blueprint} />
          )}
          {current === "analysis" && (
            <AnalysisStep caseData={caseData} caseId={caseId} />
          )}
          {current === "minuta" && (
            <MinutaEditor
              caseId={caseId}
              initial={caseData.minuta_md ?? ""}
              hasMinuta={caseData.has_minuta}
              hasDocx={caseData.has_docx}
              canLearn={canLearn}
            />
          )}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          disabled={currentIdx <= 0}
          onClick={() => goTo(STEPS[currentIdx - 1].key)}
        >
          <ArrowLeft className="h-4 w-4" />
          Anterior
        </Button>
        <Button
          disabled={
            currentIdx >= STEPS.length - 1 ||
            !STEPS[currentIdx + 1]?.unlocked(ctx)
          }
          onClick={() => goTo(STEPS[currentIdx + 1].key)}
        >
          Próximo
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function AnalysisStep({
  caseData,
  caseId,
}: {
  caseData: Case;
  caseId: string;
}) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-0.5">
          {caseData.analyzed_at && (
            <p className="text-xs text-muted-foreground">
              Última análise em{" "}
              {new Date(caseData.analyzed_at).toLocaleString("pt-BR")}
            </p>
          )}
          {caseData.status === "analyzing" && (
            <p className="animate-pulse text-sm font-medium text-warning">
              Examinando o processo… pode levar alguns minutos.
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <AnonymizedPreviewButton caseId={caseId} />
          <AnalyzeButton
          caseId={caseId}
          alreadyAnalyzed={
            Boolean(caseData.analyzed_at) || caseData.status === "ready"
          }
          inFlight={caseData.status === "analyzing"}
          lastError={caseData.last_error}
        />
        </div>
      </div>
      {caseData.analysis_dossie ? (
        <DossiePanel dossie={caseData.analysis_dossie} />
      ) : caseData.analysis_result ? (
        <pre className="whitespace-pre-wrap rounded-md border bg-muted/30 p-4 text-sm">
          {caseData.analysis_result}
        </pre>
      ) : (
        <div className="rounded-lg border border-dashed bg-muted/30 p-8 text-center">
          <p className="text-sm text-muted-foreground">
            Ainda sem análise. Clique em <strong>Analisar</strong> acima quando
            as peças estiverem completas.
          </p>
        </div>
      )}
    </div>
  );
}
