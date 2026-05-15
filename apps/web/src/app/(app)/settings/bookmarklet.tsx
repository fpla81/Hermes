"use client";

import { useState } from "react";

interface Props {
  token: string;
  apiBaseUrl: string;
  webBaseUrl: string;
}

function buildConsoleSnippet(token: string, apiBase: string, webBase: string): string {
  return `(function(){
  var T='${token}';
  var API='${apiBase}';
  var WEB='${webBase}';
  var rx=/\\d{1,7}-\\d{2}\\.\\d{4}\\.\\d\\.\\d{2}\\.\\d{4}/;
  var n=(location.pathname.match(rx)||document.body.innerText.match(rx)||[])[0];
  if(!n){alert('Não achei o número do processo na página');return;}
  fetch(API+'/cases/ingest',{
    method:'POST',
    headers:{'Content-Type':'application/json','Authorization':'Bearer '+T},
    body:JSON.stringify({numero_processo:n,html:document.documentElement.outerHTML,url:location.href}),
  })
    .then(function(r){return r.json().then(function(j){return{ok:r.ok,j:j}})})
    .then(function(x){
      if(x.ok){window.open(WEB+'/cases/'+x.j.case_id,'_blank')}
      else{alert('Erro: '+JSON.stringify(x.j))}
    })
    .catch(function(e){alert('Falha: '+e.message)});
})();`;
}

function buildBookmarkletUrl(snippet: string): string {
  const compact = snippet.replace(/\s*\n\s*/g, "").replace(/\s{2,}/g, " ");
  return `javascript:${encodeURIComponent(compact)}`;
}

export function BookmarkletPanel({ token, apiBaseUrl, webBaseUrl }: Props) {
  const snippet = buildConsoleSnippet(token, apiBaseUrl, webBaseUrl);
  const bookmarkletUrl = buildBookmarkletUrl(snippet);
  const [copiedSnippet, setCopiedSnippet] = useState(false);
  const [copiedBookmarklet, setCopiedBookmarklet] = useState(false);

  async function copySnippet() {
    await navigator.clipboard.writeText(snippet);
    setCopiedSnippet(true);
    setTimeout(() => setCopiedSnippet(false), 2000);
  }

  async function copyBookmarklet() {
    await navigator.clipboard.writeText(bookmarkletUrl);
    setCopiedBookmarklet(true);
    setTimeout(() => setCopiedBookmarklet(false), 2000);
  }

  return (
    <div className="space-y-6">
      <div className="space-y-3 rounded-md border p-4">
        <h2 className="text-sm font-medium">Console snippet (recomendado pro Bem-te-vi)</h2>
        <p className="text-xs text-muted-foreground">
          A página do Bem-te-vi é React, que bloqueia <code>javascript:</code> URLs por
          segurança. Use o snippet abaixo no DevTools Console:
        </p>
        <ol className="ml-4 list-decimal space-y-1 text-xs text-muted-foreground">
          <li>Abre a página &quot;Peças&quot; do processo no Bem-te-vi.</li>
          <li>
            Tecla <kbd>⌘+Option+I</kbd> (ou <kbd>F12</kbd>) → aba <strong>Console</strong>.
          </li>
          <li>Cola o código abaixo no console e tecla Enter.</li>
        </ol>
        <button
          type="button"
          onClick={copySnippet}
          className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          {copiedSnippet ? "Copiado!" : "Copiar snippet pro Console"}
        </button>
        <details className="text-xs">
          <summary className="cursor-pointer text-muted-foreground">Ver código</summary>
          <pre className="mt-2 overflow-auto rounded-md border bg-muted/30 p-2 font-mono text-[10px]">
            {snippet}
          </pre>
        </details>
      </div>

      <div className="space-y-3 rounded-md border p-4">
        <h2 className="text-sm font-medium">Bookmarklet (sites sem React/CSP estrito)</h2>
        <p className="text-xs text-muted-foreground">
          Para sites que aceitam <code>javascript:</code> URLs, você pode salvar como
          favorito. Não funciona no Bem-te-vi atual.
        </p>
        <button
          type="button"
          onClick={copyBookmarklet}
          className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm font-medium hover:bg-accent"
        >
          {copiedBookmarklet ? "Copiado!" : "Copiar bookmarklet URL"}
        </button>
      </div>

      <p className="text-xs text-muted-foreground">
        O token é pessoal e está embutido no código. Para revogá-lo, troque{" "}
        <code>HERMES_INTERNAL_SECRET</code> no servidor.
      </p>
    </div>
  );
}
