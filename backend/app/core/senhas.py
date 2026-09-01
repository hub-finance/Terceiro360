"""Política de senha (§31).

A regra aqui não é "complexidade" no sentido antigo — obrigar maiúscula,
número e símbolo produz `Senha@123`, que qualquer lista de senhas comuns quebra
em segundos. O que realmente protege é **comprimento** e **não ser previsível**.
É também a recomendação atual do NIST (SP 800-63B), que abandonou a exigência
de composição e a troca periódica obrigatória.
"""
from __future__ import annotations

import re
import unicodedata

COMPRIMENTO_MINIMO = 12
COMPRIMENTO_MAXIMO = 128  # bcrypt trunca em 72 bytes; barrar antes evita surpresa

# Um punhado de senhas que aparecem em qualquer vazamento, mais as previsíveis
# neste domínio. Lista curta de propósito: ela existe para pegar o caso óbvio,
# não para substituir uma verificação contra base de vazamentos.
PREVISIVEIS = {
    "123456", "1234567890", "123456789012", "senha123456", "password123",
    "qwertyuiop", "abcdabcdabcd", "terceiro360", "terceirosetor",
    "associacao123", "administrador", "mudar123456", "12345678",
}


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


def problemas(senha: str, email: str | None = None, nome: str | None = None) -> list[str]:
    """Devolve o que há de errado com a senha. Lista vazia = aceita.

    Devolve **todos** os problemas de uma vez: corrigir um por vez, descobrindo
    o seguinte a cada tentativa, é o tipo de atrito que faz a pessoa escolher a
    senha mais fraca que passar.
    """
    achados: list[str] = []
    limpa = senha.strip()

    if len(limpa) < COMPRIMENTO_MINIMO:
        achados.append(
            f"Use pelo menos {COMPRIMENTO_MINIMO} caracteres — comprimento protege "
            f"muito mais do que símbolo no meio."
        )
    if len(limpa.encode("utf-8")) > COMPRIMENTO_MAXIMO:
        achados.append(f"Senha longa demais (máximo {COMPRIMENTO_MAXIMO} caracteres).")

    normal = _normalizar(limpa)
    if normal in PREVISIVEIS:
        achados.append("Esta senha está entre as mais usadas do mundo. Escolha outra.")

    if len(set(normal)) <= 4 and len(normal) >= 8:
        achados.append("Poucos caracteres diferentes: repetição não acrescenta segurança.")

    if re.search(r"(012345|123456|abcdef|qwerty|asdfgh)", normal):
        achados.append("Evite sequências do teclado ou de números.")

    for dado, rotulo in ((email, "seu e-mail"), (nome, "seu nome")):
        if not dado:
            continue
        for pedaco in re.split(r"[^a-z0-9]+", _normalizar(dado)):
            if len(pedaco) >= 4 and pedaco in normal:
                achados.append(f"A senha não pode conter {rotulo}.")
                break

    return achados


def validar(senha: str, email: str | None = None, nome: str | None = None) -> None:
    """Levanta ValueError com todos os problemas juntos."""
    achados = problemas(senha, email, nome)
    if achados:
        raise ValueError(" ".join(achados))
