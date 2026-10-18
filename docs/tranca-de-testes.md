# Tranca do ambiente de testes

Enquanto o sistema está publicado mas ainda não é para ser visto, uma senha
única fecha o painel inteiro — antes da tela de login, antes de qualquer
página.

## Ligar

No Render, em **terceiro360-painel → Environment → Add Environment Variable**:

| Key | Value |
|---|---|
| `T360_SENHA_SITE` | a senha que você escolher |

Salve. O Render reinicia o serviço sozinho, em cerca de um minuto.

Ao abrir o site, o navegador pede usuário e senha numa caixa própria dele.
**O usuário pode ser qualquer coisa** — só a senha é conferida. Pedir um nome
que ninguém definiu geraria dúvida na hora de digitar.

O navegador guarda a credencial enquanto a aba estiver aberta; não é pedida a
cada página.

## Desligar

Apague a variável. Sem ela — ou com ela vazia — não há tranca.

## O que ela protege, e o que não protege

**Protege:** impede que quem descubra o endereço chegue ao formulário de login
e comece a tentar senhas. É uma porta a mais, antes da sua.

**Não protege:** não é cifrada ponta a ponta nem resistente a força bruta como
o login do sistema (que trava após cinco erros). É uma tranca de obra, não um
cofre. Ela existe para reduzir exposição durante o teste, não para substituir
a senha de usuário nem o segundo fator.

**Não alcança a API.** `terceiro360-api` continua pública, e isso é correto:
todo endereço dela exige token, exceto `/saude`, que não revela nada. A
documentação interativa (`/docs`, `/redoc`, `/openapi.json`) já fica desligada
em produção.

## Por que não está no render.yaml

É medida temporária. Variável declarada em arquivo versionado tende a
sobreviver ao motivo que a criou — e uma tranca esquecida no ar vira uma
senha a mais para o cliente perguntar por quê. Ligar e desligar à mão deixa a
decisão visível.

## Detalhe de implementação

Vive em `frontend/src/middleware.ts`, que roda antes de toda requisição. A
comparação da senha é feita em tempo constante: um `===` de string pararia no
primeiro caractere diferente, e essa diferença de tempo, repetida muitas
vezes através da rede, permite descobrir a senha caractere a caractere.

A senha é lida do ambiente a cada requisição, não numa constante de módulo.
Isso foi verificado construindo a imagem **sem** a variável e executando-a
**com** ela — que é exatamente como o Render funciona: constrói primeiro,
injeta as variáveis depois. Quatro cenários conferidos: sem credencial (401),
credencial errada (401), credencial certa (200), e variável ausente ou vazia
(sem tranca).
