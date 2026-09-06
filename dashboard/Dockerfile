# Built from the monorepo root, not dashboard/, because the dashboard imports
# the shared design system and bridge protocol from ../shared.
#
# Next.js 16 requires Node 20.9+; 22 is the current LTS.
FROM node:22-alpine

WORKDIR /app

COPY dashboard/package*.json ./dashboard/
RUN cd dashboard && npm install

COPY shared ./shared
COPY dashboard ./dashboard

WORKDIR /app/dashboard

EXPOSE 3000

CMD ["npm", "run", "dev"]
