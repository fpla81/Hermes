import Link from "next/link";
import type { Route } from "next";
import { redirect } from "next/navigation";
import { auth, signOut } from "@/lib/auth";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { FileText, BookOpen, ScrollText, Settings, Users } from "lucide-react";
import { isAdmin } from "@/lib/roles";

const baseNav: { href: Route; label: string; icon: typeof FileText }[] = [
  { href: "/cases", label: "Casos", icon: FileText },
  { href: "/fundamentos", label: "Fundamentos", icon: BookOpen },
  { href: "/templates", label: "Templates", icon: ScrollText },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();
  if (!session?.user) {
    redirect("/sign-in");
  }
  const nav = isAdmin(session.user.role)
    ? [
        ...baseNav,
        { href: "/admin/users" as Route, label: "Usuários", icon: Users },
      ]
    : baseNav;

  return (
    <div className="flex min-h-screen">
      <aside className="w-60 border-r bg-card flex flex-col">
        <div className="h-14 flex items-center px-4 border-b">
          <Link href="/cases" className="font-semibold tracking-tight">
            Hermes
          </Link>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="p-3 border-t text-xs text-muted-foreground space-y-2">
          {session?.user?.email ? (
            <>
              <div className="truncate">{session.user.email}</div>
              <form
                action={async () => {
                  "use server";
                  await signOut({ redirectTo: "/sign-in" });
                }}
              >
                <button className="hover:underline" type="submit">
                  Sair
                </button>
              </form>
            </>
          ) : (
            <Link href="/sign-in" className="hover:underline">
              Entrar
            </Link>
          )}
        </div>
      </aside>

      <div className="flex-1 flex flex-col">
        <header className="h-14 border-b flex items-center justify-end gap-3 px-4">
          <ThemeToggle />
        </header>
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
