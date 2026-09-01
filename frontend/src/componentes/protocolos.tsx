"use client";

/** Protocolo no RCPJ: exigências e registro (§22, §23).
 *
 *  O ciclo real com o cartório é: protocola, o oficial exige alguma coisa,
 *  cumpre-se a exigência, o oficial registra. A tela segue esse ciclo — e o
 *  registro só é declarado quando não há exigência aberta, porque é assim que
 *  o cartório trabalha.
 */
import { useState, useTransition } from "react";

import { Aviso, Botao, Campo, Etiqueta, Vazio } from "@/componentes/base";
import { concluirRegistro, cumprirExigencia, lancarExigencia } from "@/lib/acoes";
import { dataBr } from "@/lib/formato";
import type { Exigencia, Protocolo } from "@/lib/tipos";

const SITUACAO: Record<string, { rotulo: string; cor: string }> = {
  PREPARACAO: { rotulo: "Em preparação", cor: "var(--color-tinta-3)" },
  PROTOCOLADO: { rotulo: "No cartório", cor: "var(--color-marca)" },
  EM_EXIGENCIA: { rotulo: "Em exigência", cor: "var(--color-pendencia)" },
  REGISTRADO: { rotulo: "Registrado", cor: "var(--color-apto)" },
  DEVOLVIDO: { rotulo: "Devolvido", cor: "var(--color-bloqueado)" },
};

export function ListaProtocolos({
  protocolos,
  caminho,
}: {
  protocolos: Protocolo[];
  caminho: string;
}) {
  if (protocolos.length === 0) {
    return (
      <Vazio>
        Nenhum protocolo ainda. Ele nasce quando um ato validado segue para o cartório.
      </Vazio>
    );
  }
  return (
    <ul className="space-y-3">
      {protocolos.map((p) => (
        <ItemProtocolo key={p.id} protocolo={p} caminho={caminho} />
      ))}
    </ul>
  );
}

function ItemProtocolo({ protocolo, caminho }: { protocolo: Protocolo; caminho: string }) {
  const situacao = SITUACAO[protocolo.status] ?? {
    rotulo: protocolo.status,
    cor: "var(--color-tinta-3)",
  };
  const registrado = protocolo.status === "REGISTRADO";

  return (
    <li className="rounded-md border">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b px-4 py-3">
        <span className="text-[0.875rem] font-medium">
          {protocolo.numero ? `Protocolo ${protocolo.numero}` : "Protocolo sem número"}
        </span>
        <span className="text-[0.8125rem] font-medium" style={{ color: situacao.cor }}>
          {situacao.rotulo}
        </span>
        {protocolo.data_protocolo && (
          <span className="text-[0.75rem] text-[var(--color-tinta-3)]">
            entrada em {dataBr(protocolo.data_protocolo)}
          </span>
        )}
        {registrado && (
          <span className="ml-auto text-[0.8125rem]">
            <strong>{protocolo.numero_registro}</strong>
            {protocolo.livro && ` · livro ${protocolo.livro}`}
            {protocolo.folha && ` · fl. ${protocolo.folha}`}
            {protocolo.data_registro && ` · ${dataBr(protocolo.data_registro)}`}
          </span>
        )}
      </div>

      <div className="space-y-4 px-4 py-3.5">
        <Exigencias protocolo={protocolo} caminho={caminho} />
        {!registrado && <FormularioRegistro protocolo={protocolo} caminho={caminho} />}
      </div>
    </li>
  );
}

