"use client";

import { EditorContent, useEditor } from "@tiptap/react";
import Blockquote from "@tiptap/extension-blockquote";
import Heading from "@tiptap/extension-heading";
import Paragraph from "@tiptap/extension-paragraph";
import StarterKit from "@tiptap/starter-kit";
import { useEffect } from "react";

import { docToMarkdown, markdownToDoc, type ParaStyle } from "@/lib/minuta-markdown";

// Atributos custom em paragraph e blockquote para preservar o estilo
// no round-trip pra markdown.
const ParagraphWithStyle = Paragraph.extend({
  addAttributes() {
    return {
      dataStyle: {
        default: null,
        parseHTML: (el) => el.getAttribute("data-style"),
        renderHTML: (attrs) =>
          attrs.dataStyle ? { "data-style": attrs.dataStyle as string } : {},
      },
    };
  },
});

const BlockquoteWithMarker = Blockquote.extend({
  addAttributes() {
    return {
      dataMarker: {
        default: "[[TRANSCRICAO1]]",
        parseHTML: (el) => el.getAttribute("data-marker") ?? "[[TRANSCRICAO1]]",
        renderHTML: (attrs) => ({ "data-marker": attrs.dataMarker as string }),
      },
      dataStyle: {
        default: "transcricao",
        parseHTML: () => "transcricao",
        renderHTML: () => ({ "data-style": "transcricao" }),
      },
    };
  },
});

const HeadingTema = Heading.extend({
  addAttributes() {
    const parent = this.parent?.() ?? {};
    return {
      ...parent,
      dataStyle: {
        default: "tema",
        parseHTML: (el) => el.getAttribute("data-style") ?? "tema",
        renderHTML: (attrs) => ({ "data-style": attrs.dataStyle as string }),
      },
    };
  },
}).configure({ levels: [3] });

interface Props {
  value: string;
  onChange: (markdown: string) => void;
}

const btnBase =
  "inline-flex h-8 items-center gap-1 rounded border bg-background px-2 text-xs font-medium hover:bg-accent disabled:opacity-40";
const btnActive = "bg-primary text-primary-foreground border-primary";

