"use client";

/** Curadoria de uma mudança normativa (§37, §46, §47).
 *
 *  Publicar é ato humano. O formulário pede o texto novo, a data em que passa
 *  a valer e quais dispositivos mudaram — este último campo é o que permite ao
 *  sistema calcular, depois, o que exatamente parou de valer.
 */
import { useState, useTransition } from "react";

import { Aviso, Botao, Etiqueta } from "@/componentes/base";
import { descartarAtualizacao, publicarAtualizacao, tratarImpacto } from "@/lib/acoes";
import { dataBr } from "@/lib/formato";
import type { AtualizacaoNormativa, ImpactoNormativo } from "@/lib/tipos";

const SITUACAO: Record<string, { rotulo: string; cor: string }> = {
  DETECTADA: { rotulo: "Aguardando triagem", cor: "var(--color-pendencia)" },
  EM_ANALISE: { rotulo: "Em análise", cor: "var(--color-pendencia)" },
  APROVADA: { rotulo: "Aprovada", cor: "var(--color-marca)" },
  PUBLICADA: { rotulo: "Publicada", cor: "var(--color-apto)" },
  DESCARTADA: { rotulo: "Descartada", cor: "var(--color-tinta-3)" },
};

export function ListaAtualizacoes({
  atualizacoes,
  podeCurar,
}: {
  atualizacoes: AtualizacaoNormativa[];
  podeCurar: boolean;
}) {
  const pendentes = atualizacoes.filter(
    (a) => a.situacao === "DETECTADA" || a.situacao === "EM_ANALISE",
  );

  if (atualizacoes.length === 0) {
    return (
      <p className="py-4 text-center text-[0.8125rem] text-[var(--color-tinta-3)]">
        Nenhuma mudança normativa registrada.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {!podeCurar && pendentes.length > 0 && (
        <Aviso tom="atencao">
          Você pode acompanhar, mas não publicar. Colocar uma norma em vigor exige
          responsável com registro profissional cadastrado — é esse registro que
          sustenta a fundamentação usada nos atos.
        </Aviso>
      )}
      <ul className="space-y-2">
        {atualizacoes.map((a) => (
          <ItemAtualizacao key={a.id} atualizacao={a} podeCurar={podeCurar} />
        ))}
      </ul>
    </div>
  );
}

function ItemAtualizacao({
  atualizacao,
  podeCurar,
}: {
  atualizacao: AtualizacaoNormativa;
  podeCurar: boolean;
}) {
  const [aberto, definirAberto] = useState(false);
  const [erro, definirErro] = useState<string | null>(null);
  const [sucesso, definirSucesso] = useState<string | null>(null);
  const [pendente, iniciar] = useTransition();

  const [texto, definirTexto] = useState("");
  const [vigenteDesde, definirVigenteDesde] = useState("");
  const [dispositivos, definirDispositivos] = useState("");
  const [resumo, definirResumo] = useState("");
  const [parecer, definirParecer] = useState("");

  const s = SITUACAO[atualizacao.situacao] ?? SITUACAO.DETECTADA;
  const pendente_de_triagem =
    atualizacao.situacao === "DETECTADA" || atualizacao.situacao === "EM_ANALISE";

  function publicar() {
    definirErro(null);
    iniciar(async () => {
      const r = await publicarAtualizacao(atualizacao.id, {
        texto_novo: texto,
        vigente_desde: vigenteDesde,
        resumo: resumo || undefined,
        dispositivos_alterados: dispositivos
          .split("\n")
          .map((l) => l.trim())
          .filter(Boolean),
        parecer_curadoria: parecer || undefined,
      });
      if (r.ok) {
        definirSucesso(
          `Nova redação publicada. ${r.impactos ?? 0} regra(s) ou modelo(s) foram `
            + "marcados para revisão.",
        );
        definirAberto(false);
      } else {
        definirErro(r.mensagem ?? "Falha ao publicar.");
      }
    });
  }

  function descartar() {
    definirErro(null);
    iniciar(async () => {
      const r = await descartarAtualizacao(
        atualizacao.id,
        parecer || "Mudança sem efeito normativo.",
      );
      if (r.ok) definirSucesso("Descartada, com o parecer registrado.");
      else definirErro(r.mensagem ?? "Falha ao descartar.");
    });
  }

  return (
    <li className="rounded-[var(--radius-cartao)] border bg-[var(--color-superficie)] px-4 py-3">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <p className="text-[0.875rem] font-medium leading-snug">{atualizacao.titulo}</p>
          <p className="mt-0.5 text-[0.75rem] text-[var(--color-tinta-3)]">
            {atualizacao.detectado_em && `Detectada em ${dataBr(atualizacao.detectado_em)}`}
            {" · origem "}
            {atualizacao.origem.toLowerCase()}
            {atualizacao.impactos_abertos > 0 &&
              ` · ${atualizacao.impactos_abertos} impacto(s) em aberto`}
          </p>
        </div>
        <span className="shrink-0 text-[0.75rem] font-semibold" style={{ color: s.cor }}>
          {s.rotulo}
        </span>
      </div>

      {atualizacao.resumo && (
        <p className="mt-1.5 text-[0.8125rem] leading-relaxed text-[var(--color-tinta-2)]">
          {atualizacao.resumo}
        </p>
      )}

      {atualizacao.url_evidencia && (
        <a
          href={atualizacao.url_evidencia}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 inline-block text-[0.75rem] text-[var(--color-marca)] underline underline-offset-2"
        >
          evidência na fonte oficial
        </a>
      )}

      {sucesso && (
        <div className="mt-2">
          <Aviso tom="sucesso">{sucesso}</Aviso>
        </div>
      )}
      {erro && (
        <div className="mt-2">
          <Aviso tom="erro">{erro}</Aviso>
        </div>
      )}

      {pendente_de_triagem && podeCurar && !sucesso && (
        <div className="mt-3">
          {!aberto ? (
            <Botao variante="secundario" onClick={() => definirAberto(true)}>
              Triar
            </Botao>
          ) : (
            <div className="space-y-3 border-t pt-3">
              <Campo rotulo="Nova redação (texto de referência)">
                <textarea
                  rows={5}
                  value={texto}
                  onChange={(e) => definirTexto(e.target.value)}
                  className={CLASSE}
                />
              </Campo>

              <div className="grid gap-3 sm:grid-cols-2">
                <Campo
                  rotulo="Passa a valer em"
                  ajuda="A redação anterior continua citável para os atos praticados na vigência dela."
                >
                  <input
                    type="date"
                    value={vigenteDesde}
                    onChange={(e) => definirVigenteDesde(e.target.value)}
                    className={CLASSE}
                  />
                </Campo>
                <Campo
                  rotulo="Dispositivos alterados"
                  ajuda="Um por linha. É o que permite calcular o que parou de valer."
                >
                  <textarea
                    rows={3}
                    value={dispositivos}
                    onChange={(e) => definirDispositivos(e.target.value)}
                    placeholder="art. 60"
                    className={CLASSE}
                  />
                </Campo>
              </div>

              <Campo rotulo="Resumo da alteração">
                <input
                  value={resumo}
                  onChange={(e) => definirResumo(e.target.value)}
                  className={CLASSE}
                />
              </Campo>

              <Campo rotulo="Parecer da curadoria">
                <textarea
                  rows={2}
                  value={parecer}
                  onChange={(e) => definirParecer(e.target.value)}
                  placeholder="O que foi conferido e por que esta decisão."
                  className={CLASSE}
                />
              </Campo>

              <div className="flex flex-wrap gap-2">
                <Botao
                  disabled={pendente || !texto.trim() || !vigenteDesde}
                  onClick={publicar}
                >
                  {pendente ? "Publicando…" : "Publicar nova redação"}
                </Botao>
                <Botao variante="secundario" disabled={pendente} onClick={descartar}>
                  Descartar
                </Botao>
                <Botao variante="silencioso" onClick={() => definirAberto(false)}>
                  Cancelar
                </Botao>
              </div>

              <p className="text-[0.75rem] leading-snug text-[var(--color-tinta-3)]">
                Publicar coloca esta redação em vigor no motor de validação, sob sua
                responsabilidade profissional, e marca para revisão tudo que se apoiava
                na redação anterior.
              </p>
            </div>
          )}
        </div>
      )}
    </li>
  );
}

export function ListaImpactos({ impactos }: { impactos: ImpactoNormativo[] }) {
  const ALVO: Record<string, string> = {
    REGRA_VALIDACAO: "regra de validação",
    TEMPLATE: "modelo de documento",
    CHECKLIST: "checklist",
    PARAMETRO_ESTATUTARIO: "parâmetro do estatuto",
    REGRA_RCPJ: "regra de cartório",
    EVENTO_EM_ANDAMENTO: "ato em andamento",
    ENTIDADE: "entidade",
  };

  if (impactos.length === 0) {
    return (
      <p className="py-4 text-center text-[0.8125rem] text-[var(--color-tinta-3)]">
        Nenhum impacto normativo em aberto.
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {impactos.map((i) => (
        <ItemImpacto key={i.id} impacto={i} rotuloAlvo={ALVO[i.alvo_tipo] ?? i.alvo_tipo} />
      ))}
    </ul>
  );
}

function ItemImpacto({
  impacto,
  rotuloAlvo,
}: {
  impacto: ImpactoNormativo;
  rotuloAlvo: string;
}) {
  const [pendente, iniciar] = useTransition();
  const [feito, definirFeito] = useState<string | null>(null);

  function tratar(dispensado: boolean) {
    iniciar(async () => {
      const r = await tratarImpacto(impacto.id, dispensado);
      definirFeito(r.ok ? (dispensado ? "Dispensado." : "Marcado como tratado.") : r.mensagem!);
    });
  }

  return (
    <li className="rounded-md border px-3.5 py-3">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="text-[0.875rem] font-medium">{impacto.alvo_ref}</span>
        <Etiqueta>{rotuloAlvo}</Etiqueta>
      </div>
      {impacto.descricao && (
        <p className="mt-1 text-[0.8125rem] leading-relaxed text-[var(--color-tinta-2)]">
          {impacto.descricao}
        </p>
      )}
      {feito ? (
        <p className="mt-2 text-[0.8125rem] text-[var(--color-apto)]">{feito}</p>
      ) : (
        <div className="mt-2 flex flex-wrap gap-2">
          <Botao variante="secundario" disabled={pendente} onClick={() => tratar(false)}>
            Revisei
          </Botao>
          <Botao variante="silencioso" disabled={pendente} onClick={() => tratar(true)}>
            Não se aplica
          </Botao>
        </div>
      )}
    </li>
  );
}

const CLASSE =
  "w-full rounded-md border bg-[var(--color-superficie)] px-3 py-2 text-[0.8125rem] font-normal text-[var(--color-tinta)]";

function Campo({
  rotulo,
  ajuda,
  children,
}: {
  rotulo: string;
  ajuda?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[0.75rem] font-medium text-[var(--color-tinta-2)]">
        {rotulo}
      </span>
      {children}
      {ajuda && (
        <span className="mt-1 block text-[0.6875rem] leading-snug text-[var(--color-tinta-3)]">
          {ajuda}
        </span>
      )}
    </label>
  );
}
