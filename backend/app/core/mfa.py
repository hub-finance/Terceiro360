"""Segundo fator por TOTP (§31).

Senha vaza — por reuso em outro site, por phishing, por anotação num papel. O
segundo fator é o que impede que uma senha vazada vire acesso ao cadastro de
associados de trinta entidades.

TOTP (o código de seis dígitos que troca a cada trinta segundos) foi escolhido
em vez de SMS: SMS é interceptável por troca de chip, custa por mensagem e
depende de operadora. TOTP funciona em qualquer autenticador gratuito, offline,
sem custo por uso.
"""
from __future__ import annotations

import secrets

import pyotp

from app.core.security import conferir_senha, hash_senha

EMISSOR = "TERCEIRO360"
# Uma janela para trás e uma para frente: relógio de celular costuma estar
# alguns segundos fora, e recusar por isso gera chamado de suporte sem fim.
TOLERANCIA_JANELAS = 1
QUANTIDADE_CODIGOS_RECUPERACAO = 8


def novo_segredo() -> str:
    return pyotp.random_base32()


def uri_de_provisionamento(segredo: str, email: str) -> str:
    """A URI que vira QR Code no aplicativo autenticador."""
    return pyotp.TOTP(segredo).provisioning_uri(name=email, issuer_name=EMISSOR)


def conferir_codigo(segredo: str | None, codigo: str) -> bool:
    if not segredo or not codigo:
        return False
    limpo = codigo.strip().replace(" ", "").replace("-", "")
    if not limpo.isdigit():
        return False
    return pyotp.TOTP(segredo).verify(limpo, valid_window=TOLERANCIA_JANELAS)


def gerar_codigos_recuperacao() -> tuple[list[str], list[str]]:
    """Devolve (códigos em claro para mostrar uma vez, hashes para guardar).

    Sem eles, perder o celular significa perder a conta — e o caminho de volta
    vira "peça para o administrador desligar seu MFA", que é exatamente a porta
    que o atacante usa por telefone.
    """
    claros = [
        f"{secrets.token_hex(2)}-{secrets.token_hex(2)}-{secrets.token_hex(2)}"
        for _ in range(QUANTIDADE_CODIGOS_RECUPERACAO)
    ]
    return claros, [hash_senha(c) for c in claros]


def consumir_codigo_recuperacao(codigo: str, hashes: list[str]) -> list[str] | None:
    """Confere e devolve a lista sem o código usado. `None` se não bateu.

    Código de recuperação vale uma vez só: reaproveitável, ele seria uma
    segunda senha permanente, escrita num papel.
    """
    limpo = codigo.strip().lower()
    for guardado in hashes:
        if conferir_senha(limpo, guardado):
            return [h for h in hashes if h != guardado]
    return None
