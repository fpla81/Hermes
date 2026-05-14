import { signIn } from "@/lib/auth";

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-background">
      <div className="w-full max-w-sm space-y-6 border rounded-lg p-6 bg-card">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Entrar no Hermes</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Enviaremos um link mágico para o seu e-mail.
          </p>
        </div>
        <form
          action={async (formData) => {
            "use server";
            const email = formData.get("email") as string;
            await signIn(
              process.env.AUTH_RESEND_KEY ? "resend" : "nodemailer",
              { email, redirectTo: "/cases" },
            );
          }}
          className="space-y-3"
        >
          <input
            name="email"
            type="email"
            required
            placeholder="voce@dominio.com"
            className="w-full h-10 px-3 rounded-md border bg-background"
          />
          <button
            type="submit"
            className="w-full h-10 rounded-md bg-primary text-primary-foreground font-medium hover:opacity-90"
          >
            Enviar link
          </button>
        </form>
      </div>
    </div>
  );
}
