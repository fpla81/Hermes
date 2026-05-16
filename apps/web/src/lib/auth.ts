import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

import { authConfig } from "./auth.config";
import { upsertUserAndGetRole, type UserRole } from "./roles";

const SHARED_PASSWORD = process.env.HERMES_USER_PASSWORD ?? "hermes";

const ALLOWED_EMAILS_RAW = process.env.HERMES_ALLOWED_EMAILS;
const ALLOWED_EMAILS = ALLOWED_EMAILS_RAW
  ? ALLOWED_EMAILS_RAW.split(",").map((e) => e.trim().toLowerCase()).filter(Boolean)
  : [(process.env.HERMES_USER_EMAIL ?? "admin@hermes.local").toLowerCase()];

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  session: { strategy: "jwt" },
  providers: [
    Credentials({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Senha", type: "password" },
      },
      async authorize(creds) {
        const email = String(creds?.email ?? "").trim().toLowerCase();
        const password = String(creds?.password ?? "");
        if (!email || password !== SHARED_PASSWORD) return null;
        if (!ALLOWED_EMAILS.includes(email)) return null;
        return { id: email, email, name: email };
      },
    }),
  ],
  callbacks: {
    ...authConfig.callbacks,
    async jwt({ token, user, trigger }) {
      if (user) {
        token.id = user.id;
        token.email = user.email;
      }
      // Lê role do DB. Carrega no primeiro login e quando explicitamente
      // pedido (admin alterou role e disparou update).
      if ((user || trigger === "update" || !token.role) && token.email) {
        try {
          token.role = await upsertUserAndGetRole(token.email as string);
        } catch {
          token.role = (token.role as UserRole | undefined) ?? "user";
        }
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = (token.id as string) ?? (token.email as string);
        session.user.email = (token.email as string) ?? session.user.email;
        session.user.role = (token.role as UserRole | undefined) ?? "user";
      }
      return session;
    },
  },
});
