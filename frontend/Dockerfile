# Multi-stage Dockerfile for Switchyard Frontend
FROM node:22-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci || npm install

COPY . .
RUN npm run build

FROM caddy:2-alpine AS runtime

COPY --from=builder /app/dist /usr/share/caddy
EXPOSE 3001

CMD ["caddy", "file-server", "--root", "/usr/share/caddy", "--listen", ":3001"]
