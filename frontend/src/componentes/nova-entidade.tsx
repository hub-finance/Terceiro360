"use client";

/** Cadastro de uma entidade.
 *
 * Só a razão social é obrigatória, e de propósito: quem está constituindo uma
 * entidade do zero muitas vezes ainda não tem CNPJ, nem endereço definitivo,
 * nem data de constituição. Exigir esses campos aqui obrigaria a inventá-los —
 * exatamente o que o resto do sistema recusa fazer. O que faltar aparece como
 * lacuna na hora de gerar documento, que é onde a falta realmente importa.
 */
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Aviso, Botao, Campo } from "@/componentes/base";
import { type DadosReceita, consultarCnpj, criarEntidade } from "@/lib/acoes";

const TIPOS: { valor: string; rotulo: string; nota: string }[] = [
  { valor: "ASSOCIACAO", rotulo: "Associação", nota: "União de pessoas para fim não econômico (CC, art. 53)." },
  { valor: "IGREJA", rotulo: "Igreja", nota: "Organização religiosa com culto e comunidade próprios." },
  { valor: "ORGANIZACAO_RELIGIOSA", rotulo: "Organização religiosa", nota: "Convenção, diocese, ordem ou congregação (CC, art. 44, IV)." },
  { valor: "FUNDACAO", rotulo: "Fundação", nota: "Patrimônio afetado a um fim; exige velamento do Ministério Público." },
  { valor: "INSTITUTO", rotulo: "Instituto", nota: "Nome usual de associação com fim técnico, cultural ou científico." },
  { valor: "OSC", rotulo: "OSC", nota: "Organização da sociedade civil, Lei 13.019/2014." },
  { valor: "OSCIP", rotulo: "OSCIP", nota: "Qualificação federal da Lei 9.790/1999." },
  { valor: "ENTIDADE_FILANTROPICA", rotulo: "Entidade filantrópica", nota: "Assistência social, saúde ou educação, Lei 12.101/2009." },
  { valor: "ENTIDADE_EDUCACIONAL", rotulo: "Entidade educacional", nota: "Mantenedora de estabelecimento de ensino." },
  { valor: "ENTIDADE_ASSISTENCIAL", rotulo: "Entidade assistencial", nota: "Atendimento, assessoramento ou defesa de direitos." },
  { valor: "OUTRA", rotulo: "Outra", nota: "Nenhuma das anteriores." },
];

const UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"];

