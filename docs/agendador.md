# Agendador — vigílias e prazos

O sistema não pode depender de alguém lembrar de olhar. Mandato vence sozinho,
certidão caduca sozinha e lei muda sozinha; quem não varre periodicamente
descobre tarde — às vezes depois de praticar um ato com diretoria vencida.

Duas varreduras cobrem isso:

| Tarefa | O que faz | Frequência sugerida |
|---|---|---|
| `vigilias` | Confere nas fontes oficiais as normas cuja periodicidade venceu; abre triagem quando o texto mudou e cobra o responsável quando a fonte é de conferência manual | diária |
| `prazos` | Recalcula a agenda de cada entidade, materializa os prazos e dispara os alertas de janela (90/60/30/15/7/3/1 dias) | diária |

## Como rodar

Ele é um **comando**, não um processo residente:

```bash
python -m app.agendador tudo        # as duas, na ordem
python -m app.agendador vigilias
python -m app.agendador prazos --json
```

Ou, em desenvolvimento: `make varrer` (ou `make varrer t=prazos`).

A escolha por comando é deliberada: o disparador fica com quem opera — cron,
systemd timer, Cloud Scheduler, Kubernetes CronJob, GitHub Actions — e não há
mais um processo para monitorar. Sai com código **1** quando a rodada teve
falhas, então o supervisor percebe sem ler log.

```cron
# Todo dia às 6h, com o log indo para onde a operação já olha.
0 6 * * *  cd /app && python -m app.agendador tudo >> /var/log/terceiro360.log 2>&1
```

Também dá para disparar pela API — `POST /api/v1/agendador/executar/{tarefa}` —
ou pelo botão "Rodar varredura agora", nas telas de Prazos e de Pendências.
Serve para quando se sabe que uma lei acabou de mudar e não faz sentido esperar
até amanhã.

## Rodar duas vezes não duplica nada

Isso não é detalhe de implementação, é o que decide se alguém deixa o agendador
ligado:

- **Prazo** tem chave de idempotência derivada da sua origem; recalcular
  reaproveita a linha existente.
- **Alerta** guarda a janela já disparada. O aviso dos 30 dias sai uma vez; o
  dos 7 dias sai depois, porque é outro aviso, mais urgente.
- **Pendência** é procurada antes de ser aberta: uma conferência manual não
  resolvida vira uma pendência, não trinta por mês.
- **Prazo remarcado** (mandato prorrogado, certidão renovada) tem os alertas
  zerados: os que já saíram valiam para a data antiga.

## O que a rodada deixa registrado

Cada execução grava uma linha em `execucoes_agendador` — tarefa, início, fim,
resultado, contadores e falhas. Num sistema de conformidade, *"a vigília rodou
ontem?"* precisa ter resposta, e essa resposta não pode ser o log do servidor,
que ninguém guarda por anos.

O histórico aparece em **Pendências → Varreduras**, com o resultado de cada uma:

- `OK` — correu inteira;
- `PARCIAL` — correu, mas alguma fonte falhou (o site oficial fora do ar não
  derruba a verificação das outras trinta; o erro fica anotado);
- `ERRO` — abortou.

## Quem recebe o alerta

Com responsável definido no prazo, é dele o aviso. Sem responsável, avisa todos
os usuários ativos do cliente — um prazo sem dono é justamente o que não pode
passar em branco.

Hoje a notificação é interna (`/api/v1/notificacoes`). O modelo já prevê os
canais `EMAIL` e `WHATSAPP`; o envio externo é trabalho de outro bloco.
