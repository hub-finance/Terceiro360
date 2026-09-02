# Do sistema que funciona ao produto que se vende

O sistema está no ar e faz o que promete. Isso não é o mesmo que estar pronto
para cobrar por ele. Este documento separa as duas coisas e diz, na ordem, o
que falta.

A separação importa porque as pendências são de naturezas diferentes: algumas
são código, outras são dinheiro, outras são assinatura de profissional
habilitado. Só as primeiras dependem de programação.

---

## Fase 0 — O que impede vender hoje

Nenhum destes itens é opcional. Enquanto qualquer um estiver aberto, vender é
assumir um risco que não é do cliente, é seu.

### 0.1 Curadoria da base normativa por profissional inscrito na OAB

A base legal foi montada a partir da legislação, com fonte e dispositivo
citados em cada regra. **Ela não foi conferida por advogado.** Enquanto não
for, o sistema é uma ferramenta de apoio interno, não um produto que outro
escritório possa usar confiando no resultado.

O que precisa acontecer: um profissional habilitado percorre a Central de
Fontes, confere cada dispositivo e cada regra de validação, e assina essa
conferência. O sistema já registra quem confirmou o quê e quando — a estrutura
existe, falta a pessoa.

**Não é tarefa de programação.** É o item de maior risco e o de caminho
crítico mais longo.

### 0.2 Contratos e documentos jurídicos do próprio negócio

Para cobrar de alguém você precisa de:

- **Contrato de licença de uso** — o que o cliente pode fazer, por quanto
  tempo, o que acontece se parar de pagar, e o que ele leva embora ao sair.
- **Termos de uso** e **Política de privacidade** — obrigatórios, e não é
  modelo copiado da internet: o sistema trata dado pessoal sensível (CPF, RG,
  endereço de dirigentes).
- **Definição de responsabilidade técnica** — deixar escrito, em linguagem
  que sobreviva a uma discussão judicial, que a automação prepara e valida mas
  não substitui a análise profissional. Essa frase já está no rodapé do
  sistema; ela precisa estar também no contrato.
- **Encarregado de dados (LGPD, art. 41)** — pessoa nomeada, com canal de
  contato publicado.

### 0.3 Sair dos planos gratuitos

Os planos gratuitos de hoje têm duas limitações incompatíveis com cliente
pagante: os serviços dormem sem uso (até 50 segundos para acordar) e as cópias
de segurança são limitadas.

| Item | Custo aproximado |
|---|---|
| Render — dois serviços pagos | US$ 14/mês |
| Supabase Pro — cópias diárias e restauração a um ponto no tempo | US$ 25/mês |
| Domínio próprio (.com.br) | R$ 40/ano |

Cerca de **R$ 220/mês**. Isso atende os primeiros clientes com folga.

### 0.4 Restauração testada

Ter cópia de segurança não é o mesmo que conseguir restaurar. Antes do
primeiro cliente: derrubar um banco de teste, restaurar da cópia, e cronometrar
quanto tempo levou. O número que sai desse teste é o que se promete em
contrato — nunca um número estimado.

### 0.5 Teste de invasão independente

Contratar alguém para tentar invadir e relatar por onde conseguiu. Custa entre
R$ 5.000 e R$ 15.000 no Brasil para um sistema deste porte. O relatório é
também argumento comercial: escritório que cuida de dado de terceiro pergunta
sobre isso.

---

## Fase 1 — O que o produto ainda não faz

Estas são lacunas de produto. Não impedem vender para um primeiro cliente
próximo, mas impedem vender em escala.

### 1.1 Importar documentos existentes

*(Sugestão levantada durante o desenvolvimento — e é a de melhor relação entre
esforço e valor de toda esta lista.)*

Hoje o estatuto é cadastrado campo a campo: alguém lê o documento e transcreve
mandato, quórum e prazo de convocação. Para um escritório com trinta entidades,
isso é trinta transcrições antes de o sistema servir para alguma coisa. **É a
maior barreira de entrada do produto.**

O que construir, em três degraus:

