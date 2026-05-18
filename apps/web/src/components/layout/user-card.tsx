import { LogOut } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { signOut } from "@/lib/auth";
import type { UserRole } from "@/lib/roles";

const ROLE_LABEL: Record<UserRole, string> = {
  user: "Usuário",
  manager: "Gerente",
  admin: "Administrador",
};

function initialsFromEmail(email: string): string {
  const local = email.split("@")[0] ?? "";
  return (local.match(/[a-z]/gi)?.slice(0, 2).join("") || email.slice(0, 2)).toUpperCase();
}

export function UserCard({
  email,
  role,
}: {
  email: string;
  role: UserRole;
}) {
  return (
    <div className="border-t bg-card/50 p-3">
      <div className="flex items-center gap-3">
        <Avatar>
          <AvatarFallback className="bg-primary text-primary-foreground">
            {initialsFromEmail(email)}
          </AvatarFallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{email}</p>
          <Badge variant="muted" className="mt-1">
            {ROLE_LABEL[role]}
          </Badge>
        </div>
        <form
          action={async () => {
            "use server";
            await signOut({ redirectTo: "/sign-in" });
          }}
        >
          <button
            type="submit"
            title="Sair"
            className="rounded-md p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
