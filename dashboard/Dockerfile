# Built from the monorepo root, not dashboard/, because the dashboard imports
# the shared design system and bridge protocol from ../shared.
#
# Next.js 16 requires Node 20.9+; 22 is the current LTS.
FROM node:22-alpine AS deps

WORKDIR /app

COPY dashboard/package*.json ./dashboard/
RUN cd dashboard && npm ci

COPY shared ./shared
COPY dashboard ./dashboard

WORKDIR /app/dashboard

ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
ARG NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
ARG NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
ARG NEXT_PUBLIC_SENTRY_DSN=

ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_CLERK_SIGN_IN_URL=$NEXT_PUBLIC_CLERK_SIGN_IN_URL
ENV NEXT_PUBLIC_CLERK_SIGN_UP_URL=$NEXT_PUBLIC_CLERK_SIGN_UP_URL
ENV NEXT_PUBLIC_SENTRY_DSN=$NEXT_PUBLIC_SENTRY_DSN
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

FROM node:22-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

COPY --from=deps /app/shared ./shared
COPY --from=deps /app/dashboard/package*.json ./dashboard/
COPY --from=deps /app/dashboard/node_modules ./dashboard/node_modules
COPY --from=deps /app/dashboard/.next ./dashboard/.next
COPY --from=deps /app/dashboard/public ./dashboard/public
COPY --from=deps /app/dashboard/next.config.* ./dashboard/
COPY --from=deps /app/dashboard/tsconfig.json ./dashboard/

WORKDIR /app/dashboard

EXPOSE 3000

CMD ["npm", "run", "start"]
