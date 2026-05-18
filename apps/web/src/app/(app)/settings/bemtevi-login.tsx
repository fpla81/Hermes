"use client";

import { useActionState } from "react";

import {
  cancelLoginAction,
  completeLoginAction,
  startLoginAction,
  type CompleteLoginState,
  type StartLoginState,
} from "./actions";

const INITIAL_START: StartLoginState = {};
const INITIAL_COMPLETE: CompleteLoginState = {};

export function BemTeViLoginPanel({
  activeSessionId,
}: {
  activeSessionId: string | null;
}) {
  const [startState, startFormAction, startPending] = useActionState(
    startLoginAction,
    INITIAL_START,
  );
  const [completeState, completeFormAction, completePending] = useActionState(
    completeLoginAction,
    INITIAL_COMPLETE,
  );

  const sessionId = startState.session?.session_id ?? activeSessionId;
  const hasOpenSession = Boolean(sessionId) && !completeState.ok;

  return (
    <div className="space-y-3 rounded-md border p-4">
      <h2 className="text-sm font-medium">Sessão Bem-te-vi</h2>
      <p className="text-xs text-muted-foreground">
        Clique em &quot;Iniciar login&quot;. O Chrome abre na máquina onde o
        serviço Playwright está rodando. Faça o login normal e clique em
        &quot;Concluí o login&quot; abaixo para salvar o cookie no profile.
      </p>

      {!hasOpenSession && (
        <form action={startFormAction}>
          <button
            type="submit"
            disabled={startPending}
            className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {startPending ? "Abrindo Chrome…" : "Iniciar login"}
          </button>
          {startState.error && (
            <p className="mt-2 text-sm text-destructive">{startState.error}</p>
          )}
          {completeState.ok && (
            <p className="mt-2 text-sm text-emerald-600">
              Cookie salvo. Pode capturar processos.
            </p>
          )}
        </form>
      )}

      {hasOpenSession && sessionId && (
        <div className="space-y-2">
          <p className="text-sm">
            Chrome aberto.{" "}
            {startState.session?.reused
              ? "Já havia uma sessão em andamento — use a janela aberta."
              : "Faça o login na janela que abriu."}
          </p>
          <p className="text-xs text-muted-foreground">
            Profile: {startState.session?.profile_dir ?? "(em uso)"}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <form action={completeFormAction}>
              <input type="hidden" name="session_id" value={sessionId} />
              <button
                type="submit"
                disabled={completePending}
                className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {completePending ? "Salvando…" : "Concluí o login"}
              </button>
            </form>
            <form action={cancelLoginAction}>
              <input type="hidden" name="session_id" value={sessionId} />
              <button
                type="submit"
                className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm font-medium hover:bg-accent"
              >
                Cancelar
              </button>
            </form>
          </div>
          {completeState.error && (
            <p className="text-sm text-destructive">{completeState.error}</p>
          )}
        </div>
      )}
    </div>
  );
}
