import NextAuth from "next-auth";
import Resend from "next-auth/providers/resend";
import Nodemailer from "next-auth/providers/nodemailer";
import { DrizzleAdapter } from "@auth/drizzle-adapter";
import { db } from "@/db";
import {
  users,
  accounts,
  sessions,
  verificationTokens,
} from "@/db/schema";
import { authConfig } from "./auth.config";

const useResend = !!process.env.AUTH_RESEND_KEY;

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  adapter: DrizzleAdapter(db, {
    usersTable: users,
    accountsTable: accounts,
    sessionsTable: sessions,
    verificationTokensTable: verificationTokens,
  }),
  session: { strategy: "database" },
  providers: [
    useResend
      ? Resend({
          apiKey: process.env.AUTH_RESEND_KEY!,
          from: process.env.AUTH_EMAIL_FROM ?? "hermes@example.com",
        })
      : Nodemailer({
          server: {
            host: process.env.SMTP_HOST ?? "localhost",
            port: Number(process.env.SMTP_PORT ?? 1025),
            auth: process.env.SMTP_USER
              ? { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS }
              : undefined,
          },
          from: process.env.AUTH_EMAIL_FROM ?? "hermes@example.com",
        }),
  ],
  callbacks: {
    ...authConfig.callbacks,
    async session({ session, user }) {
      if (session.user) {
        session.user.id = user.id;
        (session.user as { role?: string }).role = (user as { role?: string }).role;
      }
      return session;
    },
  },
});