export function MinutaTiptap({ value, onChange }: Props) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        paragraph: false,
        blockquote: false,
        heading: false,
        // não queremos lista, código, hr, etc. no editor de minuta
        bulletList: false,
        orderedList: false,
        listItem: false,
        codeBlock: false,
        horizontalRule: false,
      }),
      ParagraphWithStyle,
      BlockquoteWithMarker,
      HeadingTema,
    ],
    content: markdownToDoc(value),
    editorProps: {
      attributes: {
        class:
          "min-h-[28rem] w-full max-w-none rounded-md border bg-background p-4 text-sm leading-relaxed focus:outline-none " +
          "[&_blockquote]:ml-8 [&_blockquote]:mr-4 [&_blockquote]:border-l-2 [&_blockquote]:border-muted [&_blockquote]:pl-3 [&_blockquote]:text-[0.8125rem] [&_blockquote]:text-muted-foreground " +
          "[&_p[data-style=ementa]]:ml-12 [&_p[data-style=ementa]]:italic [&_p[data-style=ementa]]:text-muted-foreground " +
          "[&_p[data-style=nota]]:text-xs [&_p[data-style=nota]]:text-muted-foreground " +
          "[&_p[data-style=alerta]]:rounded [&_p[data-style=alerta]]:border [&_p[data-style=alerta]]:border-destructive/40 [&_p[data-style=alerta]]:bg-destructive/10 [&_p[data-style=alerta]]:p-2 [&_p[data-style=alerta]]:text-destructive " +
          "[&_h3]:mt-4 [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:uppercase [&_h3]:tracking-wide " +
          "[&_p]:my-2 [&_p]:text-justify",
      },
    },
    onUpdate: ({ editor }) => {
      const md = docToMarkdown(editor.getJSON());
      onChange(md);
    },
    immediatelyRender: false,
  });

  // Quando o valor externo muda (ex.: rascunho gerado), recarrega o conteúdo
  // SEM disparar onUpdate em loop.
  useEffect(() => {
    if (!editor) return;
    const currentMd = docToMarkdown(editor.getJSON());
    if (currentMd !== value) {
      editor.commands.setContent(markdownToDoc(value), { emitUpdate: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, editor]);

  if (!editor) return null;

  const setStyle = (style: ParaStyle | null) => {
    if (style === "transcricao") {
      editor.chain().focus().setBlockquote().run();
      return;
    }
    // Sai do blockquote se estiver dentro
    if (editor.isActive("blockquote")) {
      editor.chain().focus().lift("blockquote").run();
    }
    editor.chain().focus().setParagraph().run();
    editor
      .chain()
      .focus()
      .updateAttributes("paragraph", { dataStyle: style })
      .run();
  };

  const setTranscricao = (n: 1 | 2 | 3) => {
    const marker = `[[TRANSCRICAO${n}]]`;
    if (!editor.isActive("blockquote")) {
      editor.chain().focus().setBlockquote().run();
    }
    editor
      .chain()
      .focus()
      .updateAttributes("blockquote", { dataMarker: marker })
      .run();
  };

  const isTranscricao = (n: 1 | 2 | 3) =>
    editor.isActive("blockquote") &&
    editor.getAttributes("blockquote").dataMarker === `[[TRANSCRICAO${n}]]`;

  const setHeading = () => {
    if (editor.isActive("heading", { level: 3 })) {
      editor.chain().focus().setParagraph().run();
    } else {
      if (editor.isActive("blockquote")) {
        editor.chain().focus().lift("blockquote").run();
      }
      editor.chain().focus().toggleHeading({ level: 3 }).run();
    }
  };

  const isCorpoActive =
    editor.isActive("paragraph") &&
    !editor.getAttributes("paragraph").dataStyle &&
    !editor.isActive("blockquote");

  const isStyleActive = (s: ParaStyle) =>
    editor.isActive("paragraph") &&
    editor.getAttributes("paragraph").dataStyle === s;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-1 rounded-md border bg-muted/40 p-1">
        <button
          type="button"
          className={`${btnBase} ${isCorpoActive ? btnActive : ""}`}
          onClick={() => setStyle(null)}
          title="Texto comum (CORPO)"
        >
          Corpo
        </button>
        <button
          type="button"
          className={`${btnBase} ${isTranscricao(1) ? btnActive : ""}`}
          onClick={() => setTranscricao(1)}
          title="Transcrição nível 1 — trecho do acórdão recorrido"
        >
          Transcrição 1
        </button>
        <button
          type="button"
          className={`${btnBase} ${isTranscricao(2) ? btnActive : ""}`}
          onClick={() => setTranscricao(2)}
          title="Transcrição nível 2 — embargos de declaração"
        >
          Transcrição 2
        </button>
        <button
          type="button"
          className={`${btnBase} ${isTranscricao(3) ? btnActive : ""}`}
          onClick={() => setTranscricao(3)}
          title="Transcrição nível 3 — outros trechos citados"
        >
          Transcrição 3
        </button>
        <button
          type="button"
          className={`${btnBase} ${isStyleActive("ementa") ? btnActive : ""}`}
          onClick={() => setStyle("ementa")}
          title="Ementa em itálico recuado"
        >
          Ementa
        </button>
        <button
          type="button"
          className={`${btnBase} ${editor.isActive("heading", { level: 3 }) ? btnActive : ""}`}
          onClick={setHeading}
          title="Cabeçalho de TEMA"
        >
          TEMA
        </button>
        <span className="mx-1 h-5 w-px bg-border" aria-hidden />
        <button
          type="button"
          className={`${btnBase} ${editor.isActive("bold") ? btnActive : ""}`}
          onClick={() => editor.chain().focus().toggleBold().run()}
          title="Negrito"
        >
          <strong>N</strong>
        </button>
        <button
          type="button"
          className={`${btnBase} ${editor.isActive("italic") ? btnActive : ""}`}
          onClick={() => editor.chain().focus().toggleItalic().run()}
          title="Itálico"
        >
          <em>I</em>
        </button>
      </div>
      <EditorContent editor={editor} />
    </div>
  );
}
