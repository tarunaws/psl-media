# Build React app
FROM node:22-alpine AS build
WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
# CRA reads env vars at build time.
# Provide REACT_APP_* values via build args if needed.
RUN npm run build

# Serve via nginx + reverse proxy to private k8s services
FROM nginx:1.27-alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
