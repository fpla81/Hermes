/**
 * Renderiza a minuta em markdown com marcadores `[[CORPO]]` /
 * `[[TRANSCRICAO*]]` / `[[EMENTA]]` / `[[NOTA]]` / `[[ALERTA_VERMELHO]]`
 * como HTML estilizado, espelhando aproximadamente a aparência do DOCX
 * final.
 *
 * Cada linha não-vazia entre marcadores vira um <p> com a classe
 * apropriada. Linhas vazias são separadores de parágrafo dentro do mesmo
 * bloco.
 */

export interface MinutaBlock {
  style: BlockStyle;
  paragraphs: string[];
}

export type BlockStyle =
  | "corpo"
  | "transcricao"
  | "ementa"
  | "nota"
  | "alerta";

const MARKER_TO_STYLE: Record<string, BlockStyle> = {
  "[[CORPO]]": "corpo",
  "[[TRANSCRICAO1]]": "transcricao",
  "[[TRANSCRICAO2]]": "transcricao",
  "[[TRANSCRICAO3]]": "transcricao",
  "[[EMENTA]]": "ementa",
  "[[NOTA]]": "nota",
  "[[ALERTA_VERMELHO]]": "alerta",
};

export function parseMinuta(text: string): MinutaBlock[] {
  const blocks: MinutaBlock[] = [];
  let current: MinutaBlock = { style: "corpo", paragraphs: [] };
  const lines = (text ?? "").split(/\r?\n/);
  for (const raw of lines) {
    const line = raw.replace(/\s+$/, "");
    const trimmed = line.trim();
    if (MARKER_TO_STYLE[trimmed]) {
      if (current.paragraphs.length > 0) blocks.push(current);
      current = { style: MARKER_TO_STYLE[trimmed], paragraphs: [] };
      continue;
    }
    if (!trimmed) continue;
    current.paragraphs.push(trimmed);
  }
  if (current.paragraphs.length > 0) blocks.push(current);
  return blocks;
}

/**
 * Estiliza inline:
 *  - `***texto***` → bold+italic
 *  - `**texto**` → bold
 *  - `*texto*` → italic
 * Mantém o resto literal. Escape básico de HTML.
 */
function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function inlineMarkdown(s: string): string {
  let out = escapeHtml(s);
  out = out.replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>");
  out = out.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  out = out.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>");
  return out;
}

function isHeading(text: string): boolean {
  if (text.startsWith("TEMA ") || text.startsWith("TEMA-")) return true;
  if (text === text.toUpperCase() && text.length > 8 && /^[A-ZÀ-Ý0-9 \-,()/.ºª§]+$/.test(text)) {
    return true;
  }
  if (text.toUpperCase() === "DISPOSITIVO") return true;
  return false;
}

const STYLE_CLASS: Record<BlockStyle, string> = {
  corpo:
    "text-justify text-sm leading-relaxed",
  transcricao:
    "ml-8 mr-4 text-justify text-[0.8125rem] leading-relaxed text-muted-foreground border-l-2 border-muted pl-3",
  ementa:
    "ml-12 text-justify text-sm italic leading-snug text-muted-foreground",
  nota:
    "text-[0.75rem] text-muted-foreground",
  alerta:
    "rounded border border-destructive/40 bg-destructive/10 p-2 text-sm text-destructive",
};

/** Devolve HTML string segura para inserir em `dangerouslySetInnerHTML`. */
export function renderMinutaHtml(text: string): string {
  const blocks = parseMinuta(text);
  if (blocks.length === 0) {
    return '<p class="text-sm text-muted-foreground">Sem conteúdo.</p>';
  }
  const parts: string[] = [];
  for (const block of blocks) {
    for (const para of block.paragraphs) {
      const klass = STYLE_CLASS[block.style];
      if (block.style === "corpo" && isHeading(para)) {
        parts.push(
          `<p class="${klass} font-semibold uppercase tracking-wide">${escapeHtml(para)}</p>`,
        );
      } else {
        parts.push(`<p class="${klass}">${inlineMarkdown(para)}</p>`);
      }
    }
  }
  return parts.join("\n");
}
