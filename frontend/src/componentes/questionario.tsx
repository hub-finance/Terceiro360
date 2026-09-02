"use client";

/** QUESTIONÁRIO INTELIGENTE (§11, §52).
 *
 *  Pergunta só o que é próprio do ato — o resto vem do cadastro. Ao lado de
 *  cada campo que depende de regra estatutária, mostra o que o estatuto diz,
 *  para que a pessoa responda com o parâmetro à vista e não de memória.
 */
import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { Aviso, Botao } from "@/componentes/base";
import { criarAto, salvarRespostas } from "@/lib/acoes";
import type { CampoQuestionario } from "@/lib/tipos";

export interface ReferenciaEstatuto {
  valor: string | null;
  status: string;
  rotulo: string;
  dispositivo: string | null;
}

type Valores = Record<string, unknown>;

export function Questionario({
  campos,
  valoresIniciais,
  referencias,
  eventoId,
  entidadeId,
  tipo,
  caminho,
}: {
  campos: CampoQuestionario[];
  valoresIniciais: Valores;
  referencias: Record<string, ReferenciaEstatuto>;
  /** Sem eventoId, o formulário cria o ato ao salvar. */
  eventoId?: string;
  entidadeId: string;
  tipo: string;
  caminho: string;
}) {
  const router = useRouter();
  const [valores, definirValores] = useState<Valores>(valoresIniciais);
  const [erro, definirErro] = useState<string | null>(null);
  const [salvo, definirSalvo] = useState(false);
  const [pendente, iniciar] = useTransition();

  const faltando = campos.filter((c) => c.obrigatorio && vazio(valores[c.nome]));

  function definir(nome: string, valor: unknown) {
    definirValores((v) => ({ ...v, [nome]: valor }));
    definirSalvo(false);
  }

  function salvar() {
    definirErro(null);
    iniciar(async () => {
      if (eventoId) {
        const r = await salvarRespostas(eventoId, valores, caminho);
        if (r.ok) definirSalvo(true);
        else definirErro(r.mensagem ?? "Falha ao salvar.");
        return;
      }
      const r = await criarAto(entidadeId, tipo, valores);
      if (r.ok && r.id) router.push(`/entidades/${entidadeId}/atos/${r.id}`);
      else definirErro(r.mensagem ?? "Falha ao criar o ato.");
    });
  }

  return (
    <div className="space-y-5">
      {erro && <Aviso tom="erro">{erro}</Aviso>}

      <div className="space-y-4">
        {campos.map((c) => (
          <Campo
            key={c.nome}
            campo={c}
            valor={valores[c.nome]}
            referencia={c.referencia_estatutaria ? referencias[c.referencia_estatutaria] : undefined}
            aoMudar={(v) => definir(c.nome, v)}
          />
        ))}
      </div>

      <div className="sticky bottom-0 flex flex-wrap items-center gap-3 border-t bg-[var(--color-superficie)] py-3">
        <Botao onClick={salvar} disabled={pendente}>
          {pendente ? "Salvando…" : eventoId ? "Salvar respostas" : "Criar ato"}
        </Botao>
        {salvo && (
          <span className="text-[0.8125rem] text-[var(--color-apto)]">Respostas salvas.</span>
        )}
        {faltando.length > 0 && (
          <span className="text-[0.8125rem] text-[var(--color-tinta-3)]">
            {faltando.length} campo(s) obrigatório(s) em branco — o documento sairá com
            DADO NÃO INFORMADO neles.
          </span>
        )}
      </div>
    </div>
  );
}

