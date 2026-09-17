# syntax=docker/dockerfile:1

# ---- deps: shared base for dev + build stages -----------------------------
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# ---- dev: used by docker-compose.yml (vite dev server + HMR) --------------
FROM deps AS dev
WORKDIR /app
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ---- build: production static bundle ---------------------------------------
FROM deps AS build
WORKDIR /app
COPY . .
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# ---- prod: nginx serving the static bundle + SPA fallback ------------------
FROM nginx:1.27-alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=5 \
    CMD wget -q -O- http://localhost:80/ || exit 1
CMD ["nginx", "-g", "daemon off;"]
