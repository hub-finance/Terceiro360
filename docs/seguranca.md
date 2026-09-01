# Segurança

Duas perguntas diferentes costumam vir juntas: *o sistema pode ser copiado?* e
*o sistema pode ser invadido?* Elas se defendem de formas distintas.

## Contra cópia

O sistema é SaaS: o cliente nunca recebe o código, só o endereço. O que protege
o produto é o repositório ser privado e o acesso ser controlado — não há
recurso técnico dentro da aplicação que impeça cópia, porque o código nunca sai
do servidor.

O que **não** protege: ofuscar código, ou embutir licença no binário. Quem tem
acesso ao repositório tem o produto; quem não tem, tem só a tela.

## Contra invasão — o que já existe

| Camada | Como |
|---|---|
| Senha | bcrypt com sal aleatório. A senha não é guardada nem é reversível. |
| Sessão | JWT assinado (HS256), validade de 8h, em cookie `httpOnly` + `SameSite` — o JavaScript da página não alcança o token, o que o tira do alcance de XSS. |
| Força bruta | 5 tentativas falhas em 15 minutos travam o login, contadas por e-mail **e** por IP. Contar só por e-mail deixa passar varredura de muitas contas; só por IP deixa passar ataque distribuído contra uma conta. |
| Isolamento entre clientes | Toda consulta é filtrada por `cliente_id`; pedir o identificador de outro escritório direto na URL devolve 404, mesmo para administrador pleno do próprio. |
| Permissões | 11 perfis com permissão por recurso e ação; atos que exigem responsável habilitado conferem registro profissional. |
| Injeção de SQL | Nenhuma consulta é montada com texto: tudo passa por SQLAlchemy com parâmetros. |
| XSS | React escapa por padrão. O único ponto que renderiza HTML é o teor do documento, e ali o texto é escapado antes de a lacuna ser marcada. |
| Rastro | Toda tentativa de login — inclusive negada e bloqueada — vai para `logs`, com IP e navegador. Alterações vão para `auditoria`, com antes, depois, autor e motivo. |
| Configuração | Em produção o sistema **se recusa a subir** com chave de assinatura ou de cifragem padrão, com chave curta, ou com `DEBUG` ligado. |
| CORS | Lista fechada de origens. Nunca `*`, que com credenciais permitiria a qualquer site agir como o usuário logado. |
| Segundo fator | TOTP, com códigos de recuperação de uso único. Só é ativado depois que a pessoa prova que consegue ler um código — ativar antes trancaria quem errou a leitura do QR para fora da própria conta. O QR é desenhado no nosso servidor: mandar a URI para um gerador de terceiros seria entregar o segredo a outra empresa. |
| Política de senha | Mínimo de 12 caracteres, sem previsíveis, sem sequência de teclado, sem conter nome ou e-mail. Sem exigir símbolo: obrigar composição produz `Senha@123`, e é o comprimento que protege (NIST SP 800-63B). |
| Dado pessoal em repouso | CPF e RG cifrados em coluna (Fernet). A busca continua funcionando por um índice cego — HMAC-SHA256 com chave, não SHA simples, que cairia por força bruta em minutos. |
| Cabeçalhos | CSP com nonce por requisição, HSTS, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, nos dois servidores. |
| Freio de requisições | Teto por IP por minuto em toda a API, além do freio próprio do login. |
| `/docs` | Fechado em produção: é o mapa completo da API servido de graça. |

Cada linha dessa tabela tem teste correspondente em `tests/test_seguranca.py`,
escrito como tentativa de ataque — token forjado com outra chave, token
expirado, força bruta, e um administrador de um escritório tentando ler a
entidade de outro.

## Sobre a CSP com nonce

Vale registrar por que ela não ficou no `next.config.ts`, que seria o lugar
óbvio: `script-src 'self'` sozinho **bloqueia o próprio Next**, que injeta
script inline para hidratar a página. O efeito é traiçoeiro — a tela renderiza
normalmente, o servidor não acusa nada, e simplesmente nenhum botão funciona.

A saída é um nonce diferente por resposta, e nonce por resposta não cabe numa
configuração estática. Por isso a política é montada em `src/middleware.ts`, que
gera o nonce, o repassa no cabeçalho da requisição (o Next o aplica sozinho aos
seus scripts) e o devolve na resposta.

`'strict-dynamic'` completa: o script já autorizado pode carregar os seus
próprios pedaços, sem precisar listar cada arquivo gerado pelo build.

## O que ainda falta

1. **Backup testado** — o roteiro está em [`publicacao.md`](publicacao.md), mas
   backup que nunca foi restaurado não é backup. É tarefa de quem publica.
2. **Rotação de chave de cifragem** — hoje trocar a `T360_CHAVE_DADOS` exige
   migração manual. Falta o comando que recifra a base com a chave nova.
3. **Freio distribuído** — o teto por IP vive na memória do processo; com
   várias réplicas, cada uma conta a sua parte. Para ataque sério, o freio
   precisa estar na CDN ou no proxy reverso, antes da aplicação.
4. **Verificação contra bases de vazamento** — a lista de senhas previsíveis é
   curta de propósito; o passo seguinte é consultar uma base pública.
5. **Expiração de sessão por inatividade** — hoje o token vale 8 horas fixas.
6. **Alerta de acesso incomum** — o rastro existe em `logs`, mas ninguém é
   avisado quando aparece um login de origem nova.

## LGPD

O sistema guarda dado pessoal: nome, CPF, RG, endereço e data de nascimento de
dirigentes e associados. A tabela de pessoas já traz campo de base legal do
tratamento e de consentimento, e há trilha de auditoria e prazo de retenção de
log configurável (padrão: 5 anos).

Falta o que não é código: definir a base legal de cada tratamento, publicar
política de privacidade e nomear encarregado.
