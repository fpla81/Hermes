"use client";

import { useState } from "react";

interface Props {
  token: string;
  apiBaseUrl: string;
  webBaseUrl: string;
}

function buildBookmarkletCode(token: string, apiBase: string, webBase: string): string {
  // O bookmarklet roda na página do Bem-te-vi. Captura o HTML inteiro, tenta
  // descobrir o número CNJ via URL ou texto, e POSTa pra API.
  const body = `(function(){
  var T='${token}';
  var API='${apiBase}';
  var WEB='${webBase}';
  var rx=/\\d{1,7}-\\d{2}\\.\\d{4}\\.\\d\\.\\d{2}\\.\\d{4}/;
  var n=(location.pathname.match(rx)||document.body.innerText.match(rx)||[])[0];
  if(!n){alert('N\\u00e3o achei o n\\u00famero do processo na p\\u00e1gina');return;}
  fetch(API+'/cases/ingest',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+T},body:JSON.stringify({numero_processo:n,html:document.documentElement.outerHTML,url:location.href})})
    .then(function(r){return r.json().then(function(j){return{ok:r.ok,j:j}})})
    .then(function(x){if(x.ok){window.open(WEB+'/cases/'+x.j.case_id,'_blank')}else{alert('Erro: '+JSON.stringify(x.j))}})
    .catch(function(e){alert('Falha: '+e.message)});
})();`;
  // remove quebras de linha e espaços extras pra caber numa URL javascript:
  const compact = body.replace(/\s*\n\s*/g, "").replace(/\s{2,}/g, " ");
  return `javascript:${encodeURIComponent(compact)}`;
}

export function BookmarkletPanel({ token, apiBaseUrl, webBaseUrl }: Props) {
  const code = buildBookmarkletCode(token, apiBaseUrl, webBaseUrl);
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="space-y-3 rounded-md border p-4">
      <h2 className="text-sm font-medium">Bookmarklet de captura</h2>
      <p className="text-xs text-muted-foreground">
        Arraste o botão abaixo para a barra de favoritos do seu Chrome. Quando
        estiver na página &quot;Peças&quot; do Bem-te-vi, clique no favorito
        para enviar o conteúdo para o Hermes.
      </p>

      <div className="flex flex-wrap items-center gap-2">
        <a
          href={code}
          // eslint-disable-next-line react/jsx-no-target-blank
          className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          onClick={(e) => e.preventDefault()}
          draggable
        >
          Enviar pro Hermes
        </a>
        <button
          type="button"
          onClick={copy}
          className="inline-flex h-9 items-center rounded-md border bg-background px-3 text-sm font-medium hover:bg-accent"
        >
          {copied ? "Copiado!" : "Copiar código"}
        </button>
      </div>

      <details className="text-xs">
        <summary className="cursor-pointer text-muted-foreground">
          Ver código (debug)
        </summary>
        <pre className="mt-2 overflow-auto rounded-md border bg-muted/30 p-2 font-mono text-[10px]">
          {decodeURIComponent(code.replace("javascript:", ""))}
        </pre>
      </details>

      <p className="text-xs text-muted-foreground">
        O token é pessoal e fica embutido no bookmarklet. Para revogá-lo,
        troque <code>HERMES_INTERNAL_SECRET</code> no servidor.
      </p>
    </div>
  );
}