export function FormularioNovaEntidade() {
  const router = useRouter();
  const [tipo, definirTipo] = useState("ASSOCIACAO");
  const [erro, definirErro] = useState<string | null>(null);
  const [enviando, definirEnviando] = useState(false);

  // Preenchimento pela Receita. O formulário continua não controlado — trocar
  // a `versao` remonta os campos com os novos valores padrão, o que preserva a
  // digitação normal sem transformar cada tecla em re-renderização.
  const [valores, definirValores] = useState<Record<string, string>>({});
  const [versao, definirVersao] = useState(0);
  const [receita, definirReceita] = useState<DadosReceita | null>(null);
  const [consultando, definirConsultando] = useState(false);
  const [avisoReceita, definirAvisoReceita] = useState<string | null>(null);

  const notaDoTipo = TIPOS.find((t) => t.valor === tipo)?.nota;

  async function buscarNaReceita() {
    const cnpj = (
      document.querySelector<HTMLInputElement>('input[name="cnpj" defaultValue={valores.cnpj ?? ""}]')?.value ?? ""
    ).trim();
    if (!cnpj) {
      definirAvisoReceita("Informe o CNPJ para consultar.");
      return;
    }

    definirAvisoReceita(null);
    definirConsultando(true);
    const resultado = await consultarCnpj(cnpj);
    definirConsultando(false);

    if (!resultado.ok || !resultado.dados) {
      definirAvisoReceita(resultado.mensagem ?? "Consulta indisponível.");
      return;
    }

    const d = resultado.dados;
    definirValores({
      razao_social: d.razao_social ?? "",
      nome_fantasia: d.nome_fantasia ?? "",
      cnpj: d.cnpj ?? cnpj,
      data_constituicao: d.data_constituicao ?? "",
      logradouro: d.logradouro ?? "",
      numero: d.numero ?? "",
      complemento: d.complemento ?? "",
      bairro: d.bairro ?? "",
      municipio: d.municipio ?? "",
      uf: d.uf ?? "",
      cep: d.cep ?? "",
      email: d.email ?? "",
      telefone: d.telefone ?? "",
    });
    // Natureza que o sistema não reconhece devolve null: manter a escolha de
    // quem está cadastrando é melhor do que trocá-la por um palpite.
    if (d.tipo_entidade) definirTipo(d.tipo_entidade);
    definirReceita(d);
    definirVersao((v) => v + 1);
  }

  async function enviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    definirErro(null);
    definirEnviando(true);

    const form = new FormData(evento.currentTarget);
    // Campo vazio vira ausência, não string vazia: o backend distingue "não
    // informado" de "informado como nada", e a diferença aparece no documento.
    const limpo = (chave: string) => {
      const valor = (form.get(chave) as string | null)?.trim();
      return valor ? valor : null;
    };

    const resultado = await criarEntidade({
      razao_social: limpo("razao_social"),
      nome_fantasia: limpo("nome_fantasia"),
      cnpj: limpo("cnpj"),
      tipo_entidade: tipo,
      data_constituicao: limpo("data_constituicao"),
      logradouro: limpo("logradouro"),
      numero: limpo("numero"),
      complemento: limpo("complemento"),
      bairro: limpo("bairro"),
      municipio: limpo("municipio"),
      uf: limpo("uf"),
      cep: limpo("cep"),
      email: limpo("email"),
      telefone: limpo("telefone"),
      site: limpo("site"),
    });

    if (!resultado.ok || !resultado.id) {
      definirErro(resultado.mensagem ?? "Falha ao cadastrar a entidade.");
      definirEnviando(false);
      return;
    }

    router.push(`/entidades/${resultado.id}`);
    router.refresh();
  }

  return (
    <form key={versao} onSubmit={enviar} className="space-y-7">
      <section className="space-y-4">
        <h2 className="text-[0.9375rem] font-semibold tracking-tight">Identificação</h2>

        <Campo
          rotulo="Razão social"
          name="razao_social" defaultValue={valores.razao_social ?? ""}
          required
          autoFocus
          placeholder="Associação Beneficente Exemplo"
          ajuda="O nome como constará do estatuto e do registro. Único campo obrigatório."
        />

        <div className="space-y-1.5">
          <label htmlFor="tipo" className="block text-[0.8125rem] font-medium text-[var(--color-tinta-2)]">
            Tipo de entidade
          </label>
          <select
            id="tipo"
            value={tipo}
            onChange={(e) => definirTipo(e.target.value)}
            className="w-full rounded-md border bg-[var(--color-superficie)] px-3 py-2 text-[0.875rem] text-[var(--color-tinta)]"
          >
            {TIPOS.map((t) => (
              <option key={t.valor} value={t.valor}>
                {t.rotulo}
              </option>
            ))}
          </select>
          {notaDoTipo && (
            <p className="text-[0.75rem] text-[var(--color-tinta-3)]">{notaDoTipo}</p>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Campo
            rotulo="Nome fantasia"
            name="nome_fantasia"
            defaultValue={valores.nome_fantasia ?? ""}
            placeholder="Opcional"
          />
          <div className="space-y-1.5">
            <label
              htmlFor="cnpj"
              className="block text-[0.8125rem] font-medium text-[var(--color-tinta-2)]"
            >
              CNPJ
            </label>
            <div className="flex gap-2">
              <input
                id="cnpj"
                name="cnpj"
                defaultValue={valores.cnpj ?? ""}
                inputMode="numeric"
                placeholder="00.000.000/0001-00"
                className="min-w-0 flex-1 rounded-md border bg-[var(--color-superficie)] px-3 py-2 text-[0.875rem] text-[var(--color-tinta)] placeholder:text-[var(--color-tinta-3)]"
              />
              <Botao variante="secundario" onClick={buscarNaReceita} disabled={consultando}>
                {consultando ? "Buscando…" : "Buscar"}
              </Botao>
            </div>
            <p className="text-[0.75rem] text-[var(--color-tinta-3)]">
              Com o CNPJ, <strong>Buscar</strong> preenche o cadastro pela base da
              Receita. Deixe vazio se a entidade ainda não foi registrada.
            </p>
          </div>
        </div>

        {avisoReceita && <Aviso tom="atencao">{avisoReceita}</Aviso>}

        {receita && (
          <Aviso
            tom={receita.situacao_exige_atencao ? "atencao" : "sucesso"}
            titulo={
              receita.situacao_exige_atencao
                ? `Situação cadastral: ${receita.situacao_cadastral}`
                : "Cadastro preenchido pela Receita Federal"
            }
          >
            {receita.situacao_exige_atencao && (
              <>
                A Receita registra este CNPJ como{" "}
                <strong>{receita.situacao_cadastral?.toLowerCase()}</strong>. Isso não
                impede o cadastro aqui, mas impede a maior parte dos atos registrais —
                confirme antes de seguir.{" "}
              </>
            )}
            {receita.natureza_juridica && (
              <>
                Natureza jurídica: <strong>{receita.natureza_juridica}</strong>.{" "}
                {!receita.tipo_entidade && (
                  <>
                    O sistema não converte essa natureza automaticamente — escolha o
                    tipo acima.{" "}
                  </>
                )}
              </>
            )}
            Confira campo a campo antes de gravar: a base fiscal atrasa em relação ao
            registro civil, e quem tem o estatuto na mão é você. Fonte: {receita.fonte}.
          </Aviso>
        )}

        <Campo
          rotulo="Data de constituição"
          name="data_constituicao" defaultValue={valores.data_constituicao ?? ""}
          type="date"
          ajuda="A data da assembleia de fundação. Vazio se ela ainda não aconteceu."
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-[0.9375rem] font-semibold tracking-tight">Sede</h2>
        <p className="-mt-2 text-[0.8125rem] text-[var(--color-tinta-3)]">
          O endereço entra nos documentos e determina o cartório competente. Pode
          ficar para depois.
        </p>

        <div className="grid gap-4 sm:grid-cols-[1fr_8rem]">
          <Campo rotulo="Logradouro" name="logradouro" defaultValue={valores.logradouro ?? ""} placeholder="Rua, avenida, praça" />
          <Campo rotulo="Número" name="numero" defaultValue={valores.numero ?? ""} />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo rotulo="Complemento" name="complemento" defaultValue={valores.complemento ?? ""} />
          <Campo rotulo="Bairro" name="bairro" defaultValue={valores.bairro ?? ""} />
        </div>
        <div className="grid gap-4 sm:grid-cols-[1fr_6rem_10rem]">
          <Campo rotulo="Município" name="municipio" defaultValue={valores.municipio ?? ""} />
          <div className="space-y-1.5">
            <label htmlFor="uf" className="block text-[0.8125rem] font-medium text-[var(--color-tinta-2)]">
              UF
            </label>
            <select
              id="uf"
              name="uf"
              defaultValue={valores.uf ?? ""}
              className="w-full rounded-md border bg-[var(--color-superficie)] px-3 py-2 text-[0.875rem] text-[var(--color-tinta)]"
            >
              <option value="">—</option>
              {UFS.map((uf) => (
                <option key={uf} value={uf}>
                  {uf}
                </option>
              ))}
            </select>
          </div>
          <Campo rotulo="CEP" name="cep" defaultValue={valores.cep ?? ""} inputMode="numeric" placeholder="00000-000" />
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-[0.9375rem] font-semibold tracking-tight">Contato</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <Campo rotulo="E-mail" name="email" defaultValue={valores.email ?? ""} type="email" />
          <Campo rotulo="Telefone" name="telefone" defaultValue={valores.telefone ?? ""} />
          <Campo rotulo="Site" name="site" placeholder="https://" />
        </div>
      </section>

      {erro && <Aviso tom="erro">{erro}</Aviso>}

      <div className="flex items-center gap-3 border-t pt-5">
        <Botao tipo="submit" disabled={enviando}>
          {enviando ? "Cadastrando…" : "Cadastrar entidade"}
        </Botao>
        <Botao variante="silencioso" onClick={() => router.back()} disabled={enviando}>
          Cancelar
        </Botao>
      </div>
    </form>
  );
}
