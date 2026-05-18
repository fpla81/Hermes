import type { NextAuthConfig } from "next-auth";

/**
 * Config edge-safe usada pelo middleware. Não inclua providers ou adapter
 * — eles vivem em ``auth.ts``.
 */
export const authConfig: NextAuthConfig = {
  pages: { signIn: "/sign-in" },
  providers: [],
};
