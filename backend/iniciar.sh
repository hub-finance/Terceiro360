#!/bin/sh
# Partida do servidor em produção.
#
# A migração roda aqui, na subida, e não num passo manual à parte: publicar
# código novo com o banco na versão antiga é uma das formas mais rápidas de
# derrubar um sistema. `set -e` garante que, se a migração falhar, o servidor
# não sobe — melhor ficar fora do ar do que atender com o banco errado.
set -e

echo "==> Aplicando migrações"
alembic upgrade head

# Carga inicial (perfis, base normativa, modelos de documento). É idempotente:
# rodar de novo atualiza o que mudou e não duplica nada. Fica atrás de uma
# variável porque só faz sentido na primeira subida de um ambiente novo.
if [ "${T360_CARGA_INICIAL}" = "true" ]; then
  echo "==> Carga inicial"
  python -m app.seeds
fi

echo "==> Subindo a API na porta ${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
