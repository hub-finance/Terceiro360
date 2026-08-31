"""Carga inicial: `python -m app.seeds [--demo]`."""
from __future__ import annotations

import sys

from app.core.db import Base, SessionLocal, engine
from app.models import Base as ModelosBase  # noqa: F401  (registra os mapeamentos)
from app.seeds.carga import popular


def main() -> None:
    com_demo = "--demo" in sys.argv
    print("Criando as tabelas que ainda não existem…")
    ModelosBase.metadata.create_all(engine)

    with SessionLocal() as db:
        resumo = popular(db, com_demonstracao=com_demo)

    print("\nCarga concluída:")
    for chave, valor in resumo.items():
        print(f"  {chave}: {valor}")

    if com_demo and isinstance(resumo.get("demonstracao"), dict):
        demo = resumo["demonstracao"]
        if "usuario" in demo:
            print(f"\n  Acesso de demonstração: {demo['usuario']} / {demo['senha']}")
            print("  Troque essa senha antes de expor o ambiente.")


if __name__ == "__main__":
    main()
