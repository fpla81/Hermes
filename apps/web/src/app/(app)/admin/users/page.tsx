import { asc } from "drizzle-orm";
import { notFound } from "next/navigation";

import { PageHeader } from "@/components/layout/page-header";
import { db } from "@/db";
import { users } from "@/db/schema";
import { auth } from "@/lib/auth";
import { isAdmin } from "@/lib/roles";

import { UsersTable } from "./users-table";

export const dynamic = "force-dynamic";

export default async function AdminUsersPage() {
  const session = await auth();
  if (!isAdmin(session?.user?.role)) {
    notFound();
  }
  const rows = await db
    .select({
      id: users.id,
      email: users.email,
      name: users.name,
      role: users.role,
      createdAt: users.createdAt,
    })
    .from(users)
    .orderBy(asc(users.email));

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Administração"
        title="Usuários"
        description="Atribua papéis. Gerentes podem extrair fundamentações e editar a base do gabinete. Demais usuários geram e editam apenas minutas."
      />

      <UsersTable
        rows={rows}
        currentEmail={session?.user?.email?.toLowerCase() ?? ""}
      />
    </div>
  );
}
