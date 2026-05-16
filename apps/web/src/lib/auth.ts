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
        // DEBUG: remove depois que login funcionar
        console.log("[auth.authorize] tentativa:", {
          email,
          passwordLen: password.length,
          expectedLen: SHARED_PASSWORD.length,
          allowed: ALLOWED_EMAILS,
          emailInAllow: ALLOWED_EMAILS.includes(email),
          passwordMatch: password === SHARED_PASSWORD,
        });
        if (!email || password !== SHARED_PASSWORD) return null;
        if (!ALLOWED_EMAILS.includes(email)) return null;
        return { id: email, email, name: email };
      },
    }),
  ],
  callbacks: {
    ...authConfig.callbacks,
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.email = user.email;
      }
      // Relê role do banco a cada refresh — assim mudanças via
      // /admin/users ou nas envs HERMES_ADMINS / HERMES_MANAGERS
      // entram em vigor na próxima request, sem precisar logar de novo.
      if (token.email) {
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
