FROM node:22-bookworm-slim AS frontend-build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY index.html tsconfig.json vite.config.ts ./
COPY public ./public
COPY src ./src
RUN npm run build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends nginx supervisor curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY services/productos/requirements.txt /tmp/productos-requirements.txt
COPY services/clientes/requirements.txt /tmp/clientes-requirements.txt
COPY services/pedidos/requirements.txt /tmp/pedidos-requirements.txt
RUN pip install --no-cache-dir -r /tmp/productos-requirements.txt -r /tmp/clientes-requirements.txt -r /tmp/pedidos-requirements.txt
COPY services ./services
COPY nginx.production.conf /etc/nginx/conf.d/default.conf
COPY supervisord.conf /etc/supervisor/conf.d/app.conf
COPY --from=frontend-build /app/dist /usr/share/nginx/html
RUN rm -f /etc/nginx/sites-enabled/default
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD curl -f http://localhost:3000/api/productos/salud || exit 1
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
