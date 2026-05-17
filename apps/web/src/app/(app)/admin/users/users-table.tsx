"use client";

import { useActionState, useState } from "react";
import { CheckCircle2 } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { setUserRoleAction, type RoleUpdateState } from "./actions";

const INITIAL: RoleUpdateState = {};

interface Row {
  id: string;
  email: string;
  name: string | null;
  role: string;
  createdAt: Date;
}

const ROLE_LABEL: Record<string, string> = {
  user: "Usuário",
  manager: "Gerente",
  admin: "Administrador",
};

const ROLE_VARIANT: Record<string, "muted" | "secondary" | "default"> = {
  user: "muted",
  manager: "secondary",
  admin: "default",
};

function initials(email: string): string {
  const local = email.split("@")[0] ?? "";
  return (local.match(/[a-z]/gi)?.slice(0, 2).join("") || email.slice(0, 2)).toUpperCase();
}

interface Props {
  rows: Row[];
  currentEmail: string;
}

export function UsersTable({ rows, currentEmail }: Props) {
  if (rows.length === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-16 text-center">
          <p className="text-sm text-muted-foreground">
            Nenhum usuário registrado ainda. Eles aparecem aqui após o primeiro
            login.
          </p>
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardContent className="p-0">
        <ul className="divide-y">
          {rows.map((u) => (
            <UserRow key={u.id} row={u} isSelf={u.email === currentEmail} />
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function UserRow({ row, isSelf }: { row: Row; isSelf: boolean }) {
  const [state, formAction, pending] = useActionState(
    setUserRoleAction,
    INITIAL,
  );
  const [role, setRole] = useState(row.role);

  return (
    <li className="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
      <div className="flex items-center gap-3">
        <Avatar className="h-10 w-10">
          <AvatarFallback className="bg-primary/10 text-primary">
            {initials(row.email)}
          </AvatarFallback>
        </Avatar>
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <p className="text-sm font-medium">{row.email}</p>
            {isSelf && (
              <Badge variant="outline" className="text-[9px]">
                Você
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            Desde{" "}
            {row.createdAt.toLocaleDateString("pt-BR", {
              day: "2-digit",
              month: "short",
              year: "numeric",
            })}
            {" · "}
            <Badge
              variant={ROLE_VARIANT[row.role] ?? "muted"}
              className="ml-1 align-middle"
            >
              {ROLE_LABEL[row.role] ?? row.role}
            </Badge>
          </p>
        </div>
      </div>

      <form action={formAction} className="flex items-center gap-2">
        <input type="hidden" name="userId" value={row.id} />
        <input type="hidden" name="role" value={role} />
        <Select value={role} onValueChange={setRole}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="user">Usuário</SelectItem>
            <SelectItem value="manager">Gerente</SelectItem>
            <SelectItem value="admin">Administrador</SelectItem>
          </SelectContent>
        </Select>
        <Button type="submit" disabled={pending || role === row.role}>
          {pending ? "Salvando…" : "Salvar"}
        </Button>
        {state.ok && (
          <CheckCircle2 className="h-4 w-4 text-success" />
        )}
        {state.error && (
          <span className="text-xs text-destructive">{state.error}</span>
        )}
      </form>
    </li>
  );
}
