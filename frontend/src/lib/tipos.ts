/** Contratos da API do TERCEIRO360, espelhando o backend. */

export type Semaforo = "APTO" | "PENDENCIA" | "BLOQUEADO";
export type Prioridade = "URGENTE" | "ALTA" | "MEDIA" | "BAIXA";

export interface Fundamento {
  origem: string;
  referencia: string;
  dispositivo: string | null;
  trecho: string | null;
  versao_norma: string | null;
  /** §46 — se a redação já foi conferida por um responsável habilitado. */
  curado: boolean | null;
  url: string | null;
}

export interface Achado {
  codigo: string;
  severidade: Semaforo;
  icone: string;
  titulo: string;
  mensagem: string;
  campo: string | null;
  sugestao: string | null;
  fundamentos: Fundamento[];
  dados: Record<string, unknown>;
}

export interface ResultadoValidacao {
  semaforo: Semaforo;
  icone: string;
  pode_gerar_documentos: boolean;
  total_achados: number;
  bloqueios: number;
  pendencias: number;
  avaliado_em: string;
  achados: Achado[];
  campos_faltantes?: string[];
  checklist?: Checklist;
}

export interface ItemChecklist {
  codigo: string;
  descricao: string;
  obrigatorio: boolean;
  origem: string;
  origens: string[];
  fundamento: string | null;
  status: "PENDENTE" | "OK" | "NAO_APLICAVEL";
  observacao: string | null;
}

export interface Checklist {
  tipo_evento: string;
  completo: boolean;
  total: number;
  pendentes: number;
  avisos: string[];
  itens: ItemChecklist[];
}

export interface Usuario {
  id: string;
  nome: string;
  email: string;
  cliente_id: string;
  registro_profissional: string | null;
  permissoes: string[];
}

export interface EntidadeResumo {
  id: string;
  razao_social: string;
  nome_fantasia: string | null;
  cnpj: string | null;
  tipo_entidade: string;
  municipio: string | null;
  uf: string | null;
  ativa: boolean;
}

export interface CriterioScore {
  codigo: string;
  rotulo: string;
  peso: number;
  atingido: number;
  pontos: number;
  justificativa: string;
}

export interface Score {
  pontuacao: number;
  classificacao: "Excelente" | "Regular" | "Atenção" | "Risco elevado";
  cor: string;
  data_referencia: string;
  criterios: CriterioScore[];
}

export interface Pendencia {
  codigo: string;
  severidade: Semaforo;
  icone: string;
  titulo: string;
  descricao: string;
  prioridade: Prioridade;
  referencia: string | null;
  sugestao: string | null;
}

export interface Prazo {
  descricao: string;
  tipo: string;
  data_limite: string;
  dias_restantes: number;
  prioridade: Prioridade;
  origem: string;
  fundamento: string | null;
  vencido?: boolean;
  chave?: string;
}

export interface MembroDiretoria {
  nome: string;
  cargo: string;
}

export interface Dashboard {
  entidade: {
    id: string;
    razao_social: string;
    cnpj: string | null;
    tipo: string;
    municipio: string | null;
    uf: string | null;
    situacao_cadastral: string | null;
  };
  estatuto: {
    versao: number | null;
    data: string | null;
    registro: string | null;
    parametros_confirmados: number;
    parametros_totais: number;
  };
  diretoria: {
    gestao: string | null;
    vigente: boolean;
    inicio: string | null;
    fim: string | null;
    membros: MembroDiretoria[];
    cargos_vagos: string[];
  };
  score: Score;
  pendencias: Pendencia[];
  prazos: Prazo[];
  alertas: { descricao: string; janela_dias: number; data_limite: string }[];
  atos_em_andamento: {
    id: string;
    tipo: string;
    titulo: string | null;
    status: string;
    semaforo: Semaforo | null;
    data: string | null;
  }[];
}

/* ─────────────────────────────────────────── Matriz de atos e questionário */

export interface CampoQuestionario {
  nome: string;
  pergunta: string;
  tipo: "data" | "texto" | "numero" | "opcao" | "lista" | "booleano" | "pessoas";
  obrigatorio: boolean;
  opcoes: string[];
  ajuda: string | null;
  /** Parâmetro do estatuto exibido ao lado do campo como referência (§52). */
  referencia_estatutaria: string | null;
}

