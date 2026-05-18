/**
 * Conversões entre o markdown da minuta (com marcadores
 * `[[CORPO]]` / `[[TRANSCRICAO*]]` / `[[EMENTA]]` / `[[NOTA]]` /
 * `[[ALERTA_VERMELHO]]`) e o JSON do Tiptap (ProseMirror schema).
 *
 * Estratégia de mapeamento de blocos:
 *  - [[CORPO]]            → paragraph
 *  - [[TRANSCRICAO*]]     → blockquote (preserva o nome exato no atributo
 *                            data-marker quando precisarmos voltar)
 *  - [[EMENTA]]           → paragraph com classe "ementa" (data-style)
 *  - [[NOTA]]             → paragraph com classe "nota"
 *  - [[ALERTA_VERMELHO]]  → paragraph com classe "alerta"
 *  - Cabeçalhos "TEMA - X" ou tudo em CAIXA ALTA dentro de CORPO viram
 *    heading level 3 (não-destrutivo: round-trip preserva o texto).
 *
 * Marks inline suportados: `**bold**`, `*italic*`, `***both***`. Resto
 * passa literal.
 *
 * O round-trip é projetado para ser idempotente para 99% dos casos.
 * Marcadores desconhecidos viram texto comum.
 */

export type ParaStyle = "corpo" | "transcricao" | "ementa" | "nota" | "alerta";

interface RawBlock {
  style: ParaStyle;
  marker: string; // marcador original, ex.: "[[TRANSCRICAO1]]"
  paragraphs: string[];
}

const MARKER_TO_STYLE: Record<string, ParaStyle> = {
  "[[CORPO]]": "corpo",
  "[[TRANSCRICAO1]]": "transcricao",
  "[[TRANSCRICAO2]]": "transcricao",
  "[[TRANSCRICAO3]]": "transcricao",
  "[[EMENTA]]": "ementa",
  "[[NOTA]]": "nota",
  "[[ALERTA_VERMELHO]]": "alerta",
};

const STYLE_TO_MARKER: Record<ParaStyle, string> = {
  corpo: "[[CORPO]]",
  transcricao: "[[TRANSCRICAO1]]",
  ementa: "[[EMENTA]]",
  nota: "[[NOTA]]",
  alerta: "[[ALERTA_VERMELHO]]",
};

function parseBlocks(md: string): RawBlock[] {
  const lines = (md ?? "").split(/\r?\n/);
  const out: RawBlock[] = [];
  let current: RawBlock = {
    style: "corpo",
    marker: "[[CORPO]]",
    paragraphs: [],
  };
  for (const raw of lines) {
    const line = raw.replace(/\s+$/, "");
    const trimmed = line.trim();
    if (MARKER_TO_STYLE[trimmed]) {
      if (current.paragraphs.length > 0) out.push(current);
      current = {
        style: MARKER_TO_STYLE[trimmed],
        marker: trimmed,
        paragraphs: [],
      };
      continue;
    }
    if (!trimmed) continue;
    current.paragraphs.push(trimmed);
  }
  if (current.paragraphs.length > 0) out.push(current);
  return out;
}

function isHeading(text: string): boolean {
  if (text.startsWith("TEMA ") || text.startsWith("TEMA-")) return true;
  if (text.toUpperCase() === "DISPOSITIVO") return true;
  if (
    text.length > 8 &&
    text === text.toUpperCase() &&
    /^[A-ZÀ-Ý0-9 \-,()/.ºª§:]+$/.test(text)
  ) {
    return true;
  }
  return false;
}

// --- inline marks parser ----------------------------------------------------

interface InlineNode {
  type: "text";
  text: string;
  marks?: Array<{ type: "bold" | "italic" }>;
}

function parseInline(text: string): InlineNode[] {
  const out: InlineNode[] = [];
  let rest = text;
  // ordem importa: tripla > dupla > simples
  const pattern = /(\*\*\*([^*]+)\*\*\*|\*\*([^*]+)\*\*|\*([^*]+)\*)/;
  while (rest.length > 0) {
    const m = pattern.exec(rest);
    if (!m) {
      out.push({ type: "text", text: rest });
      break;
    }
    if (m.index > 0) {
      out.push({ type: "text", text: rest.slice(0, m.index) });
    }
    if (m[2] !== undefined) {
      out.push({
        type: "text",
        text: m[2],
        marks: [{ type: "bold" }, { type: "italic" }],
      });
    } else if (m[3] !== undefined) {
      out.push({ type: "text", text: m[3], marks: [{ type: "bold" }] });
    } else if (m[4] !== undefined) {
      out.push({ type: "text", text: m[4], marks: [{ type: "italic" }] });
    }
    rest = rest.slice(m.index + m[0].length);
  }
  return out.filter((n) => n.text.length > 0);
}

