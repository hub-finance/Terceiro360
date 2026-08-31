# TERCEIRO360 CONTÁBIL — especificação reservada

> **Situação:** fora do escopo ativo por decisão de produto. Especificação
> preservada aqui para retomada em fase posterior, sem retrabalho.

O que **permaneceu** no escopo ativo: os atos societários de prestação de
contas — assembleia de aprovação, parecer do Conselho Fiscal, ata e
arquivamento — vivem no módulo JURÍDICO, porque são atos de assembleia, não
escrituração.

O que ficou **reservado**: a contabilidade propriamente dita.

## Modelo de dados previsto

| Tabela | Conteúdo |
|---|---|
| `exercicios` | ano, data de início e fim, situação (aberto/encerrado/aprovado) |
| `plano_contas` | código, descrição, tipo, natureza, conta-pai, aceita lançamento |
| `lancamentos` | data, histórico, documento, valor, projeto, centro de custo |
| `lancamento_partidas` | conta, D/C, valor — dupla partida real, não campo único |
| `projetos` | fonte de recurso, convênio, recurso vinculado, vigência |
| `centros_custo` | estrutura de rateio |
| `prestacoes_contas` | exercício, situação, parecer, evento de aprovação |
| `patrimonio` / `imobilizado` | bens, depreciação, doações recebidas |

## Funcionalidades previstas

- Escrituração com dupla partida e fechamento de exercício.
- Balancete, Balanço Patrimonial, DRE, DFC e DMPL quando aplicável.
- Segregação de recursos vinculados (convênios, subvenções, doações com
  destinação específica) — o ponto que mais gera glosa em prestação de contas.
- Relatórios por projeto e por centro de custo.
- Prestação de contas: exercício → documentos → relatórios → parecer →
  assembleia → ata → aprovação → arquivamento.

## Integrações com o que já existe

1. O **motor de prazos** já prevê `PRESTACAO_CONTAS`: hoje ele cobra o prazo
   estatutário; com o módulo contábil, passa a cobrar também o fechamento.
2. O **checklist** do ato de aprovação de contas já exige demonstrações e
   parecer do Conselho Fiscal — hoje como documentos anexados, no futuro
   gerados pelo próprio módulo.
3. O **score de governança** tem o critério `PRESTACAO_CONTAS` com peso 12,
   hoje alimentado por evento; passaria a ser alimentado pelo exercício.

## Base normativa a acrescentar na Central de Fontes

- ITG 2002 (R1) — Entidade sem Finalidade de Lucros (CFC)
- NBC TG 1000 e demais normas do CFC aplicáveis
- Lei nº 13.019/2014, art. 33 — escrituração exigida para parcerias
- Regras da Receita Federal quanto a obrigações acessórias

## Plano comercial

O plano CONTÁBIL do §45 entra junto com este módulo.
