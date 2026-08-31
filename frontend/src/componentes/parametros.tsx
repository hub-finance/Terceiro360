"use client";

import { useState, useTransition } from "react";

import { Aviso, Botao, Etiqueta, SeloSemaforo } from "@/componentes/base";
import { confirmarParametro, gravarParametro } from "@/lib/acoes";

export interface ParametroApi {
  chave: string;
  rotulo: string;
  pergunta: string;
  grupo: string;
  tipo: string;
  unidade: string | null;
  exemplos: string[];
  nota: string | null;
  valor: string | null;
  dispositivo: string | null;
  trecho: string | null;
  confirmado: boolean;
  origem: string | null;
  confianca: number | null;
  status: "CONFIRMADO" | "VALIDACAO_NECESSARIA" | "DADO_NAO_INFORMADO";
}

const ESTADO = {
  CONFIRMADO: { semaforo: "APTO", texto: "Confirmado" },
  VALIDACAO_NECESSARIA: { semaforo: "PENDENCIA", texto: "Validação necessária" },
  DADO_NAO_INFORMADO: { semaforo: "PENDENCIA", texto: "Não informado" },
} as const;

export function ListaParametros({
  versaoId,
  parametros,
  caminho,
}: {
  versaoId: string;
  parametros: ParametroApi[];
  caminho: string;
}) {
  const [filtro, definirFiltro] = useState<"TODOS" | "PENDENTES">("PENDENTES");
  const pendentes = parametros.filter((p) => p.status !== "CONFIRMADO");
  const visiveis = filtro === "PENDENTES" ? pendentes : parametros;

  const grupos = visiveis.reduce<Record<string, ParametroApi[]>>((acc, p) => {
    (acc[p.grupo] ??= []).push(p);
    return acc;
  }, {});

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {(["PENDENTES", "TODOS"] as const).map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => definirFiltro(f)}
            aria-pressed={filtro === f}
            className={`rounded-full border px-3 py-1 text-[0.75rem] font-medium ${
              filtro === f
                ? "border-[var(--color-marca-contorno)] bg-[var(--color-marca-clara)] text-[var(--color-marca)]"
                : "text-[var(--color-tinta-2)]"
            }`}
          >
            {f === "PENDENTES" ? `Pendentes (${pendentes.length})` : `Todas (${parametros.length})`}
          </button>
        ))}
      </div>

      {visiveis.length === 0 ? (
        <Aviso tom="sucesso">
          Todas as regras do estatuto estão confirmadas. As validações de quórum,
          prazo e competência já usam esses valores.
        </Aviso>
      ) : (
        <div className="space-y-6">
          {Object.entries(grupos).map(([grupo, itens]) => (
            <section key={grupo}>
              <h3 className="mb-2 text-[0.6875rem] font-semibold uppercase tracking-wider text-[var(--color-tinta-3)]">
                {grupo}
              </h3>
              <ul className="space-y-2">
                {itens.map((p) => (
                  <Parametro key={p.chave} parametro={p} versaoId={versaoId} caminho={caminho} />
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function Parametro({
  parametro,
  versaoId,
  caminho,
}: {
  parametro: ParametroApi;
  versaoId: string;
  caminho: string;
}) {
  const [editando, definirEditando] = useState(false);
  const [valor, definirValor] = useState(parametro.valor ?? "");
  const [dispositivo, definirDispositivo] = useState(parametro.dispositivo ?? "");
  const [erro, definirErro] = useState<string | null>(null);
  const [pendente, iniciar] = useTransition();

  const estado = ESTADO[parametro.status];

  function confirmar() {
    definirErro(null);
    iniciar(async () => {
      const r = await confirmarParametro(versaoId, parametro.chave, caminho);
      if (!r.ok) definirErro(r.mensagem ?? "Falha ao confirmar.");
    });
  }

  function salvar(confirmado: boolean) {
    definirErro(null);
    iniciar(async () => {
      const r = await gravarParametro(
        versaoId,
        {
          chave: parametro.chave,
          valor,
          tipo_valor: parametro.tipo === "lista" ? "lista" : parametro.tipo,
          dispositivo: dispositivo || undefined,
          confirmado,
        },
        caminho,
      );
      if (r.ok) definirEditando(false);
      else definirErro(r.mensagem ?? "Falha ao gravar.");
    });
  }

  return (
    <li className="rounded-[var(--radius-cartao)] border bg-[var(--color-superficie)] px-4 py-3">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0 flex-1">
          {/* A pergunta em linguagem de usuário vem antes do rótulo técnico (§52). */}
          <p className="text-[0.875rem] font-medium leading-snug">{parametro.pergunta}</p>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="text-[0.75rem] text-[var(--color-tinta-3)]">{parametro.rotulo}</span>
            {parametro.dispositivo && <Etiqueta>{parametro.dispositivo}</Etiqueta>}
            {parametro.origem === "IA_SUGERIDO" && (
              <Etiqueta tom="marca">
                sugerido pela IA
                {parametro.confianca !== null && ` · ${Math.round(parametro.confianca * 100)}%`}
              </Etiqueta>
            )}
          </div>
        </div>
        <SeloSemaforo estado={estado.semaforo} texto={estado.texto} />
      </div>

      {!editando && (
        <div className="mt-2.5 flex flex-wrap items-center justify-between gap-3">
          <p className="text-[0.875rem]">
            {parametro.valor ? (
              <span className="font-medium">
                {parametro.valor}
                {parametro.unidade && (
                  <span className="font-normal text-[var(--color-tinta-3)]"> {parametro.unidade}</span>
                )}
              </span>
            ) : (
              <span className="font-semibold text-[var(--color-bloqueado)]">
                DADO NÃO INFORMADO
              </span>
            )}
          </p>
          <div className="flex gap-2">
            <Botao variante="silencioso" onClick={() => definirEditando(true)} disabled={pendente}>
              {parametro.valor ? "Editar" : "Preencher"}
            </Botao>
            {parametro.status === "VALIDACAO_NECESSARIA" && (
              <Botao onClick={confirmar} disabled={pendente}>
                {pendente ? "Confirmando…" : "Confirmar"}
              </Botao>
            )}
          </div>
        </div>
      )}

      {editando && (
        <div className="mt-3 space-y-3 border-t pt-3">
          <div className="grid gap-3 sm:grid-cols-[1fr_10rem]">
            <label className="block">
              <span className="mb-1 block text-[0.75rem] font-medium text-[var(--color-tinta-2)]">
                Valor
              </span>
              <input
                value={valor}
                onChange={(e) => definirValor(e.target.value)}
                placeholder={parametro.exemplos[0] ?? ""}
                className="w-full rounded-md border bg-[var(--color-superficie)] px-3 py-2 text-[0.875rem]"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-[0.75rem] font-medium text-[var(--color-tinta-2)]">
                Dispositivo
              </span>
              <input
                value={dispositivo}
                onChange={(e) => definirDispositivo(e.target.value)}
                placeholder="art. 21"
                className="w-full rounded-md border bg-[var(--color-superficie)] px-3 py-2 text-[0.875rem]"
              />
            </label>
          </div>

          {parametro.exemplos.length > 0 && (
            <p className="text-[0.75rem] text-[var(--color-tinta-3)]">
              Exemplos: {parametro.exemplos.join(" · ")}
            </p>
          )}
          {parametro.nota && (
            <p className="text-[0.75rem] leading-snug text-[var(--color-tinta-3)]">
              {parametro.nota}
            </p>
          )}

          <div className="flex flex-wrap gap-2">
            <Botao onClick={() => salvar(true)} disabled={pendente || !valor.trim()}>
              {pendente ? "Salvando…" : "Salvar e confirmar"}
            </Botao>
            <Botao variante="secundario" onClick={() => salvar(false)} disabled={pendente || !valor.trim()}>
              Salvar sem confirmar
            </Botao>
            <Botao
              variante="silencioso"
              onClick={() => {
                definirEditando(false);
                definirValor(parametro.valor ?? "");
              }}
              disabled={pendente}
            >
              Cancelar
            </Botao>
          </div>
        </div>
      )}

      {parametro.trecho && !editando && (
        <details className="mt-2">
          <summary className="cursor-pointer text-[0.75rem] text-[var(--color-tinta-3)]">
            Trecho do estatuto
          </summary>
          <blockquote className="mt-1.5 border-l-2 pl-3 text-[0.8125rem] italic leading-relaxed text-[var(--color-tinta-2)]">
            {parametro.trecho}
          </blockquote>
        </details>
      )}

      {erro && (
        <p className="mt-2 text-[0.8125rem] text-[var(--color-bloqueado)]" role="alert">
          {erro}
        </p>
      )}
    </li>
  );
}
