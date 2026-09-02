# Imagem do painel TERCEIRO360.
FROM node:22-alpine AS dependencias
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:22-alpine AS construcao
WORKDIR /app
COPY --from=dependencias /app/node_modules ./node_modules
COPY . .
# `public/` pode não existir (o projeto não tem arquivo estático ainda),
# e o COPY do estágio final falharia — em produção, não aqui. Criar a
# pasta vazia custa nada e tira essa aresta do caminho do build.
RUN mkdir -p public
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine AS producao
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000

# O build `standalone` traz o servidor e só as dependências que ele usa.
COPY --from=construcao /app/.next/standalone ./
COPY --from=construcao /app/.next/static ./.next/static
COPY --from=construcao /app/public ./public

# Sem privilégio: um servidor web não precisa ser root.
RUN addgroup -g 10001 painel && adduser -u 10001 -G painel -D painel
USER painel

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:3000/entrar').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
