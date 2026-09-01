"use client";

/** Segurança da conta: senha e segundo fator (§31).
 *
 *  Duas decisões de interface que mudam se a proteção é usada ou abandonada:
 *
 *  1. A senha é avaliada enquanto se digita, dizendo **tudo** o que falta de
 *     uma vez. Descobrir um problema por tentativa faz a pessoa escolher a
 *     senha mais fraca que passar.
 *  2. Os códigos de recuperação aparecem uma única vez, com o peso que
 *     merecem. Sem eles, perder o celular é perder a conta.
 */
import { useEffect, useState, useTransition } from "react";

import { Aviso, Botao, Campo, Etiqueta } from "@/componentes/base";
import {
  confirmarMfa,
  conferirForcaDaSenha,
  desativarMfa,
  iniciarMfa,
  trocarSenha,
} from "@/lib/acoes";

export function TrocaDeSenha({ email }: { email: string }) {
  const [pendente, iniciar] = useTransition();
  const [atual, definirAtual] = useState("");
  const [nova, definirNova] = useState("");
  const [problemas, definirProblemas] = useState<string[]>([]);
  const [resultado, definirResultado] = useState<{ ok: boolean; texto: string } | null>(null);

  // Avalia enquanto digita, sem castigar cada tecla com uma chamada.
  useEffect(() => {
    if (nova.length < 4) {
      definirProblemas([]);
      return;
    }
    const relogio = setTimeout(async () => {
      const r = await conferirForcaDaSenha(nova, email);
      definirProblemas(r.problemas);
    }, 400);
    return () => clearTimeout(relogio);
  }, [nova, email]);

  const pronta = nova.length >= 12 && problemas.length === 0 && atual.length > 0;

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        iniciar(async () => {
          const r = await trocarSenha(atual, nova);
          definirResultado({
            ok: r.ok,
            texto: r.ok ? "Senha alterada." : (r.mensagem ?? "Falha ao trocar."),
          });
          if (r.ok) {
            definirAtual("");
            definirNova("");
          }
        });
      }}
    >
      <Campo
        rotulo="Senha atual"
        name="senha_atual"
        type="password"
        autoComplete="current-password"
        value={atual}
        onChange={(e) => definirAtual(e.target.value)}
        ajuda="Pedimos mesmo com você já logado: sessão aberta em máquina destravada não pode virar troca de senha."
      />
      <Campo
        rotulo="Senha nova"
        name="senha_nova"
        type="password"
        autoComplete="new-password"
        value={nova}
        onChange={(e) => definirNova(e.target.value)}
        ajuda="Mínimo de 12 caracteres. Uma frase que só você diria protege mais do que símbolo no meio de uma palavra curta."
      />

      {problemas.length > 0 && (
        <ul className="space-y-1">
          {problemas.map((p) => (
            <li
              key={p}
              className="text-[0.75rem] leading-snug"
              style={{ color: "var(--color-pendencia)" }}
            >
              • {p}
            </li>
          ))}
        </ul>
      )}
      {nova.length >= 12 && problemas.length === 0 && (
        <p className="text-[0.75rem]" style={{ color: "var(--color-apto)" }}>
          • Senha aceita.
        </p>
      )}

      <Botao tipo="submit" disabled={pendente || !pronta}>
        Trocar senha
      </Botao>
      {resultado && <Aviso tom={resultado.ok ? "sucesso" : "erro"}>{resultado.texto}</Aviso>}
    </form>
  );
}

