import type { Config } from "drizzle-kit";

export default {
  schema: "./src/db/schema.ts",
  out: "./drizzle",
  dialect: "postgresql",
  schemaFilter: ["auth"],
  dbCredentials: {
    url:
      process.env.WEB_DATABASE_URL ??
      "postgresql://hermes:hermes@localhost:5432/hermes",
  },
} satisfies Config;
