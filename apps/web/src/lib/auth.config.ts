import type { NextAuthConfig } from "next-auth";

/**
 * Config compartilhada usada pelo middleware (Edge runtime).
 *
 * NÃO inclua aqui providers que dependem de APIs Node (Nodemailer/Resend
 * importam `stream`, `crypto`, etc. — quebra o Edge). A config completa,
 * com Drizzle adapter e providers, fica em `auth.ts` e é usada em rotas
 * server-side e Route Handlers.
 */
export const authConfig: NextAuthConfig = {
  pages: { signIn: "/sign-in" },
  providers: [],
  callbacks: {
    authorized({ auth }) {
      return !!auth?.user;
    },
  },
};
