# Build context: repo root
FROM node:22-alpine
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@11.1.1 --activate
COPY package.json pnpm-workspace.yaml ./
COPY pnpm-lock.yaml* ./
COPY apps/web/package.json ./apps/web/package.json
COPY packages ./packages
RUN pnpm install --filter web... --frozen-lockfile || pnpm install --filter web...
COPY apps/web ./apps/web
WORKDIR /app/apps/web
EXPOSE 3000
CMD ["pnpm", "dev"]
