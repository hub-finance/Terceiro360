# Banco de dados e migrações

## Os dois bancos, e por que dois

| Banco | Onde se usa | Por quê |
|---|---|---|
| **PostgreSQL 16** | produção, homologação, verificação antes de publicar | é o banco real: JSONB, UUID nativo, constraints levadas a sério |
| **SQLite** | desenvolvimento e a suíte do dia a dia | a suíte inteira roda em ~4s, sem subir infraestrutura |

O código não se ramifica entre os dois. Dois decoradores em `app/core/types.py`
resolvem a diferença:

- `GUID` → `UUID` nativo no PostgreSQL, `CHAR(36)` no SQLite
- `JSONType()` → `JSONB` no PostgreSQL, `JSON` no SQLite
- `EnumType` → `VARCHAR` nos dois, convertendo para o membro do enum na leitura

**Antes de publicar, rode a suíte no PostgreSQL.** É onde aparecem as
diferenças que importam:

```bash
make teste-pg
```

## Comandos

```bash
make migrar                          # aplica o que estiver pendente
make migracao m="o que mudou"        # gera a partir do modelo
make carga                           # perfis, base normativa e modelos
make carga demo=1                    # inclui o cenário de demonstração
```

Direto pelo Alembic, quando precisar de controle fino:

```bash
cd backend
.venv/bin/alembic current                  # em que revisão o banco está
.venv/bin/alembic history --verbose        # o caminho até aqui
.venv/bin/alembic upgrade head
.venv/bin/alembic downgrade -1             # volta uma revisão
.venv/bin/alembic upgrade head --sql       # só imprime o DDL, não aplica
```

O último é o que se usa quando o DBA quer revisar o SQL antes de deixar rodar
em produção.

## Como as migrações são escritas aqui

**A URL nunca fica no `alembic.ini`.** Vem de `T360_DATABASE_URL`, ou de quem
chamar a migração passando a URL pela `Config` — uma URL explícita sempre vence
a da configuração. Migração rodar no banco errado em silêncio é o tipo de erro
que só se descobre tarde demais.

**A migração descreve o banco, não o código.** O Alembic é instruído
(`render_item` em `alembic/env.py`) a escrever `postgresql.UUID(as_uuid=True)` e
`sa.String(length=n)` em vez de citar `app.core.types.GUID` ou `EnumType`. Uma
migração de dois anos atrás precisa continuar rodando mesmo que aquelas classes
tenham sido renomeadas.

**Uma transação por migração.** Se uma falhar no meio, o banco não fica
meio migrado.

## O teste que impede a divergência

`tests/test_migracoes.py` sobe um banco limpo, aplica todas as migrações e pede
ao Alembic que compare o resultado com os modelos. Se sobrar qualquer
diferença, o teste falha e diz o comando que gera a migração faltante.

Ele também confere que o `downgrade` desmonta tudo e que os tipos nativos do
PostgreSQL foram mesmo usados — 172 colunas `uuid` e 28 `jsonb` na estrutura
atual.

Sem esse teste, o roteiro conhecido é: alguém acrescenta um campo ao modelo,
esquece a migração, a suíte passa (SQLite cria as tabelas a partir do modelo),
e o erro só aparece em produção, na hora de gerar um documento.

## Subindo com Docker

```bash
docker compose up -d                                  # banco + API
docker compose run --rm api python -m app.seeds --demo
```

O compose já aplica as migrações ao subir a API, e só a inicia depois que o
`pg_isready` do banco responde.

## Estrutura atual

51 tabelas de domínio. Os agrupamentos:

- **Identidade e acesso** — clientes, usuarios, perfis, usuario_perfis
- **Entidade** — entidades, naturezas_juridicas
- **Estatuto** — estatutos, estatuto_versoes, estatuto_parametros
- **Governança** — orgaos, cargos, mandatos, mandato_membros, associados
- **Atos** — eventos, assembleias, convocacoes, listas_presenca, deliberacoes,
  pareceres_juridicos
- **Documentos** — templates, documentos, documento_versoes, assinaturas,
  certidoes
- **Registral** — rcpj, regras_rcpj, protocolos, checklists, checklist_itens
- **Normativo** — fontes_juridicas, fonte_versoes, dispositivos,
  vinculos_normativos, monitoramentos_normativos, atualizacoes_normativas,
  impactos_normativos
- **Prazos** — prazos, pendencias, notificacoes
- **Indicadores** — configuracoes_score, score_snapshots, linha_tempo
- **Igrejas** — unidades_eclesiasticas, modelos_governanca_eclesiastica,
  ministros
- **IA** — analises_ia, sugestoes_ia
- **Auditoria** — logs, auditoria