export interface Questionario {
  tipo_evento: string;
  titulo: string;
  campos: CampoQuestionario[];
}

export type ExigeReforma = "SEMPRE" | "NUNCA" | "DEPENDE_DO_ESTATUTO" | "NAO_APLICAVEL";
export type EspecieAssembleia =
  | "ORDINARIA"
  | "EXTRAORDINARIA"
  | "CONFORME_ESTATUTO"
  | "NAO_ASSEMBLEAR";

export interface Ato {
  tipo: string;
  titulo: string;
  categoria: string;
  descricao: string;
  orgao_competente: string;
  especie_assembleia: EspecieAssembleia;
  exige_reforma_estatutaria: ExigeReforma;
  exige_convocacao_especifica: boolean;
  chave_quorum: string | null;
  efeito_registral: "REGISTRO" | "AVERBACAO" | "INTERNO";
  assemblear: boolean;
  documentos: string[];
  fundamentos: { fonte: string; dispositivo: string }[];
  parametros_relevantes: string[];
  nota: string | null;
  alertas: string[];
}

export interface AtoDetalhado extends Ato {
  questionario: Questionario;
  parametros: { chave: string; rotulo: string; pergunta: string; nota: string | null }[];
}

export interface Evento {
  id: string;
  tipo: string;
  titulo: string | null;
  status: string;
  semaforo: Semaforo | null;
  data_referencia: string | null;
  dados: Record<string, unknown>;
}

export interface DocumentoResumo {
  id: string;
  tipo: string;
  categoria: string;
  titulo: string;
  status: StatusDocumento;
  versao_atual: number;
  data: string | null;
  evento_id: string | null;
  origem: string | null;
  template: string | null;
  assinaturas_pendentes: number;
}

export interface ResultadoGeracao {
  semaforo: Semaforo;
  gerados: {
    documento_id: string;
    tipo: string;
    titulo: string;
    versao: number;
    lacunas: string[];
  }[];
  sem_modelo_cadastrado: string[];
  ressalvas: Achado[];
}

/* ──────────────────────────────────── Central de Fontes Jurídicas (§38) */

export interface FonteResumo {
  id: string;
  chave: string;
  identificacao: string;
  apelido: string | null;
  tipo: string;
  jurisdicao: string;
  url_oficial: string | null;
  ementa: string | null;
  versao_vigente: number | null;
  vigente_desde: string | null;
  /** §46 — se a redação já foi conferida por responsável habilitado. */
  curada: boolean;
  curador: string | null;
  total_versoes: number;
}

export interface Dispositivo {
  identificacao: string;
  texto: string | null;
  tags: string[];
  revogado: boolean;
}

export interface VersaoNorma {
  numero: number;
  situacao: string;
  vigente_desde: string | null;
  vigente_ate: string | null;
  curada: boolean;
  resumo_alteracao: string | null;
  dispositivos?: Dispositivo[];
}

export interface FonteDetalhada {
  chave: string;
  identificacao: string;
  apelido: string | null;
  url_oficial: string | null;
  ementa: string | null;
  consultado_em: string;
  versao_aplicavel: VersaoNorma | null;
  historico: VersaoNorma[];
}

export interface Vigilia {
  id: string;
  nome: string;
  modo: "HTTP" | "MANUAL";
  url?: string | null;
  situacao: "EM_DIA" | "VENCIDA" | "ATRASADA" | "NUNCA_VERIFICADA";
  ultima_verificacao: string | null;
  periodicidade_dias: number;
  proxima_verificacao: string;
  ultimo_erro?: string | null;
  ativo?: boolean;
}

export interface AtualizacaoNormativa {
  id: string;
  titulo: string;
  situacao: "DETECTADA" | "EM_ANALISE" | "APROVADA" | "PUBLICADA" | "DESCARTADA";
  origem: string;
  resumo: string | null;
  detectado_em: string | null;
  publicado_em: string | null;
  url_evidencia: string | null;
  impactos_abertos: number;
  tem_diff: boolean;
}

export interface ImpactoNormativo {
  id: string;
  alvo_tipo: string;
  alvo_ref: string;
  severidade: string;
  descricao: string | null;
  status: string;
  norma: string | null;
  publicado_em: string | null;
}

export interface VinculoNormativo {
  id: string;
  alvo_tipo: string;
  alvo_ref: string;
  fonte_chave: string;
  dispositivo: string | null;
  observacao: string | null;
}

