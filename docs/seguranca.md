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
| Configuração | Em produção o sistema **se recusa a subir** com a chave de assinatura padrão, com chave curta, ou com `DEBUG` ligado. |
| CORS | Lista fechada de origens. Nunca `*`, que com credenciais permitiria a qualquer site agir como o usuário logado. |

Cada linha dessa tabela tem teste correspondente em `tests/test_seguranca.py`,
escrito como tentativa de ataque — token forjado com outra chave, token
expirado, força bruta, e um administrador de um escritório tentando ler a
entidade de outro.

## O que ainda falta

Nada disso impede o uso interno, mas deve entrar antes de cliente pagante:

1. **HTTPS obrigatório e HSTS** — depende da publicação; hoje é http local.
2. **MFA** — o campo existe no modelo de usuário, a verificação não.
3. **Política de senha** — não há mínimo de força nem troca periódica.
4. **Limite de requisições geral** — o freio hoje cobre só o login.
5. **Cabeçalhos de resposta** — CSP, `X-Frame-Options`, `X-Content-Type-Options`.
6. **`/docs` e `/openapi.json` abertos** — convém fechar em produção.
7. **Backup testado** — backup que nunca foi restaurado não é backup.
8. **Criptografia de CPF em repouso** — hoje o dado pessoal está protegido pelo
   banco, não em coluna cifrada.

## LGPD

O sistema guarda dado pessoal: nome, CPF, RG, endereço e data de nascimento de
dirigentes e associados. A tabela de pessoas já traz campo de base legal do
tratamento e de consentimento, e há trilha de auditoria e prazo de retenção de
log configurável (padrão: 5 anos).

Falta o que não é código: definir a base legal de cada tratamento, publicar
política de privacidade e nomear encarregado.
