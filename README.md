# TERCEIRO360

**Inteligência e automação para o Terceiro Setor.**

ERP jurídico-societário para associações, fundações, OSCs, OSCIPs, institutos,
igrejas e organizações religiosas. O sistema não gera documentos: ele
**cadastra → analisa → parametriza → valida → alerta → gera → revisa → assina →
protocola → arquiva → controla prazos**.

## Módulos

| Módulo | O que faz |
|---|---|
| **TERCEIRO360 JURÍDICO** | Atos societários, estatutos, assembleias, atas e RCPJ |
| **TERCEIRO360 GOVERNANÇA** | Mandatos, órgãos, compliance e indicadores |
| **TERCEIRO360 DOCUMENTOS** | Gestão e geração documental com versionamento |
| **TERCEIRO360 IGREJAS** | Núcleo para igrejas e organizações religiosas |
| **TERCEIRO360 IA** | Análise de estatutos, documentos e conformidade |

**TERCEIRO360 CONTÁBIL** está especificado e reservado para fase posterior —
ver `docs/reservado/modulo-contabil.md`.

## As três regras que governam o sistema

**1. Nada é presumido.** Quando falta informação, o sistema responde
`DADO NÃO INFORMADO`. Quando há dúvida, `VALIDAÇÃO NECESSÁRIA`. Quando as
fontes se contradizem, `INCONSISTÊNCIA IDENTIFICADA`. Nunca um valor plausível
no lugar de um valor conferido.

**2. A lei federal não decide sozinha.** Toda validação resolve
`LEI + ESTATUTO + REGRA DO RCPJ COMPETENTE + DADOS DA ENTIDADE`, com a
procedência declarada em cada conclusão. Na maior parte dos temas — quórum,
prazo de convocação, duração de mandato — a lei devolve a definição ao
estatuto, e é o estatuto cadastrado que manda.

**3. A base legal envelhece, e o sistema sabe disso.** A Central de Fontes
mantém cada norma versionada por data de vigência, com vigilância periódica,
curadoria humana obrigatória para publicar e cálculo de impacto sobre as regras
e modelos que dependiam da redação antiga.

## Rodando

Com Docker — sobe o PostgreSQL, aplica as migrações e inicia a API:

```bash
docker compose up -d
docker compose run --rm api python -m app.seeds --demo
```

Sem Docker:

```bash
make instalar
cp backend/.env.example backend/.env      # ajuste T360_DATABASE_URL
make migrar && make carga demo=1
make rodar
```

Documentação da API em `http://localhost:8000/docs`.
Acesso de demonstração: `admin@demo.terceiro360.local` / `terceiro360`.

```bash
make teste        # 153 testes em SQLite, ~45s
make teste-pg     # 156 testes em PostgreSQL — rode antes de publicar
make varrer       # roda o agendador uma vez (vigílias + prazos)
```

- Banco e migrações: [`docs/banco-e-migracoes.md`](docs/banco-e-migracoes.md)
- Agendador — vigílias e alertas de prazo: [`docs/agendador.md`](docs/agendador.md)
- Exportação em DOCX e PDF: [`docs/exportacao.md`](docs/exportacao.md)
- Segurança e LGPD: [`docs/seguranca.md`](docs/seguranca.md)
- Publicação (Supabase + API + painel): [`docs/publicacao.md`](docs/publicacao.md)

## Arquitetura

```
Next.js (Vercel)
      ↓ HTTPS
FastAPI — API + motores + agendador
      ↓
PostgreSQL + Storage        ·        API de IA
```

```
backend/app/
├── core/        configuração, banco, tipos, segurança, permissões
├── engines/     os motores — puros, sem ORM, testáveis isoladamente
│   ├── conformidade/   resolve LEI + ESTATUTO + RCPJ; lê quórum em português
│   ├── validacao/      checks jurídicos, documentais e registrais + semáforo
│   ├── normativo/      vigilância, diff, curadoria e impacto de mudança legal
│   ├── templates/      documento inteligente com condicionais e lacunas
│   ├── checklist/  score/  prazos/  decisao/  inconsistencias/
├── modules/     domínio: identity, entidades, juridico, documentos,
│                registral, normativo, prazos, governanca, igrejas, ia,
│                compliance
├── api/rotas/   88 operações REST
└── seeds/       base normativa, modelos de documento, dados de demonstração
```

Os motores não conhecem o banco: recebem estruturas simples e devolvem achados
com fundamentação. É o que permite testá-los sem subir infraestrutura e
reaproveitá-los fora da API.

## Responsabilidade profissional

A automação auxilia na preparação, organização, validação e geração de
documentos, **mas não substitui a análise profissional** quando esta for
necessária. Atos de risco jurídico elevado passam obrigatoriamente por revisão.
