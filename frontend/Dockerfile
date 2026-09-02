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
# HOSTNAME precisa ser 0.0.0.0 explicitamente. O servidor `standalone` do
# Next lê `process.env.HOSTNAME` e o Docker preenche essa variável sozinho,
# com o nome do contêiner — o servidor então tenta escutar num nome que nem
# sempre resolve, e ou morre na partida ou escuta onde o roteador do Render
# não alcança. O sintoma é 502 com o deploy verde.
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

# O build `standalone` traz o servidor e só as dependências que ele usa.
COPY --from=construcao /app/.next/standalone ./
COPY --from=construcao /app/.next/static ./.next/static
COPY --from=construcao /app/public ./public

# Sem privilégio: um servidor web não precisa ser root.
RUN addgroup -g 10001 painel && adduser -u 10001 -G painel -D painel
USER painel

EXPOSE 3000
# A porta vem do ambiente: o Render injeta a dele e ignora o padrão daqui.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||3000)+'/entrar').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
