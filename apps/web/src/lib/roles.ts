import { eq } from "drizzle-orm";

import { db } from "@/db";
import { users } from "@/db/schema";

export type UserRole = "user" | "manager" | "admin";

const ADMIN_EMAILS = (process.env.HERMES_ADMINS ?? "")
  .split(",")
  .map((e) => e.trim().toLowerCase())
  .filter(Boolean);

const MANAGER_EMAILS = (process.env.HERMES_MANAGERS ?? "")
  .split(",")
  .map((e) => e.trim().toLowerCase())
  .filter(Boolean);

function bootstrapRole(email: string): UserRole {
  const lower = email.toLowerCase();
  if (ADMIN_EMAILS.includes(lower)) return "admin";
  if (MANAGER_EMAILS.includes(lower)) return "manager";
  return "user";
}

/**
 * Upsert do usuário ao logar. Se já existe, mantém a role atual; se for
 * primeiro login, aplica a role-bootstrap das envs ``HERMES_ADMINS`` /
 * ``HERMES_MANAGERS`` (ou "user" como fallback).
 *
 * Retorna a role final que deve viajar no JWT.
 */
export async function upsertUserAndGetRole(email: string): Promise<UserRole> {
  const lower = email.toLowerCase();
  const existing = await db
    .select({ role: users.role })
    .from(users)
    .where(eq(users.email, lower))
    .limit(1);

  if (existing.length > 0) {
    const current = existing[0].role as UserRole;
    // se a env promoveu o email mas o banco ainda não refletiu, ajusta
    const bootstrap = bootstrapRole(email);
    if (
      (bootstrap === "admin" && current !== "admin") ||
      (bootstrap === "manager" && current === "user")
    ) {
      await db
        .update(users)
        .set({ role: bootstrap })
        .where(eq(users.email, lower));
      return bootstrap;
    }
    return current;
  }

  const initialRole = bootstrapRole(email);
  await db
    .insert(users)
    .values({ email: lower, role: initialRole })
    .onConflictDoNothing();
  return initialRole;
}

export function isManager(role: UserRole | undefined | null): boolean {
  return role === "manager" || role === "admin";
}

export function isAdmin(role: UserRole | undefined | null): boolean {
  return role === "admin";
}