export function SegundoFator({
  habilitado,
  codigosRestantes,
}: {
  habilitado: boolean;
  codigosRestantes: number;
}) {
  const [pendente, iniciar] = useTransition();
  const [svgQr, definirSvgQr] = useState<string | null>(null);
  const [segredo, definirSegredo] = useState<string | null>(null);
  const [codigo, definirCodigo] = useState("");
  const [codigosRecuperacao, definirCodigos] = useState<string[] | null>(null);
  const [senha, definirSenha] = useState("");
  const [erro, definirErro] = useState<string | null>(null);

  if (codigosRecuperacao) {
    return (
      <div className="space-y-3">
        <Aviso tom="sucesso" titulo="Segundo fator ativado">
          A partir de agora, entrar exige a senha e o código do aplicativo.
        </Aviso>
        <Aviso tom="atencao" titulo="Guarde estes códigos fora do celular">
          Cada um vale uma vez e serve para entrar se você perder o aparelho.
          Eles não serão mostrados de novo.
        </Aviso>
        <ul className="grid grid-cols-2 gap-2 rounded-md border bg-[var(--color-superficie-2)] p-3 font-mono text-[0.8125rem]">
          {codigosRecuperacao.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ul>
      </div>
    );
  }

  if (habilitado) {
    return (
      <div className="space-y-3">
        <p className="flex flex-wrap items-center gap-2 text-[0.875rem]">
          <Etiqueta tom="marca">ativo</Etiqueta>
          <span className="text-[var(--color-tinta-2)]">
            {codigosRestantes} código(s) de recuperação ainda válidos.
          </span>
        </p>
        <p className="text-[0.8125rem] leading-relaxed text-[var(--color-tinta-3)]">
          Desativar reduz a proteção da conta: uma senha vazada voltaria a ser
          suficiente para entrar. Por isso pedimos a senha aqui também.
        </p>
        <Campo
          rotulo="Sua senha"
          name="senha_desativar"
          type="password"
          value={senha}
          onChange={(e) => definirSenha(e.target.value)}
        />
        <Botao
          variante="perigo"
          disabled={pendente || !senha}
          onClick={() =>
            iniciar(async () => {
              const r = await desativarMfa(senha);
              if (!r.ok) definirErro(r.mensagem ?? "Falha ao desativar.");
            })
          }
        >
          Desativar segundo fator
        </Botao>
        {erro && <Aviso tom="erro">{erro}</Aviso>}
      </div>
    );
  }

  if (svgQr) {
    return (
      <div className="space-y-3">
        <p className="text-[0.875rem] leading-relaxed text-[var(--color-tinta-2)]">
          Abra seu aplicativo autenticador, escolha &ldquo;adicionar conta&rdquo; e leia o
          código abaixo. Depois confirme com os seis dígitos que ele mostrar.
        </p>
        <div
          className="h-48 w-48 overflow-hidden rounded border bg-white"
          role="img"
          aria-label="Código QR para o aplicativo autenticador"
          dangerouslySetInnerHTML={{ __html: svgQr }}
        />
        <details className="text-[0.75rem] text-[var(--color-tinta-3)]">
          <summary className="cursor-pointer">Não consigo ler o código</summary>
          <p className="mt-1">
            Digite esta chave no aplicativo:{" "}
            <code className="font-mono text-[var(--color-tinta)]">{segredo}</code>
          </p>
        </details>
        <Campo
          rotulo="Código do aplicativo"
          name="codigo_mfa"
          inputMode="numeric"
          autoComplete="one-time-code"
          placeholder="000000"
          value={codigo}
          onChange={(e) => definirCodigo(e.target.value)}
          ajuda="Só ativamos depois que você prova que consegue ler o código — ativar antes trancaria você para fora da conta."
        />
        <Botao
          disabled={pendente || codigo.length < 6}
          onClick={() =>
            iniciar(async () => {
              const r = await confirmarMfa(codigo);
              if (r.ok) definirCodigos(r.codigos ?? []);
              else definirErro(r.mensagem ?? "Código inválido.");
            })
          }
        >
          Confirmar e ativar
        </Botao>
        {erro && <Aviso tom="erro">{erro}</Aviso>}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-[0.875rem] leading-relaxed text-[var(--color-tinta-2)]">
        Com o segundo fator ligado, uma senha vazada não basta para entrar. É a
        proteção que mais rende num sistema que guarda CPF e documento de
        terceiros.
      </p>
      <Botao
        disabled={pendente}
        onClick={() =>
          iniciar(async () => {
            const r = await iniciarMfa();
            if (r.ok) {
              definirSvgQr(r.svg ?? null);
              definirSegredo(r.segredo ?? null);
            } else {
              definirErro(r.mensagem ?? "Falha ao iniciar.");
            }
          })
        }
      >
        Ativar segundo fator
      </Botao>
      {erro && <Aviso tom="erro">{erro}</Aviso>}
    </div>
  );
}