function Exigencias({ protocolo, caminho }: { protocolo: Protocolo; caminho: string }) {
  const [pendente, iniciar] = useTransition();
  const [erro, definirErro] = useState<string | null>(null);
  const [nova, definirNova] = useState("");
  const [prazo, definirPrazo] = useState("");
  const [abrindo, definirAbrindo] = useState(false);

  function lancar(evento: React.FormEvent) {
    evento.preventDefault();
    if (!nova.trim()) return;
    definirErro(null);
    iniciar(async () => {
      const r = await lancarExigencia(
        protocolo.id,
        { descricao: nova.trim(), prazo: prazo || null },
        caminho,
      );
      if (r.ok) {
        definirNova("");
        definirPrazo("");
        definirAbrindo(false);
      } else {
        definirErro(r.mensagem ?? "Falha ao lançar.");
      }
    });
  }

  return (
    <div>
      <h3 className="mb-2 text-[0.8125rem] font-semibold text-[var(--color-tinta-2)]">
        Exigências do cartório
      </h3>
      {protocolo.exigencias.length === 0 ? (
        <p className="text-[0.8125rem] text-[var(--color-tinta-3)]">
          Nenhuma exigência lançada.
        </p>
      ) : (
        <ul className="space-y-2">
          {protocolo.exigencias.map((e, indice) => (
            <ItemExigencia
              key={`${e.descricao}-${indice}`}
              exigencia={e}
              indice={indice}
              protocoloId={protocolo.id}
              caminho={caminho}
            />
          ))}
        </ul>
      )}

      {abrindo ? (
        <form onSubmit={lancar} className="mt-3 space-y-3 rounded-md border p-3">
          <Campo
            rotulo="O que o cartório exigiu"
            name="exigencia"
            value={nova}
            onChange={(e) => definirNova(e.target.value)}
            placeholder="Reconhecer firma do presidente na ata"
            ajuda="Copie a redação da intimação: é ela que vai ser conferida no reingresso."
          />
          <Campo
            rotulo="Prazo para cumprir"
            name="prazo"
            type="date"
            value={prazo}
            onChange={(e) => definirPrazo(e.target.value)}
            ajuda="Com prazo informado, o alerta entra na agenda automaticamente."
          />
          <div className="flex gap-2">
            <Botao tipo="submit" disabled={pendente || !nova.trim()}>
              Lançar exigência
            </Botao>
            <Botao variante="silencioso" onClick={() => definirAbrindo(false)}>
              Cancelar
            </Botao>
          </div>
        </form>
      ) : (
        <div className="mt-2">
          <Botao variante="silencioso" onClick={() => definirAbrindo(true)}>
            Lançar exigência
          </Botao>
        </div>
      )}
      {erro && (
        <div className="mt-2">
          <Aviso tom="erro">{erro}</Aviso>
        </div>
      )}
    </div>
  );
}

function ItemExigencia({
  exigencia,
  indice,
  protocoloId,
  caminho,
}: {
  exigencia: Exigencia;
  indice: number;
  protocoloId: string;
  caminho: string;
}) {
  const [pendente, iniciar] = useTransition();
  const [erro, definirErro] = useState<string | null>(null);
  const [observacao, definirObservacao] = useState("");
  const [dando, definirDando] = useState(false);

  if (exigencia.cumprida) {
    return (
      <li className="rounded-md border px-3 py-2 text-[0.8125rem]">
        <span className="flex flex-wrap items-center gap-2">
          <span className="text-[var(--color-tinta-2)] line-through">{exigencia.descricao}</span>
          <Etiqueta>cumprida em {dataBr(exigencia.cumprida_em)}</Etiqueta>
          {exigencia.cumprida_por && (
            <span className="text-[0.75rem] text-[var(--color-tinta-3)]">
              por {exigencia.cumprida_por}
            </span>
          )}
        </span>
        {exigencia.observacao && (
          <p className="mt-1 text-[0.75rem] text-[var(--color-tinta-3)]">
            {exigencia.observacao}
          </p>
        )}
      </li>
    );
  }

  return (
    <li
      className="rounded-md border px-3 py-2.5"
      style={{ borderColor: "var(--color-pendencia-contorno)" }}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[0.8125rem] font-medium">{exigencia.descricao}</span>
        {exigencia.prazo && <Etiqueta>até {dataBr(exigencia.prazo)}</Etiqueta>}
      </div>
      {dando ? (
        <div className="mt-2 space-y-2">
          <Campo
            rotulo="Como foi cumprida"
            name={`obs-${indice}`}
            value={observacao}
            onChange={(e) => definirObservacao(e.target.value)}
            placeholder="Firma reconhecida no 2º Tabelionato em 14/03"
          />
          <div className="flex gap-2">
            <Botao
              disabled={pendente}
              onClick={() =>
                iniciar(async () => {
                  const r = await cumprirExigencia(protocoloId, indice, observacao, caminho);
                  if (r.ok) definirDando(false);
                  else definirErro(r.mensagem ?? "Falha ao dar baixa.");
                })
              }
            >
              Dar baixa
            </Botao>
            <Botao variante="silencioso" onClick={() => definirDando(false)}>
              Cancelar
            </Botao>
          </div>
        </div>
      ) : (
        <div className="mt-2">
          <Botao variante="secundario" onClick={() => definirDando(true)}>
            Cumprir
          </Botao>
        </div>
      )}
      {erro && (
        <div className="mt-2">
          <Aviso tom="erro">{erro}</Aviso>
        </div>
      )}
    </li>
  );
}

