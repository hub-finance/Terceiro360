"""As dependências declaradas batem com as que o código importa.

Este teste existe por causa de um defeito real: `httpx` foi usado na consulta
de CNPJ estando declarado apenas no extra `dev`. Em desenvolvimento tudo
passava — o pytest instala os extras. A imagem de produção roda
`pip install .` sem extras, e a API morria na partida, num import, antes de
qualquer log útil.

É a classe de erro que nenhum teste de comportamento pega, porque no ambiente
onde os testes rodam a biblioteca está sempre lá.
"""
from __future__ import annotations

import ast
import pathlib
import sys
import tomllib
from importlib.metadata import packages_distributions

RAIZ = pathlib.Path(__file__).resolve().parent.parent
APP = RAIZ / "app"


def _modulos_importados() -> set[str]:
    """Todo módulo de topo importado por `app/`, sem os da própria aplicação."""
    modulos: set[str] = set()
    for arquivo in APP.rglob("*.py"):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                modulos.update(alias.name.split(".")[0] for alias in no.names)
            elif isinstance(no, ast.ImportFrom):
                if no.level:  # import relativo: é da própria aplicação
                    continue
                if no.module:
                    modulos.add(no.module.split(".")[0])
    return modulos


def _declaradas() -> set[str]:
    dados = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    projeto = dados["project"]
    nomes = set()
    for linha in projeto.get("dependencies", []):
        # "psycopg[binary]>=3.2" -> "psycopg"
        nome = linha.split(">")[0].split("<")[0].split("=")[0].split("[")[0].strip()
        nomes.add(nome.lower().replace("_", "-"))
    return nomes


def test_todo_import_de_terceiro_esta_declarado():
    distribuicoes = packages_distributions()
    declaradas = _declaradas()
    faltando: dict[str, str] = {}

    for modulo in sorted(_modulos_importados()):
        if modulo == "app" or modulo in sys.stdlib_module_names:
            continue
        for dist in distribuicoes.get(modulo, []):
            if dist.lower().replace("_", "-") not in declaradas:
                faltando[modulo] = dist

    assert not faltando, (
        "Módulos importados por app/ cujo pacote não está em "
        "[project].dependencies do pyproject.toml — a imagem de produção "
        f"não vai tê-los: {faltando}"
    )
