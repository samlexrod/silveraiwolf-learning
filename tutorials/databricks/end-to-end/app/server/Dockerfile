# Silverline Explorer — pre-built GraphQL server bundle.
FROM node:24-slim

WORKDIR /app
COPY package.json ./
COPY dist/server.js ./dist/server.js
COPY data ./data

ENV PORT=4000
EXPOSE 4000

CMD ["node", "dist/server.js"]
