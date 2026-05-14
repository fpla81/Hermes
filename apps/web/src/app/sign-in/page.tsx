import { signIn } from "@/lib/auth";

export default function SignInPage({
  searchParams,
}: {
  searchParams?: Promise<{ error?: string }>;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-background">
      <div className="w-full max-w-sm space-y-6 border rounded-lg p-6 bg-card">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Entrar no Hermes</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Acesso privado. Use suas credenciais.
          </p>
        </div>
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
          className="space-y-3"
        >
          <input
            name="email"
            type="email"
            required
            placeholder="email"
            className="w-full h-10 px-3 rounded-md border bg-background"
          />
          <input
            name="password"
            type="password"
            required
            placeholder="senha"
            className="w-full h-10 px-3 rounded-md border bg-background"
          />
          <ErrorMessage searchParams={searchParams} />
          <button
            type="submit"
            className="w-full h-10 rounded-md bg-primary text-primary-foreground font-medium hover:opacity-90"
          >
            Entrar
          </button>
        </form>
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
    <p className="text-sm text-destructive">Credenciais inválidas.</p>
  );
}
