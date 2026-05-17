"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import {
  BookOpen,
  ChevronDown,
  Filter,
  Lock,
  Pencil,
  Search,
  TrendingUp,
  Trash2,
} from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Fundamento } from "@/lib/fundamentos-types";
import { cn } from "@/lib/utils";

import { deleteFundamentoAction } from "./actions";
import { FundamentoEditorDialog } from "./editor-dialog";

interface Props {
  initialQuery: string;
  initialTema: string;
  items: Fundamento[];
  canEdit: boolean;
}

export function FundamentosBrowser({
  initialQuery,
  initialTema,
  items,
  canEdit,
}: Props) {
  const router = useRouter();
  const [q, setQ] = useState(initialQuery);
  const [tema, setTema] = useState(initialTema);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [removing, setRemoving] = useState<string | null>(null);
  const [editing, setEditing] = useState<Fundamento | null>(null);
  const [, startTransition] = useTransition();

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams();
    if (q.trim()) params.set("q", q.trim());
    if (tema.trim()) params.set("tema", tema.trim());
    const qs = params.toString();
    startTransition(() => {
      router.push(qs ? `/fundamentos?${qs}` : "/fundamentos");
    });
  };

  const onDelete = async (id: string) => {
    if (!confirm("Remover esta fundamentação?")) return;
    setRemoving(id);
    try {
      const fd = new FormData();
      fd.set("id", id);
      await deleteFundamentoAction({}, fd);
      startTransition(() => router.refresh());
    } finally {
      setRemoving(null);
    }
  };

  return (
    <div className="space-y-6">
      {!canEdit && (
        <Alert variant="info">
          <Lock className="h-4 w-4" />
          <AlertDescription>
            Modo somente leitura. Para editar ou remover fundamentações, peça
            ao administrador o papel de gerente.
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardContent className="pt-6">
          <form
            onSubmit={onSubmit}
            className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end"
          >
            <div className="space-y-1.5">
              <Label htmlFor="q">Buscar</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="q"
                  className="pl-9"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="título, resumo, tema"
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="tema">Tema</Label>
              <div className="relative">
                <Filter className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="tema"
                  className="pl-9"
                  value={tema}
                  onChange={(e) => setTema(e.target.value)}
                  placeholder="Ex.: DANO MORAL"
                />
              </div>
            </div>
            <Button type="submit">Filtrar</Button>
          </form>
        </CardContent>
      </Card>

      {items.length === 0 ? (
        <Card className="border-dashed">
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <div className="grid h-12 w-12 place-items-center rounded-full bg-primary/10 text-primary">
              <BookOpen className="h-5 w-5" />
            </div>
            <div className="space-y-1">
              <h3 className="font-serif text-lg font-semibold">
                Nenhuma fundamentação registrada
              </h3>
              <p className="max-w-sm text-sm text-muted-foreground">
                Gerentes podem usar o botão{" "}
                <span className="font-medium">Aprender fundamentação</span> ao
                final de uma minuta para começar a base.
              </p>
            </div>
          </div>
        </Card>
      ) : (
        <ul className="space-y-3">
          {items.map((f) => (
            <li key={f.id}>
              <Card>
                <CardContent className="space-y-3 pt-6">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1 space-y-1">
                      <Badge variant="muted" className="font-mono">
                        {f.tema}
                      </Badge>
                      <h3 className="font-serif text-lg font-semibold leading-snug">
                        {f.titulo}
                      </h3>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <TrendingUp className="h-3 w-3" />
                        <span>{f.usage_count} usos</span>
                      </div>
                      {canEdit && (
                        <div className="flex items-center gap-1">
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => setEditing(f)}
                          >
                            <Pencil className="h-3.5 w-3.5" />
                            Editar
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => onDelete(f.id)}
                            disabled={removing === f.id}
                            className="text-muted-foreground hover:text-destructive"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>

                  {f.resumo && (
                    <p className="text-sm leading-relaxed text-foreground/85">
                      {f.resumo}
                    </p>
                  )}

                  {f.tags && f.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {f.tags.map((t, i) => (
                        <Badge key={i} variant="secondary">
                          {t}
                        </Badge>
                      ))}
                    </div>
                  )}

                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      setExpanded((e) => ({ ...e, [f.id]: !e[f.id] }))
                    }
                    className="-ml-3 text-muted-foreground"
                  >
                    <ChevronDown
                      className={cn(
                        "h-3.5 w-3.5 transition-transform",
                        expanded[f.id] && "rotate-180",
                      )}
                    />
                    {expanded[f.id] ? "Ocultar corpo" : "Ver corpo da fundamentação"}
                  </Button>
                  {expanded[f.id] && (
                    <pre className="overflow-auto whitespace-pre-wrap rounded-md border bg-muted/30 p-3 text-xs leading-relaxed">
                      {f.corpo_md}
                    </pre>
                  )}
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}

      {editing && (
        <FundamentoEditorDialog
          open={!!editing}
          onClose={() => setEditing(null)}
          fundamento={editing}
        />
      )}
    </div>
  );
}