function serializeInline(content: InlineNode[] | undefined): string {
  if (!content) return "";
  let out = "";
  for (const node of content) {
    if (node.type !== "text") continue;
    const hasBold = node.marks?.some((m) => m.type === "bold") ?? false;
    const hasItalic = node.marks?.some((m) => m.type === "italic") ?? false;
    if (hasBold && hasItalic) out += `***${node.text}***`;
    else if (hasBold) out += `**${node.text}**`;
    else if (hasItalic) out += `*${node.text}*`;
    else out += node.text;
  }
  return out;
}

// --- markdown → tiptap doc -------------------------------------------------

export function markdownToDoc(md: string): Record<string, unknown> {
  const blocks = parseBlocks(md);
  const content: Record<string, unknown>[] = [];
  for (const block of blocks) {
    if (block.style === "transcricao") {
      content.push({
        type: "blockquote",
        attrs: { dataMarker: block.marker, dataStyle: "transcricao" },
        content: block.paragraphs.map((p) => ({
          type: "paragraph",
          content: parseInline(p),
        })),
      });
      continue;
    }
    for (const p of block.paragraphs) {
      if (block.style === "corpo" && isHeading(p)) {
        content.push({
          type: "heading",
          attrs: { level: 3, dataStyle: "tema" },
          content: parseInline(p),
        });
        continue;
      }
      content.push({
        type: "paragraph",
        attrs: block.style === "corpo" ? null : { dataStyle: block.style },
        content: parseInline(p),
      });
    }
  }
  if (content.length === 0) {
    content.push({ type: "paragraph" });
  }
  return { type: "doc", content };
}

// --- tiptap doc → markdown -------------------------------------------------

interface DocNode {
  type: string;
  attrs?: Record<string, unknown> | null;
  content?: DocNode[];
  text?: string;
  marks?: Array<{ type: string }>;
}

function inlineNodes(nodes: DocNode[] | undefined): InlineNode[] {
  if (!nodes) return [];
  return nodes
    .filter((n) => n.type === "text" && typeof n.text === "string")
    .map((n) => ({
      type: "text",
      text: n.text!,
      marks: n.marks?.filter(
        (m): m is { type: "bold" | "italic" } =>
          m.type === "bold" || m.type === "italic",
      ),
    }));
}

export function docToMarkdown(doc: Record<string, unknown>): string {
  const root = doc as unknown as DocNode;
  const children: DocNode[] = root.content ?? [];
  const out: string[] = [];
  let lastStyle: ParaStyle | null = null;

  const emitMarker = (style: ParaStyle, attrs?: Record<string, unknown> | null) => {
    if (style === lastStyle) return;
    const marker =
      style === "transcricao" && attrs?.dataMarker
        ? String(attrs.dataMarker)
        : STYLE_TO_MARKER[style];
    if (out.length > 0) out.push("");
    out.push(marker);
    lastStyle = style;
  };

  for (const node of children) {
    if (node.type === "blockquote") {
      emitMarker("transcricao", node.attrs);
      const paragraphs = (node.content ?? []).filter(
        (p) => p.type === "paragraph",
      );
      for (const p of paragraphs) {
        const text = serializeInline(inlineNodes(p.content));
        if (text.trim()) out.push(text);
      }
      continue;
    }
    if (node.type === "heading") {
      emitMarker("corpo");
      const text = serializeInline(inlineNodes(node.content));
      if (text.trim()) out.push(text);
      continue;
    }
    if (node.type === "paragraph") {
      const style = (node.attrs?.dataStyle as ParaStyle | undefined) ?? "corpo";
      const okStyle: ParaStyle =
        style === "transcricao" ||
        style === "ementa" ||
        style === "nota" ||
        style === "alerta"
          ? style
          : "corpo";
      emitMarker(okStyle, node.attrs);
      const text = serializeInline(inlineNodes(node.content));
      if (text.trim()) out.push(text);
    }
  }
  // garante que o resultado começa com um marcador
  if (out.length === 0 || !out[0].startsWith("[[")) {
    out.unshift("[[CORPO]]");
  }
  return out.join("\n");
}
