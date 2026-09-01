# Publicação — Supabase (banco) + API + painel

O TERCEIRO360 tem três peças. Só uma delas o Supabase hospeda.

| Peça | Onde | Por quê |
|---|---|---|
| **Banco PostgreSQL** | Supabase, região **São Paulo** | Dado pessoal em território nacional simplifica a LGPD, e a latência cai. |
| **API (Python/FastAPI)** | Um host de contêiner: Fly.io, Render, Railway, Cloud Run | O Supabase não roda Python. |
| **Painel (Next.js)** | Vercel, ou o mesmo host, pelo `frontend/Dockerfile` | — |

## 1. Banco no Supabase

Crie o projeto **na região South America (São Paulo)** — a região não muda
depois sem migrar tudo.

### A string de conexão: qual das duas

O Supabase oferece duas, e a escolha tem consequência:

```
# Pooler em modo transação — porta 6543. Use esta.
postgresql+psycopg://postgres.SEUPROJETO:SENHA@aws-1-sa-east-1.pooler.supabase.com:6543/postgres?sslmode=require

# Conexão direta — porta 5432. Só para rodar migração.
postgresql+psycopg://postgres:SENHA@db.SEUPROJETO.supabase.co:5432/postgres?sslmode=require
```

**Por que o pooler para a aplicação:** o projeto tem um teto baixo de conexões
diretas, e cada réplica da API abriria as suas. O pooler multiplexa.

**Por que a direta para migrar:** migração cria e altera objeto no schema; em
modo transação isso é frágil.

**A armadilha:** em modo transação, cada consulta pode cair numa conexão
diferente. O psycopg prepara a consulta repetida e depois a chama pelo nome —
e a conexão seguinte não conhece aquele nome. O sintoma é
`prepared statement "_pg3_1" does not exist`, intermitente, só sob carga, nunca
em desenvolvimento. `app/core/db.py` detecta o pooler pela porta e pelo host e
desliga o preparo automático sozinho; não é preciso configurar nada.

Duas coisas que também mordem:

- **Senha com caractere especial.** Um `@` ou `#` na senha quebra a URL em
  silêncio. Codifique (`@` vira `%40`) ou troque a senha por uma sem símbolos.
- **`sslmode=require`.** Sem ele a conexão pode cair para texto puro.

### Migrar

Pela conexão **direta**, uma vez a cada publicação:

```bash
T360_DATABASE_URL="postgresql+psycopg://postgres:SENHA@db.SEUPROJETO.supabase.co:5432/postgres?sslmode=require" \
  python -m alembic upgrade head
```

Depois a carga inicial — perfis, base normativa e modelos, **sem** `--demo`:

```bash
python -m app.seeds
```

## 2. As chaves

Em produção a API **se recusa a subir** sem estas duas. É deliberado: subir
inseguro em silêncio é pior do que não subir.

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"   # rode duas vezes
```

| Variável | O que acontece se vazar | O que acontece se perder |
|---|---|---|
| `T360_SECRET_KEY` | Qualquer um forja a sessão de qualquer usuário | Todos são deslogados. Só isso. |
| `T360_CHAVE_DADOS` | Uma cópia do banco entrega os CPFs | **Os CPFs e RGs já gravados ficam ilegíveis para sempre.** |

Guarde a segunda em cofre — não só na variável de ambiente do provedor. Ela não
é recuperável a partir do banco.

Demais variáveis de produção:

```bash
T360_ENVIRONMENT=production
T360_DEBUG=false
T360_CORS_ORIGENS=["https://painel.seudominio.com.br"]
```

## 3. API

Com o `backend/Dockerfile`, em qualquer host de contêiner. Confira depois de
subir:

```bash
curl -sI https://api.seudominio.com.br/saude | grep -i strict-transport
curl -s  https://api.seudominio.com.br/docs -o /dev/null -w '%{http_code}\n'   # 404 é o esperado
```

`/docs` fechado e HSTS presente: os dois sinais de que o ambiente entendeu que
é produção.

## 4. Painel

Na Vercel, aponte o diretório-raiz para `frontend/` e defina `API_URL` com o
endereço público da API. Ou use o `frontend/Dockerfile`, que produz o build
`standalone`.

O painel é o único que fala com a API. O navegador nunca fala — é isso que
mantém o token fora do JavaScript da página.

## 5. Agendador

Sem alguém o disparando, prazo não alerta e mudança na lei não é detectada.
Escolha um:

```cron
0 6 * * *  cd /app && python -m app.agendador tudo
```

No Compose já há um serviço `agendador` que roda a cada 24h. Em host sem cron
(Render, Fly), use o agendador do próprio provedor. Detalhes em
[`agendador.md`](agendador.md).

## 6. Backup

O Supabase faz backup diário automático — no plano gratuito, com retenção
curta. Isso **não** é um plano de backup, por dois motivos: retenção curta não
cobre um erro descoberto semanas depois, e backup nunca restaurado não é
backup.

Faça o seu, e teste a volta:

```bash
# Cópia (pela conexão direta)
pg_dump "postgresql://postgres:SENHA@db.SEUPROJETO.supabase.co:5432/postgres?sslmode=require" \
  --no-owner --no-acl -Fc -f terceiro360-$(date +%F).dump

# Ensaio de restauração num banco descartável — o passo que quase ninguém faz
createdb ensaio_restauracao
pg_restore -d ensaio_restauracao --no-owner terceiro360-$(date +%F).dump
psql -d ensaio_restauracao -c "SELECT count(*) FROM pessoas;"
```

Guarde a cópia **fora** do Supabase. Backup no mesmo provedor não protege
contra perder o acesso à conta.

Lembre que o CPF sai cifrado no dump: para lê-lo depois é preciso a
`T360_CHAVE_DADOS` da época. Backup do banco sem a chave é backup incompleto.

## 7. Conferência final

- [ ] Região do projeto Supabase é São Paulo
- [ ] `T360_SECRET_KEY` e `T360_CHAVE_DADOS` geradas, e a segunda no cofre
- [ ] `T360_ENVIRONMENT=production` e `T360_DEBUG=false`
- [ ] `T360_CORS_ORIGENS` com o domínio real, sem `*`
- [ ] `alembic upgrade head` rodado pela conexão direta
- [ ] Carga inicial **sem** `--demo`
- [ ] `/docs` respondendo 404 e HSTS presente
- [ ] Agendador disparando diariamente
- [ ] Backup próprio, restaurado uma vez para valer
- [ ] Verificação em duas etapas ativada nas contas com acesso amplo
- [ ] Base normativa conferida por responsável com registro profissional