/* ─────────────────────────────────────────── Acervo documental (etapa 2.7) */

export type StatusDocumento =
  | "RASCUNHO" | "GERADO" | "REVISADO" | "APROVADO"
  | "ASSINADO" | "PROTOCOLADO" | "REGISTRADO" | "ARQUIVADO" | "CANCELADO";

export interface Assinatura {
  id: string;
  signatario: string;
  papel: string | null;
  tipo: string;
  status: "PENDENTE" | "ASSINADO" | "RECUSADO";
  reconhecimento_firma: boolean;
  data: string | null;
}

export interface VersaoDocumento {
  numero: number;
  criado_em: string;
  motivo: string | null;
  lacunas: number;
  hash: string | null;
}

export interface DocumentoDetalhado {
  id: string;
  tipo: string;
  titulo: string;
  status: StatusDocumento;
  versao_atual: number;
  conteudo: string | null;
  lacunas: string[];
  fundamentos: string[];
  versoes: VersaoDocumento[];
  assinaturas: Assinatura[];
}

/* ───────────────────────────────────────────────── Protocolos (etapa 2.7) */

export interface Exigencia {
  descricao: string;
  prazo: string | null;
  cumprida: boolean;
  lancada_em?: string;
  cumprida_em?: string;
  cumprida_por?: string;
  observacao?: string | null;
}

export interface Protocolo {
  id: string;
  numero: string | null;
  status: "PREPARACAO" | "PROTOCOLADO" | "EM_EXIGENCIA" | "REGISTRADO" | "DEVOLVIDO";
  evento_id: string;
  data_protocolo: string | null;
  data_registro: string | null;
  numero_registro: string | null;
  livro: string | null;
  folha: string | null;
  exigencias: Exigencia[];
  exigencias_abertas: number;
}

/* ────────────────────────────────────── Diretoria e associados (etapa 2.7) */

export interface MembroMandato {
  pessoa: string;
  cpf: string | null;
  cargo: string;
  situacao: "ATIVO" | "RENUNCIOU" | "DESTITUIDO" | "FALECIDO" | "AFASTADO";
}

export interface Mandato {
  id: string;
  designacao: string;
  orgao: string;
  data_inicio: string;
  data_fim: string;
  vigente: boolean;
  encerrado: boolean;
  membros: MembroMandato[];
}

export interface NoGovernanca {
  id: string;
  nome: string;
  tipo: string;
  codigo: string | null;
  responsaveis: { nome: string; cargo: string }[];
  mandato: string | null;
  filhos: NoGovernanca[];
}

export interface MapaGovernanca {
  entidade: string;
  orgaos: NoGovernanca[];
}

export interface Associado {
  id: string;
  pessoa: string;
  cpf: string | null;
  categoria: string | null;
  situacao: "ATIVO" | "SUSPENSO" | "DESLIGADO" | "LICENCIADO";
  direito_voto: boolean;
  elegivel: boolean;
  apto_hoje: boolean;
  data_admissao: string | null;
}

export interface QuadroAssociados {
  total: number;
  aptos_a_votar: number;
  associados: Associado[];
}

/* ───────────────────────────── Prazos, pendências e agendador (bloco 3) */

export interface PrazoRegistrado {
  id: string;
  tipo: string;
  descricao: string;
  data_limite: string;
  dias_restantes: number;
  status: "ABERTO" | "CUMPRIDO" | "VENCIDO" | "CANCELADO";
  origem: string;
  fundamento: string | null;
  alertas_disparados: number[];
  chave: string | null;
}

export interface PendenciaAberta {
  id: string;
  tipo: string;
  codigo: string | null;
  descricao: string;
  detalhamento: string | null;
  prioridade: Prioridade;
  status: string;
  origem: string;
  entidade: string | null;
  entidade_id: string | null;
  prazo_limite: string | null;
  criado_em: string;
}

export interface ExecucaoAgendador {
  id: string;
  tarefa: "VIGILIAS" | "PRAZOS";
  resultado: "OK" | "PARCIAL" | "ERRO";
  iniciada_em: string;
  concluida_em: string | null;
  duracao_s: number | null;
  numeros: Record<string, number>;
  falhas: { alvo: string; erro: string }[];
  detalhe: string | null;
  acionada_por: string;
}
