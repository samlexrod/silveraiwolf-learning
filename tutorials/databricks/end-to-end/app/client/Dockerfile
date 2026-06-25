# Silverline Explorer — React/Vite client. Build the static bundle, serve with nginx.
FROM node:24-slim AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY . .
# The browser runs on the host, so it reaches the server via the published port.
ARG VITE_SERVER=localhost:4000
ENV VITE_SERVER=$VITE_SERVER
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
