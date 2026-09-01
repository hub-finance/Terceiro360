# Rodar o TERCEIRO360 no seu Windows

Guia para quem não é programador. São quatro passos; o primeiro é o único
demorado, e só se faz uma vez.

> **Por que `localhost:3000` deu "conexão recusada"?**
> `localhost` quer dizer "este computador". O endereço procura o sistema na sua
> máquina — e ele ainda não está lá. Os passos abaixo o colocam lá.

---

## Passo 1 — Instalar o Docker Desktop (uma vez só)

O Docker é o que faz o sistema inteiro (banco de dados, servidor, painel) subir
com um comando, sem você instalar cada peça separadamente.

1. Baixe em **https://www.docker.com/products/docker-desktop/** → *Download for
   Windows*.
2. Execute o instalador. Deixe marcada a opção **"Use WSL 2"**.
3. **Reinicie o computador** quando ele pedir. Não pule: sem reiniciar, o
   Docker abre e fica travado em "starting".
4. Abra o Docker Desktop e espere o ícone da baleia, no canto inferior
   esquerdo, ficar **verde**. Na primeira vez ele demora uns minutos.

**Se aparecer erro de virtualização:** significa que a virtualização está
desligada na BIOS do computador. É comum em máquina de escritório. Procure
*"ativar virtualização BIOS"* junto com a marca do seu computador — costuma ser
uma tecla (F2, F10 ou Del) durante a inicialização, e uma opção chamada
*Intel VT-x*, *AMD-V* ou *SVM Mode*.

---

## Passo 2 — Baixar o sistema

O repositório é público, então não precisa de senha nem de instalar o Git.

1. Abra **https://github.com/hub-finance/Terceiro360**
2. Botão verde **Code** → **Download ZIP**
3. Salve em algum lugar fácil e **extraia** — por exemplo, para
   `C:\terceiro360`

Depois de extrair você deve ver, dentro da pasta, os itens `backend`,
`frontend`, `docs` e o arquivo `docker-compose.yml`. Se em vez disso houver
uma única pasta dentro da pasta, entre nela — é essa que interessa.

---

## Passo 3 — Ligar o sistema

1. Abra a pasta no Explorador de Arquivos.
2. Clique na barra de endereço (onde está o caminho), apague, escreva
   `powershell` e tecle **Enter**. Abre um terminal já na pasta certa.
3. Cole o primeiro comando e tecle Enter:

```powershell
docker compose up -d --build
```

A primeira vez demora — ele está montando tudo. Pode passar de **10 minutos**,
e é normal ver muito texto rolando. Espere terminar e voltar o cursor.

4. Depois cole o segundo, que carrega os dados de demonstração:

```powershell
docker compose run --rm api python -m app.seeds --demo
```

---

## Passo 4 — Entrar

Abra o navegador em **http://localhost:3000**

- **Usuário:** `admin@demo.terceiro360.local`
- **Senha:** `terceiro360`

Você entra numa associação de demonstração já com estatuto cadastrado,
diretoria, 40 associados e documentos gerados, para explorar sem medo de
estragar nada.

---

## No dia seguinte

Não repita a instalação. Basta:

- **Ligar:** abra o Docker Desktop, espere ficar verde, e no PowerShell da
  pasta rode `docker compose up -d`
- **Desligar:** `docker compose down`
- **Apagar tudo e recomeçar do zero:** `docker compose down -v` (o `-v` apaga o
  banco junto — some tudo o que você tiver cadastrado)

---

## Quando der errado

| O que aparece | O que é | O que fazer |
|---|---|---|
| `docker : O termo 'docker' não é reconhecido` | O Docker não está instalado, ou o PowerShell foi aberto antes da instalação | Feche o PowerShell, confirme que o Docker Desktop está aberto e verde, abra o PowerShell de novo |
| `error during connect... docker_engine` | O Docker Desktop não terminou de iniciar | Espere a baleia ficar verde e repita o comando |
| `port is already allocated` na porta 3000 | Outro programa já usa essa porta | Feche o outro programa, ou peça que eu troque a porta do painel |
| `port is already allocated` na porta 5432 | Você já tem PostgreSQL instalado na máquina | Pare o serviço do PostgreSQL, ou me peça para trocar a porta do banco |
| A página abre mas fica em branco | O painel subiu antes da API | Rode `docker compose restart painel` e recarregue |
| `no such service: api` | O PowerShell não está na pasta certa | Confira se o `docker-compose.yml` está na pasta onde o terminal está — `dir` lista os arquivos |

Se aparecer algo que não está nesta tabela, copie a mensagem inteira e me
mande. É mais rápido do que descrever.

---

## Ver o que está acontecendo por dentro

```powershell
docker compose ps        # o que está no ar
docker compose logs api  # o que a API está dizendo
```

E, se quiser rodar a varredura de prazos e de mudanças na lei sem esperar o
horário:

```powershell
docker compose run --rm api python -m app.agendador tudo
```
