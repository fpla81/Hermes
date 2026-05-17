import { Scale } from "lucide-react";

import { Brand } from "@/components/layout/brand";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { signIn } from "@/lib/auth";

export default function SignInPage({
  searchParams,
}: {
  searchParams?: Promise<{ error?: string }>;
}) {
  return (
    <div className="bg-editorial relative flex min-h-screen items-center justify-center overflow-hidden p-6">
      <div className="absolute inset-0 -z-10 bg-background" />
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <Brand size="lg" />
          <p className="max-w-xs text-balance text-sm text-muted-foreground">
            Análise e minutas para processos do TST. Acesso restrito ao gabinete.
          </p>
        </div>

        <Card className="border-border/80 shadow-lg">
          <CardContent className="pt-6">
            <form
              action={async (formData) => {
                "use server";
                const email = String(formData.get("email") ?? "");
                const password = String(formData.get("password") ?? "");
                await signIn("credentials", {
                  email,
                  password,
                  redirectTo: "/cases",
                });
              }}
              className="space-y-4"
            >
              <div className="space-y-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  required
                  placeholder="voce@gabinete.local"
                  autoComplete="email"
                  autoFocus
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password">Senha</Label>
                <Input
                  id="password"
                  name="password"
                  type="password"
                  required
                  autoComplete="current-password"
                />
              </div>
              <ErrorMessage searchParams={searchParams} />
              <Button type="submit" className="w-full" size="lg">
                Entrar
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="mt-6 flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <Scale className="h-3 w-3" />
          Hermes · uso interno
        </p>
      </div>
    </div>
  );
}

async function ErrorMessage({
  searchParams,
}: {
  searchParams?: Promise<{ error?: string }>;
}) {
  const sp = await searchParams;
  if (!sp?.error) return null;
  return (
    <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
      Credenciais inválidas. Tente novamente.
    </p>
  );
}