function Campo({
  campo,
  valor,
  referencia,
  aoMudar,
}: {
  campo: CampoQuestionario;
  valor: unknown;
  referencia?: ReferenciaEstatuto;
  aoMudar: (v: unknown) => void;
}) {
  const id = `campo-${campo.nome}`;
  const classe =
    "w-full rounded-md border bg-[var(--color-superficie)] px-3 py-2 text-[0.875rem] text-[var(--color-tinta)]";

  return (
    <div>
      <label htmlFor={id} className="block text-[0.875rem] font-medium leading-snug">
        {campo.pergunta}
        {!campo.obrigatorio && (
          <span className="ml-1.5 font-normal text-[var(--color-tinta-3)]">(opcional)</span>
        )}
      </label>

      {campo.ajuda && (
        <p className="mt-0.5 text-[0.75rem] leading-snug text-[var(--color-tinta-3)]">
          {campo.ajuda}
        </p>
      )}

      <div className="mt-1.5">
        {campo.tipo === "booleano" ? (
          <div className="flex gap-4">
            {[
              ["Sim", true],
              ["Não", false],
            ].map(([rotulo, v]) => (
              <label key={String(v)} className="flex items-center gap-1.5 text-[0.875rem]">
                <input
                  type="radio"
                  name={id}
                  checked={valor === v}
                  onChange={() => aoMudar(v)}
                />
                {rotulo as string}
              </label>
            ))}
          </div>
        ) : campo.tipo === "opcao" ? (
          <select
            id={id}
            value={String(valor ?? "")}
            onChange={(e) => aoMudar(e.target.value || null)}
            className={classe}
          >
            <option value="">Selecione…</option>
            {campo.opcoes.map((o) => (
              <option key={o} value={o}>
                {o.replaceAll("_", " ").toLowerCase()}
              </option>
            ))}
          </select>
        ) : campo.tipo === "lista" ? (
          <ListaComSugestoes
            id={id}
            sugestoes={campo.sugestoes ?? []}
            valor={Array.isArray(valor) ? valor.map(String) : []}
            aoMudar={aoMudar}
            classe={classe}
          />
        ) : campo.tipo === "pessoas" ? (
          <ListaPessoas valor={Array.isArray(valor) ? valor : []} aoMudar={aoMudar} />
        ) : (
          <input
            id={id}
            type={campo.tipo === "data" ? "date" : campo.tipo === "numero" ? "number" : "text"}
            value={String(valor ?? "")}
            onChange={(e) =>
              aoMudar(
                campo.tipo === "numero"
                  ? e.target.value === ""
                    ? null
                    : Number(e.target.value)
                  : e.target.value || null,
              )
            }
            className={classe}
          />
        )}
      </div>

      {/* §52 — o parâmetro do estatuto ao lado da pergunta. */}
      {referencia && (
        <p className="mt-1.5 text-[0.75rem] leading-snug">
          {referencia.status === "CONFIRMADO" ? (
            <span className="text-[var(--color-tinta-2)]">
              <span className="font-medium">Segundo o estatuto cadastrado:</span>{" "}
              {referencia.valor}
              {referencia.dispositivo && ` (${referencia.dispositivo})`}
            </span>
          ) : (
            <span className="text-[var(--color-pendencia)]">
              {referencia.rotulo}: não confirmado no estatuto — o sistema não usa este
              parâmetro na validação enquanto não for confirmado.
            </span>
          )}
        </p>
      )}
    </div>
  );
}

function ListaPessoas({
  valor,
  aoMudar,
}: {
  valor: Record<string, string>[];
  aoMudar: (v: unknown) => void;
}) {
  const linhas = valor.length > 0 ? valor : [{ nome: "", cargo: "", cpf: "" }];

  function atualizar(indice: number, campo: string, v: string) {
    const novo = linhas.map((l, i) => (i === indice ? { ...l, [campo]: v } : l));
    aoMudar(novo.filter((l) => l.nome || l.cargo || l.cpf));
  }

  const classe = "rounded-md border bg-[var(--color-superficie)] px-2.5 py-1.5 text-[0.8125rem]";

  return (
    <div className="space-y-2">
      {linhas.map((l, i) => (
        <div key={i} className="grid gap-2 sm:grid-cols-[1.4fr_1fr_0.9fr]">
          <input
            value={l.nome ?? ""}
            onChange={(e) => atualizar(i, "nome", e.target.value)}
            placeholder="Nome completo"
            className={classe}
            aria-label={`Nome da pessoa ${i + 1}`}
          />
          <input
            value={l.cargo ?? ""}
            onChange={(e) => atualizar(i, "cargo", e.target.value)}
            placeholder="Cargo"
            className={classe}
            aria-label={`Cargo da pessoa ${i + 1}`}
          />
          <input
            value={l.cpf ?? ""}
            onChange={(e) => atualizar(i, "cpf", e.target.value)}
            placeholder="CPF"
            className={classe}
            aria-label={`CPF da pessoa ${i + 1}`}
          />
        </div>
      ))}
      <button
        type="button"
        onClick={() => aoMudar([...linhas, { nome: "", cargo: "", cpf: "" }])}
        className="text-[0.8125rem] font-medium text-[var(--color-marca)] hover:underline"
      >
        + Acrescentar pessoa
      </button>
      <p className="text-[0.75rem] text-[var(--color-tinta-3)]">
        Quem já estiver cadastrado entra completo nos documentos — RG, endereço e
        qualificação vêm do cadastro, sem redigitação.
      </p>
    </div>
  );
}

