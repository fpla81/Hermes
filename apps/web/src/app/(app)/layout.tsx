import type { Route } from "next";
import { redirect } from "next/navigation";
import {
  FileText,
  BookOpen,
  ScrollText,
  Settings,
  Users,
  Shield,
} from "lucide-react";

import { Brand } from "@/components/layout/brand";
import { SidebarNav, type NavSection } from "@/components/layout/sidebar-nav";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { UserCard } from "@/components/layout/user-card";
import { auth } from "@/lib/auth";
import { isAdmin, type UserRole } from "@/lib/roles";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();
  if (!session?.user) {
    redirect("/sign-in");
  }
  const role = (session.user.role ?? "user") as UserRole;
  const sections: NavSection[] = [
    {
      title: "Trabalho",
      items: [
        { href: "/cases" as Route, label: "Casos", icon: FileText },
        { href: "/fundamentos" as Route, label: "Fundamentos", icon: BookOpen },
        { href: "/templates" as Route, label: "Templates", icon: ScrollText },
      ],
    },
    {
      title: "Conta",
      items: [{ href: "/settings" as Route, label: "Ajustes", icon: Settings }],
    },
  ];
  if (isAdmin(role)) {
    sections.push({
      title: "Administração",
      items: [{ href: "/admin/users" as Route, label: "Usuários", icon: Users }],
    });
  }

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="flex w-64 shrink-0 flex-col border-r bg-card/40 backdrop-blur-sm">
        <div className="flex h-16 items-center border-b px-5">
          <Brand size="md" />
        </div>
        <SidebarNav sections={sections} />
        <UserCard email={session.user.email ?? ""} role={role} />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-end gap-3 border-b bg-background/80 px-6 backdrop-blur-sm">
          <Shield className="h-3.5 w-3.5 text-muted-foreground/60" />
          <span className="text-xs text-muted-foreground">
            Ambiente interno · acesso restrito
          </span>
          <div className="ml-2">
            <ThemeToggle />
          </div>
        </header>
        <main className="flex-1">
          <div className="mx-auto max-w-6xl px-8 py-10">{children}</div>
        </main>
      </div>
    </div>
  );
}