1. **Anexar o arquivo** — subir o PDF ou DOCX do estatuto e da ata, e guardá-lo
   junto da entidade. Já resolve a metade do problema: o documento deixa de
   viver numa pasta solta e passa a ter dono, data e versão.
2. **Extrair o texto** — ler o conteúdo do arquivo e apresentá-lo lado a lado
   com os campos, para conferência humana. Sem inteligência artificial: só
   leitura, com o trecho relevante destacado.
3. **Sugerir os valores** — o sistema propõe "mandato: 2 anos", mostrando o
   trecho de onde tirou, e **a pessoa confirma**. Nunca preenche sozinho.

O degrau 3 é onde a IA entra, e a regra do sistema continua valendo: sugestão
com fonte à vista, confirmação humana obrigatória. Já existe estrutura para
isso — cada parâmetro do estatuto tem um campo `confirmado` e um campo de
dispositivo de origem. A extração encaixa exatamente ali.

Estimativa: degrau 1, poucos dias. Degraus 2 e 3, algumas semanas.

### 1.2 Telas que faltam

Aparecem no menu como "em breve", de propósito — esconder o roteiro confunde
mais do que ajuda:

- **Modelos** — editar os modelos de documento sem depender de programador.
- **Governança** — o painel de conformidade da entidade.
- **IA jurídica** — consulta em linguagem natural sobre a base normativa.

### 1.3 Autoatendimento

Hoje um cliente novo precisa ser cadastrado por alguém com acesso ao banco.
Para vender além dos primeiros clientes é preciso: cadastro pela própria
página, cobrança recorrente automática (Stripe, Asaas ou similar), controle
de plano e limite, e cancelamento sem intervenção humana.

Enquanto forem poucos clientes, cadastrar na mão é perfeitamente aceitável —
e evita construir cobrança antes de saber qual é o preço certo.

---

## Fase 2 — Operação

O que precisa existir no dia em que houver cliente pagante:

- **Canal de suporte** com prazo de resposta declarado. Um e-mail que alguém
  realmente lê já basta no começo.
- **Aviso automático quando o sistema cair.** Hoje ninguém é avisado: o
  primeiro a descobrir seria o cliente.
- **Registro de versões** — o que mudou a cada atualização, em linguagem de
  usuário.
- **Ambiente de homologação** separado da produção, para testar antes de
  publicar.

---

## Fase 3 — Comercial

### Posicionamento

O sistema não compete com gerador de documento. O que ele faz de diferente é
**conferir antes de gerar** e **dizer o que impede, com a fonte**. Esse é o
argumento, e ele fala com quem já teve documento devolvido pelo cartório.

O público mais próximo não é a entidade pequena — é o **escritório de
contabilidade ou advocacia que atende várias entidades**, porque a dor dele é
proporcional ao número de clientes.

### Preço

Duas perguntas a responder antes de definir valor:

1. Quanto custa hoje, ao cliente, um documento devolvido pelo cartório —
   retrabalho, nova assembleia, prazo perdido?
2. Quanto tempo um profissional gasta redigindo uma ata de eleição e posse?

O preço se ancora na resposta, não no custo de infraestrutura. O custo de
infraestrutura (R$ 220/mês) só diz qual é o piso.

### Primeiros clientes

Três a cinco escritórios conhecidos, com desconto explícito de piloto, em
troca de retorno formal. Piloto não é caridade: é a única forma de descobrir o
que falta antes de descobrir com quem pagou preço cheio.

---

## Resumo da ordem

| Ordem | O que | Depende de |
|---|---|---|
| 1 | Curadoria da base por advogado | Profissional habilitado |
| 2 | Contratos, termos, política de privacidade | Advogado |
| 3 | Sair do plano gratuito | ~R$ 220/mês |
| 4 | Testar restauração de cópia | Algumas horas |
| 5 | Importar documentos (degrau 1) | Programação |
| 6 | Teste de invasão | R$ 5–15 mil |
| 7 | Pilotos com desconto | Rede de contato |
| 8 | Cobrança automática | Programação, depois dos pilotos |

Os itens 1 e 2 são o caminho crítico e **não dependem de programação**. Vale
começá-los agora, em paralelo com o resto.
