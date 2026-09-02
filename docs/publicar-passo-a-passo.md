# Publicar em ~20 minutos

Sem instalar nada no seu computador. Ao final você tem um endereço que abre em
qualquer navegador, inclusive no celular.

Você já fez a parte 1 (Supabase). Faltam as partes 2 e 3.

---

## Parte 1 — Supabase ✅

Projeto **TERCEIRO360**, região `sa-east-1` (São Paulo). Feito.

### Pegue a string de conexão

1. Abra o projeto TERCEIRO360
2. Botão **Connect**, no topo da página
3. Procure **Transaction pooler** — a que termina em `:6543`
4. Copie. Vai parecer com isto:

```
postgresql://postgres.abcdefgh:[YOUR-PASSWORD]@aws-1-sa-east-1.pooler.supabase.com:6543/postgres
```

5. **Troque `[YOUR-PASSWORD]`** pela senha que você definiu ao criar o projeto
6. **Troque `postgresql://` por `postgresql+psycopg://`** no começo

O resultado final é o que você vai colar no Render:

```
postgresql+psycopg://postgres.abcdefgh:SUASENHA@aws-1-sa-east-1.pooler.supabase.com:6543/postgres
```

> **Use o Transaction pooler, não a "Direct connection".** A conexão direta do
> Supabase hoje só atende por IPv6, e a maioria das hospedagens não tem IPv6 de
> saída — a conexão simplesmente estoura o tempo, sem erro que explique.
>
> **Se a senha tiver `@`, `#`, `/` ou `:`**, ela quebra o endereço em silêncio.
> O mais simples é trocá-la: no Supabase, Settings → Database → Reset database
> password, e gerar uma só com letras e números.

---

## Parte 2 — Render (a API e o painel)

1. Crie a conta em **https://render.com** (pode entrar com o GitHub)
2. **New +** → **Blueprint**
3. Conecte o repositório **hub-finance/Terceiro360**
4. O Render lê o `render.yaml` e mostra os dois serviços já configurados:
   `terceiro360-api` e `terceiro360-painel`
5. Ele vai pedir duas variáveis do serviço **terceiro360-api**:

   - **`T360_DATABASE_URL`** → cole a string montada na Parte 1
   - **`T360_CORS_ORIGENS`** → deixe `[]` por enquanto; ajustamos no fim

6. **Apply**. Ele monta os dois serviços — a primeira vez leva de 5 a 10 minutos.

### Guarde a chave de cifragem — agora

Assim que o serviço subir: **terceiro360-api → Environment → `T360_CHAVE_DADOS`**
→ revele e **copie para um cofre de senhas**.

Ela cifra os CPFs. Perdê-la torna os dados já gravados **ilegíveis para
sempre** — nem eu nem o Supabase conseguem recuperar.

### Feche o círculo do CORS

Quando o painel subir, ele ganha um endereço tipo
`https://terceiro360-painel.onrender.com`. Volte em
**terceiro360-api → Environment** e ajuste:

```
T360_CORS_ORIGENS = ["https://terceiro360-painel.onrender.com"]
```

Salve. O Render reinicia sozinho.

---

## Parte 3 — Entrar

Abra o endereço do **terceiro360-painel**.

A variável **`T360_CARGA_INICIAL`** decide o que é carregado na partida:

| Valor | O que carrega |
|---|---|
| `true` | Perfis, base normativa e modelos de documento |
| `demo` | O acima **+ entidade de demonstração e o primeiro usuário** |
| `false` | Nada |

Para um ambiente de testes, use **`demo`**: é o que cria o acesso
`admin@demo.terceiro360.local` / `terceiro360`.

Ela roda na partida do contêiner, e não num terminal, de propósito: o plano
gratuito do Render não dá acesso ao Shell, e sem isso não haveria como criar o
primeiro usuário — o sistema subiria sem ninguém conseguir entrar.

É idempotente: deixar em `demo` não duplica nada a cada reinício. Para um
ambiente de verdade, troque para `true` (ou `false`) depois da primeira carga,
e apague a entidade de demonstração.

**Troque essa senha no primeiro acesso** (Minha conta → Senha) e ative a
verificação em duas etapas. É um ambiente na internet, com o endereço
adivinhável.

---

## O que esperar do plano gratuito

| | O que acontece |
|---|---|
| **Render grátis** | O serviço dorme após 15 min sem uso. O primeiro acesso depois disso leva ~50 segundos para acordar. Não perde dado. |
| **Supabase grátis** | O banco hiberna após 7 dias sem uso; reativa-se por um botão no painel. Não perde dado. |

Para testar, os dois servem. Para cliente pagante, são US$ 7/mês no Render e
US$ 25/mês no Supabase.

## Uma ressalva honesta sobre região

O Render não tem servidor no Brasil — a API vai rodar nos Estados Unidos,
embora **o banco fique em São Paulo**. Para testar, tudo bem. Para uso real com
dado de cliente, o processamento fora do país conta como transferência
internacional sob a LGPD, e aí o certo é mudar a API para um host com região
brasileira: **Fly.io** (região `gru`) ou **Google Cloud Run**
(`southamerica-east1`). O sistema não muda; só o lugar onde ele roda.