function vazio(v: unknown) {
  return v === null || v === undefined || v === "" || (Array.isArray(v) && v.length === 0);
}


/** Campo de lista com pauta sugerida.
 *
 * A ordem do dia é o campo que mais custa caro quando fica pela metade:
 * deliberar sobre assunto ausente do edital é vício de anulação, e o validador
 * bloqueia o ato quando a matéria não aparece aqui. Escrever tudo à mão, sem
 * saber o que o sistema procura, transformava isso em adivinhação.
 *
 * As sugestões vêm do tipo do ato. Marcar mantém a ordem em que aparecem — a
 * pauta de uma assembleia tem sequência, e ela não pode depender da ordem em
 * que a pessoa clicou. O que for escrito à mão fica ao final, na ordem digitada.
 */
function ListaComSugestoes({
  id,
  sugestoes,
  valor,
  aoMudar,
  classe,
}: {
  id: string;
  sugestoes: string[];
  valor: string[];
  aoMudar: (valor: string[]) => void;
  classe: string;
}) {
  const marcadas = new Set(valor.filter((v) => sugestoes.includes(v)));
  const livres = valor.filter((v) => !sugestoes.includes(v));

  function alternar(item: string) {
    const proximas = new Set(marcadas);
    if (proximas.has(item)) proximas.delete(item);
    else proximas.add(item);
    aoMudar([...sugestoes.filter((s) => proximas.has(s)), ...livres]);
  }

  function trocarLivres(texto: string) {
    const novas = texto.split("\n").map((l) => l.trim()).filter(Boolean);
    aoMudar([...sugestoes.filter((s) => marcadas.has(s)), ...novas]);
  }

  if (sugestoes.length === 0) {
    return (
      <textarea
        id={id}
        rows={3}
        value={valor.join("\n")}
        onChange={(e) => trocarLivres(e.target.value)}
        placeholder="Um item por linha"
        className={classe}
      />
    );
  }

  return (
    <div className="space-y-2.5">
      <p className="text-[0.75rem] text-[var(--color-tinta-3)]">
        Marque o que constava do edital de convocação. Se a redação do seu edital
        for outra, escreva abaixo — o que vale é o que foi convocado.
      </p>

      <ul className="space-y-1">
        {sugestoes.map((item) => (
          <li key={item}>
            <label className="flex cursor-pointer items-start gap-2.5 rounded-md px-2 py-1.5 hover:bg-[var(--color-superficie-2)]">
              <input
                type="checkbox"
                checked={marcadas.has(item)}
                onChange={() => alternar(item)}
                className="mt-0.5 h-3.5 w-3.5 shrink-0 accent-[var(--color-marca)]"
              />
              <span className="text-[0.8125rem] leading-snug text-[var(--color-tinta-2)]">
                {item}
              </span>
            </label>
          </li>
        ))}
      </ul>

      <div className="space-y-1">
        <label
          htmlFor={`${id}-livres`}
          className="block text-[0.75rem] font-medium text-[var(--color-tinta-3)]"
        >
          Outros itens da pauta
        </label>
        <textarea
          id={`${id}-livres`}
          rows={2}
          value={livres.join("\n")}
          onChange={(e) => trocarLivres(e.target.value)}
          placeholder="Um item por linha"
          className={classe}
        />
      </div>

      {valor.length > 0 && (
        <p className="text-[0.75rem] text-[var(--color-tinta-3)]">
          {valor.length} {valor.length === 1 ? "item na pauta" : "itens na pauta"}.
        </p>
      )}
    </div>
  );
}
