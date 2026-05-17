"use client";

import { useActionState, useState } from "react";
import {
  Code2,
  Download,
  Eye,
  FileDown,
  GraduationCap,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";

import {
  generateMinutaDraftAction,
  learnFundamentosAction,
  saveMinutaAction,
  triggerDocxAction,
  type LearnState,
  type MinutaDraftState,
  type SaveMinutaState,
} from "../actions";
import { MinutaTiptap } from "./minuta-tiptap";

const INITIAL_DRAFT: MinutaDraftState = {};
const INITIAL_SAVE: SaveMinutaState = {};

interface Props {
  caseId: string;
  initial: string;
  hasMinuta: boolean;
  hasDocx: boolean;
  canLearn: boolean;
}

export function MinutaEditor({
  caseId,
  initial,
  hasMinuta,
  hasDocx,
  canLearn,
}: Props) {
  const [text, setText] = useState(initial);
  const [draftState, draftFormAction, draftPending] = useActionState(
    generateMinutaDraftAction,
    INITIAL_DRAFT,
  );
  const [saveState, saveFormAction, savePending] = useActionState(
    saveMinutaAction,
    INITIAL_SAVE,
  );
  const [learnState, learnFormAction, learning] = useActionState(
    learnFundamentosAction,
    {} as LearnState,
  );
  const [showRaw, setShowRaw] = useState(false);

  if (draftState.text && draftState.text !== text && !text.trim()) {
    setText(draftState.text);
  }

  const learnMsg = learnState.ok
    ? learnState.learned && learnState.learned > 0
      ? `${learnState.learned} fundamentação${learnState.learned > 1 ? "ões" : ""} guardada${learnState.learned > 1 ? "s" : ""} na base.`
      : "Nenhuma fundamentação extraída — verifique se a minuta está salva e bate com o dossiê."
    : null;

  return (
    <div className="space-y-5">
      {/* Toolbar superior — gerar, exportar, aprender */}
      <div className="flex flex-wrap items-center gap-2">
        <form action={draftFormAction}>
          <input type="hidden" name="id" value={caseId} />
          <Button type="submit" disabled={draftPending} variant="outline">
            <Sparkles className="h-4 w-4" />
            {draftPending ? "Gerando…" : "Gerar rascunho"}
          </Button>
        </form>
        {draftState.text && !draftState.error && (
          <Button
            type="button"
            variant="link"
            size="sm"
            onClick={() => setText(draftState.text!)}
          >
            Usar rascunho gerado
          </Button>
        )}
        {draftState.error && (
          <span className="text-xs text-destructive">{draftState.error}</span>
        )}

        <Separator orientation="vertical" className="h-6" />

        <form action={triggerDocxAction}>
          <input type="hidden" name="id" value={caseId} />
          <Button type="submit" disabled={!hasMinuta} variant="outline">
            <FileDown className="h-4 w-4" />
            {hasDocx ? "Regerar DOCX" : "Gerar DOCX"}
          </Button>
        </form>

        {hasDocx && (
          <Button asChild>
            <a href={`/cases/${caseId}/docx`}>
              <Download className="h-4 w-4" />
              Baixar DOCX
            </a>
          </Button>
        )}

        {canLearn && (
          <form action={learnFormAction} className="ml-auto">
            <input type="hidden" name="case_id" value={caseId} />
            <Button
              type="submit"
              disabled={!hasMinuta || learning}
              variant="success"
              title={
                hasMinuta
                  ? "Extrai as fundamentações da minuta e salva na base do gabinete"
                  : "Salve a minuta primeiro"
              }
            >
              <GraduationCap className="h-4 w-4" />
              {learning ? "Aprendendo…" : "Aprender fundamentação"}
            </Button>
          </form>
        )}
      </div>

      {learnMsg && (
        <p className="rounded-md border border-success/30 bg-success/10 px-3 py-2 text-xs text-success">
          {learnMsg}
        </p>
      )}
      {learnState.error && (
        <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {learnState.error}
        </p>
      )}

      <form action={saveFormAction} className="space-y-4">
        <input type="hidden" name="id" value={caseId} />
        <input type="hidden" name="text" value={text} />

        <div className="flex items-center justify-end">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setShowRaw((v) => !v)}
            className="text-muted-foreground"
          >
            {showRaw ? (
              <>
                <Eye className="h-3.5 w-3.5" />
                Voltar ao editor visual
              </>
            ) : (
              <>
                <Code2 className="h-3.5 w-3.5" />
                Ver código markdown
              </>
            )}
          </Button>
        </div>

        {showRaw ? (
          <Textarea
            rows={28}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="[[CORPO]]&#10;PROCESSO Nº ..."
            spellCheck={false}
            className="font-mono text-xs leading-relaxed"
          />
        ) : (
          <MinutaTiptap value={text} onChange={setText} />
        )}

        <div className="flex items-center gap-3">
          <Button
            type="submit"
            disabled={savePending || !text.trim()}
            size="lg"
          >
            {savePending ? "Salvando…" : "Salvar minuta"}
          </Button>
          {saveState.ok && (
            <span className="text-xs text-success">Salvo com sucesso.</span>
          )}
          {saveState.error && (
            <span className="text-xs text-destructive">{saveState.error}</span>
          )}
        </div>
      </form>
    </div>
  );
}
