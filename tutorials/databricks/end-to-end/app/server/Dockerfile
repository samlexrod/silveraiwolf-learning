# Silverline Explorer — GraphQL server (Apollo + pg → Lakebase)
FROM node:24-slim

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY tsconfig.json ./
COPY src ./src

ENV PORT=4000
EXPOSE 4000

# Runs via tsx. In a container there's no Databricks CLI, so set SP_CLIENT_ID + SP_SECRET
# (+ DATABRICKS_HOST) in the env to use the headless service-principal (M2M) auth mode.
CMD ["npm", "run", "serve"]
