"use server";

import { eq } from "drizzle-orm";
import { revalidatePath } from "next/cache";

import { db } from "@/db";
import { users } from "@/db/schema";
import { auth } from "@/lib/auth";
import { isAdmin, type UserRole } from "@/lib/roles";

export interface RoleUpdateState {
  ok?: boolean;
  error?: string;
}

const VALID_ROLES: UserRole[] = ["user", "manager", "admin"];

export async function setUserRoleAction(
  _prev: RoleUpdateState,
  form: FormData,
): Promise<RoleUpdateState> {
  const session = await auth();
  if (!isAdmin(session?.user?.role)) {
    return { error: "acesso restrito a administradores" };
  }
  const userId = String(form.get("userId") ?? "");
  const role = String(form.get("role") ?? "") as UserRole;
  if (!userId) return { error: "userId ausente" };
  if (!VALID_ROLES.includes(role)) return { error: "role inválida" };

  // Impede o admin de rebaixar a si mesmo (se for o último).
  const self = await db
    .select({ id: users.id, email: users.email })
    .from(users)
    .where(eq(users.id, userId))
    .limit(1);
  if (self.length === 0) return { error: "usuário não encontrado" };
  if (
    self[0].email === session?.user?.email?.toLowerCase() &&
    role !== "admin"
  ) {
    const admins = await db
      .select({ id: users.id })
      .from(users)
      .where(eq(users.role, "admin"));
    if (admins.length <= 1) {
      return { error: "não há outro admin — promova alguém antes de rebaixar você" };
    }
  }

  await db.update(users).set({ role }).where(eq(users.id, userId));
  revalidatePath("/admin/users");
  return { ok: true };
}
