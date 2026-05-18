import { Badge } from "@/components/ui/badge";

type Variant = "default" | "secondary" | "outline" | "success" | "warning" | "destructive" | "muted";

const META: Record<string, { label: string; variant: Variant }> = {
  draft: { label: "Rascunho", variant: "muted" },
  capturing: { label: "Capturando", variant: "warning" },
  captured: { label: "Capturado", variant: "muted" },
  preparing: { label: "Preparando", variant: "warning" },
  analyzing: { label: "Analisando", variant: "warning" },
  ready: { label: "Pronto", variant: "success" },
  packaging: { label: "Empacotando", variant: "warning" },
  rendering: { label: "Renderizando", variant: "warning" },
  done: { label: "Concluído", variant: "success" },
  error: { label: "Erro", variant: "destructive" },
};

export function CaseStatusBadge({ status }: { status: string }) {
  const m = META[status] ?? { label: status, variant: "muted" as Variant };
  return <Badge variant={m.variant}>{m.label}</Badge>;
}
