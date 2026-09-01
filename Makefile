# TERCEIRO360 — atalhos de desenvolvimento.
PY := backend/.venv/bin/python
PG_TESTE ?= postgresql+psycopg://postgres@127.0.0.1:55432/terceiro360_teste

.PHONY: ajuda instalar migrar migracao carga rodar varrer teste teste-pg verificar limpar

ajuda:
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "};{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

instalar: ## Cria o ambiente e instala as dependências
	cd backend && uv venv .venv && uv pip install --python .venv/bin/python -e ".[dev]"

migrar: ## Aplica as migrações pendentes
	cd backend && .venv/bin/alembic upgrade head

migracao: ## Gera uma migração a partir do modelo (make migracao m="o que mudou")
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(m)"

carga: ## Carrega perfis, base normativa e modelos (use demo=1 para dados de exemplo)
	cd backend && .venv/bin/python -m app.seeds $(if $(demo),--demo,)

rodar: ## Sobe a API em modo de desenvolvimento
	cd backend && .venv/bin/uvicorn app.main:app --reload

varrer: ## Roda o agendador uma vez (make varrer t=tudo|vigilias|prazos)
	cd backend && .venv/bin/python -m app.agendador $(or $(t),tudo)

teste: ## Roda a suíte em SQLite (rápido)
	cd backend && .venv/bin/python -m pytest tests -q

teste-pg: ## Roda a suíte em PostgreSQL (antes de publicar)
	cd backend && T360_TEST_DATABASE_URL=$(PG_TESTE) .venv/bin/python -m pytest tests -q

verificar: teste teste-pg ## Roda tudo nos dois bancos

limpar: ## Remove artefatos locais
	find backend -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.pytest_cache backend/*.db
