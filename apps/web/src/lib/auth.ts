import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

import { authConfig } from "./auth.config";

const ALLOWED_EMAIL = process.env.HERMES_USER_EMAIL ?? "admin@hermes.local";
const ALLOWED_PASSWORD = process.env.HERMES_USER_PASSWORD ?? "hermes";

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
        if (
          email === ALLOWED_EMAIL.toLowerCase() &&
          password === ALLOWED_PASSWORD
        ) {
          return { id: email, email, name: email };
        }
        return null;
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
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = (token.id as string) ?? (token.email as string);
        session.user.email = (token.email as string) ?? session.user.email;
      }
      return session;
    },
  },
});
