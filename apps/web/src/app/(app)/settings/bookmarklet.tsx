"use client";

import Link from "next/link";
import { useState } from "react";

interface Props {
  webBaseUrl: string;
}

function buildClipboardSnippet(webBase: string): string {
  return `(function(){
  var rx=/\\d{1,7}-\\d{2}\\.\\d{4}\\.\\d\\.\\d{2}\\.\\d{4}/;
  var n=(location.pathname.match(rx)||document.body.innerText.match(rx)||[])[0];
  if(!n){alert('Não achei o número do processo na página');return;}
  var payload={numero_processo:n,html:document.documentElement.outerHTML,url:location.href};
  var text=JSON.stringify(payload);
  navigator.clipboard.writeText(text).then(function(){
    alert('Copiado! Cole em ${webBase}/cases/import');
  }).catch(function(e){
    // fallback: cria textarea, seleciona e copia
    var ta=document.createElement('textarea');
    ta.value=text;document.body.appendChild(ta);ta.select();
    document.execCommand('copy');document.body.removeChild(ta);
    alert('Copiado! Cole em ${webBase}/cases/import');
  });
})();`;
}

export function BookmarkletPanel({ webBaseUrl }: Props) {
  const snippet = buildClipboardSnippet(webBaseUrl);
  const [copied, setCopied] = useState(false);

  async function copySnippet() {
    await navigator.clipboard.writeText(snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="space-y-3 rounded-md border p-4">
      <h2 className="text-sm font-medium">Importar peças do Bem-te-vi</h2>
      <p className="text-xs text-muted-foreground">
        Como o Bem-te-vi roda em HTTPS e o Hermes (em dev) em HTTP, o browser
        bloqueia chamadas diretas. O fluxo abaixo usa a área de transferência
        para evitar isso.
      </p>
      <ol className="ml-4 list-decimal space-y-1 text-xs text-muted-foreground">
        <li>
          Clique no botão abaixo para copiar o &quot;snippet de coleta&quot;.
        </li>
        <li>
          Abra a página &quot;Peças&quot; do processo no Bem-te-vi. Tecla{" "}
          <kbd>⌘+Option+I</kbd> (ou <kbd>F12</kbd>), aba <strong>Console</strong>.
        </li>
        <li>Cole o snippet no Console e tecla Enter.</li>
        <li>
          O snippet copia o HTML + número do processo para a área de
          transferência e mostra um alerta.
        </li>
        <li>
          Volte ao Hermes em <Link href="/cases/import" className="underline">/cases/import</Link>{" "}
          e cole o conteúdo.
        </li>
      </ol>
      <button
        type="button"
        onClick={copySnippet}
        className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90"
      >
        {copied ? "Copiado!" : "Copiar snippet de coleta"}
      </button>
      <details className="text-xs">
        <summary className="cursor-pointer text-muted-foreground">Ver código</summary>
        <pre className="mt-2 overflow-auto rounded-md border bg-muted/30 p-2 font-mono text-[10px]">
          {snippet}
        </pre>
      </details>
    </div>
  );
}
