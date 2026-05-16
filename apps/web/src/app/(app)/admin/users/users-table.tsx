"use client";

import { useActionState, useState } from "react";

import { setUserRoleAction, type RoleUpdateState } from "./actions";

const INITIAL: RoleUpdateState = {};

interface Row {
  id: string;
  email: string;
  name: string | null;
  role: string;
  createdAt: Date;
}

interface Props {
  rows: Row[];
  currentEmail: string;
}

export function UsersTable({ rows, currentEmail }: Props) {
  return (
    <ul className="space-y-2">
      {rows.length === 0 && (
        <li className="rounded border p-4 text-sm text-muted-foreground">
          Nenhum usuário registrado ainda. Os usuários aparecem aqui após o
          primeiro login.
        </li>
      )}
      {rows.map((u) => (
        <UserRow key={u.id} row={u} isSelf={u.email === currentEmail} />
      ))}
    </ul>
  );
}

function UserRow({ row, isSelf }: { row: Row; isSelf: boolean }) {
  const [state, formAction, pending] = useActionState(
    setUserRoleAction,
    INITIAL,
  );
  const [role, setRole] = useState(row.role);

  return (
    <li className="flex flex-wrap items-center justify-between gap-3 rounded-md border bg-background p-3">
      <div className="space-y-0.5">
        <div className="text-sm font-medium">
          {row.email}
          {isSelf && (
            <span className="ml-2 text-[10px] uppercase text-muted-foreground">
              (você)
            </span>
          )}
        </div>
        <div className="text-xs text-muted-foreground">
          desde {row.createdAt.toLocaleDateString("pt-BR")}
        </div>
      </div>

      <form action={formAction} className="flex items-center gap-2">
        <input type="hidden" name="userId" value={row.id} />
        <select
          name="role"
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="h-9 rounded-md border bg-background px-2 text-sm"
        >
          <option value="user">user</option>
          <option value="manager">manager</option>
          <option value="admin">admin</option>
        </select>
        <button
          type="submit"
          disabled={pending || role === row.role}
          className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {pending ? "Salvando…" : "Salvar"}
        </button>
        {state.ok && (
          <span className="text-xs text-emerald-600">✓</span>
        )}
        {state.error && (
          <span className="text-xs text-destructive">{state.error}</span>
        )}
      </form>
    </li>
  );
}