function FormularioRegistro({
  protocolo,
  caminho,
}: {
  protocolo: Protocolo;
  caminho: string;
}) {
  const [pendente, iniciar] = useTransition();
  const [erro, definirErro] = useState<string | null>(null);
  const [aberto, definirAberto] = useState(false);
  const [dados, definirDados] = useState({
    data_registro: "",
    numero_registro: "",
    livro: "",
    folha: "",
  });

  const travado = protocolo.exigencias_abertas > 0;

  function registrar(evento: React.FormEvent) {
    evento.preventDefault();
    definirErro(null);
    iniciar(async () => {
      const r = await concluirRegistro(protocolo.id, dados, caminho);
      if (r.ok) definirAberto(false);
      else definirErro(r.mensagem ?? "Falha ao registrar.");
    });
  }

  if (travado) {
    return (
      <Aviso tom="atencao">
        {protocolo.exigencias_abertas} exigência(s) em aberto. O cartório não registra
        antes de todas serem cumpridas — dê baixa acima e o registro se libera.
      </Aviso>
    );
  }

  if (!aberto) {
    return (
      <Botao variante="secundario" onClick={() => definirAberto(true)}>
        Registrar retorno do cartório
      </Botao>
    );
  }

  return (
    <form onSubmit={registrar} className="space-y-3 rounded-md border p-3.5">
      <p className="text-[0.8125rem] text-[var(--color-tinta-3)]">
        Transcreva o que veio na certidão. Estes dados passam a ser a referência
        registral da entidade — quem declara registrado é o oficial, não o sistema.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <Campo
          rotulo="Data do registro"
          name="data_registro"
          type="date"
          required
          value={dados.data_registro}
          onChange={(e) => definirDados({ ...dados, data_registro: e.target.value })}
        />
        <Campo
          rotulo="Número do registro"
          name="numero_registro"
          required
          value={dados.numero_registro}
          onChange={(e) => definirDados({ ...dados, numero_registro: e.target.value })}
        />
        <Campo
          rotulo="Livro"
          name="livro"
          value={dados.livro}
          onChange={(e) => definirDados({ ...dados, livro: e.target.value })}
        />
        <Campo
          rotulo="Folha"
          name="folha"
          value={dados.folha}
          onChange={(e) => definirDados({ ...dados, folha: e.target.value })}
        />
      </div>
      <div className="flex gap-2">
        <Botao
          tipo="submit"
          disabled={pendente || !dados.data_registro || !dados.numero_registro}
        >
          Concluir registro
        </Botao>
        <Botao variante="silencioso" onClick={() => definirAberto(false)}>
          Cancelar
        </Botao>
      </div>
      {erro && <Aviso tom="erro">{erro}</Aviso>}
    </form>
  );
}
