"""Cifragem de dado pessoal em repouso (§33, LGPD).

O banco já é cifrado em disco pelo provedor. Isso protege contra alguém levar
o disco embora — não protege contra o cenário realista: uma string de conexão
vazada, um backup baixado, um acesso administrativo indevido. Nesses casos o
banco entrega o CPF de todo mundo em texto puro.

O problema de cifrar o CPF é que ele precisa continuar servindo para **buscar**
e para garantir que não haja duplicata. Cifra normal muda a cada gravação, então
o mesmo CPF viraria dois valores diferentes e nenhuma busca funcionaria.

A saída é guardar duas coisas:

* **`cpf`** — o valor cifrado (Fernet: AES-128-CBC + HMAC), que só é lido para
  exibir. Cada gravação produz texto diferente, como tem de ser.
* **`cpf_indice`** — um HMAC-SHA256 do CPF normalizado, determinístico. Serve
  para procurar e para a chave única, e é de mão única: quem lê o banco não
  volta ao CPF a partir dele.

O HMAC usa chave secreta de propósito. Um SHA simples do CPF seria quebrável
por força bruta em minutos — são só 10^11 combinações, e existe lista pronta.
Com chave, sem a chave não há o que testar.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

_PREFIXO = "cif:"   # marca o que já está cifrado, para conviver com dado antigo


def _chave_fernet() -> Fernet:
    """Deriva a chave de cifragem da chave de dados do sistema.

    Derivar em vez de reaproveitar direto mantém a chave de cifragem separada
    da de assinatura de sessão, mesmo quando as duas nascem do mesmo segredo:
    trocar uma não invalida a outra por acidente.
    """
    material = hashlib.sha256(f"cifra-dado-pessoal:{settings.chave_dados}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(material))


def normalizar_documento(valor: str) -> str:
    """Só os dígitos: "123.456.789-00" e "12345678900" são o mesmo CPF."""
    return re.sub(r"\D", "", valor or "")


def indice(valor: str | None) -> str | None:
    """HMAC determinístico, para busca e unicidade."""
    digitos = normalizar_documento(valor or "")
    if not digitos:
        return None
    return hmac.new(
        settings.chave_dados.encode(), digitos.encode(), hashlib.sha256
    ).hexdigest()


def cifrar(valor: str | None) -> str | None:
    if valor is None or valor == "":
        return None
    if valor.startswith(_PREFIXO):
        return valor
    return _PREFIXO + _chave_fernet().encrypt(valor.encode()).decode()


def decifrar(valor: str | None) -> str | None:
    if valor is None or valor == "":
        return None
    if not valor.startswith(_PREFIXO):
        # Dado gravado antes da cifragem. Devolver como está mantém o sistema
        # funcionando durante a migração, em vez de esconder o cadastro inteiro.
        return valor
    try:
        return _chave_fernet().decrypt(valor[len(_PREFIXO):].encode()).decode()
    except InvalidToken:
        # Chave trocada sem migrar os dados. Devolver texto de erro seria pior:
        # entraria numa ata como se fosse o CPF da pessoa.
        return None


def mascarar(cpf: str | None) -> str | None:
    """"123.456.789-00" -> "***.456.789-**", para telas e listagens (§33)."""
    digitos = normalizar_documento(cpf or "")
    if len(digitos) != 11:
        return cpf
    return f"***.{digitos[3:6]}.{digitos[6:9]}-**"
