"""Importação de ata antiga: leitura, gravação e o caminho até a ata nova.

Duas atas, escritas como se escreve na prática: uma em lista ("Presidente:
NOME, brasileiro…") e outra corrida, com data por extenso ("aos dez dias do mês
de março de dois mil e vinte e quatro"). As duas têm uma armadilha: o
convocador da assembleia aparece como "Presidente, Sr. Fulano" sem ter sido
eleito.
"""
from __future__ import annotations

import datetime as dt
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.db import Base, get_db
from app.core.security import hash_senha
from app.main import app
from app.models import Base as ModelosBase  # noqa: F401
from app.modules.importacao.ata import cpf_valido, ler_ata, numero_por_extenso
from app.modules.importacao.servico import partir_endereco
from app.seeds.carga import popular

ATA_EM_LISTA = 'ATA DA ASSEMBLEIA GERAL ORDINÁRIA DA ASSOCIAÇÃO BENEFICENTE SÃO JOSÉ\n\nAos 15 (quinze) dias do mês de março de 2024, às 19h, na sede social, situada na Rua Laranjeiras, nº 45, Centro, Aracaju/SE, reuniram-se em Assembleia Geral Ordinária os associados da Associação Beneficente São José, inscrita no CNPJ sob o nº 10.724.882/0001-91, convocados por edital afixado na sede, com a presença de 32 (trinta e dois) associados, conforme lista de presença anexa. A Assembleia foi convocada pelo Presidente, Sr. Antônio Pereira, que assumiu a presidência dos trabalhos.\n\nApós a votação, foram eleitos para o mandato de 01/04/2024 a 31/03/2026 os seguintes membros:\n\nPresidente: JOSÉ CARLOS DOS SANTOS, brasileiro, casado, comerciante, portador da Cédula de Identidade RG nº 1.234.567 SSP/SE, inscrito no CPF sob o nº 529.982.247-25, residente e domiciliado na Rua das Flores, nº 120, Bairro Centro, Aracaju/SE, CEP 49010-000;\nVice-Presidente: MARIA DAS GRAÇAS OLIVEIRA, brasileira, viúva, professora aposentada, portadora do RG nº 2.345.678 SSP/SE, inscrita no CPF sob o nº 111.444.777-35, residente na Avenida Beira Mar, nº 500, apto 302, Bairro Treze de Julho, Aracaju/SE, CEP 49020-010;\n1º Secretário: PEDRO HENRIQUE ALVES, brasileiro, solteiro, estudante, portador do RG nº 3.456.789 SSP/SE, inscrito no CPF sob o nº 390.533.447-05, residente na Rua Itabaiana, nº 88, Bairro São José, Aracaju/SE, CEP 49015-110;\nTesoureira: ANA LÚCIA FERREIRA, brasileira, divorciada, contadora, portadora do RG nº 4.567.890 SSP/SE, residente na Rua Pacatuba, nº 210, Bairro Centro, Aracaju/SE, CEP 49010-150.\n\nNada mais havendo a tratar, foi lavrada a presente ata.\n'

ATA_CORRIDA = 'ATA DA ASSEMBLEIA GERAL EXTRAORDINÁRIA DA IGREJA EVANGÉLICA ASSEMBLEIA DE DEUS EM ESTÂNCIA\n\nAos dez dias do mês de março de dois mil e vinte e quatro, às dezenove horas, no templo sede, estando presentes quarenta e cinco membros, reuniu-se a Assembleia Geral Extraordinária, convocada pelo Pastor Presidente, Pr. Joel Martins, para eleição da nova Diretoria. Procedida a votação, foi eleita a Diretoria para o mandato com início em 1º de abril de 2024 e término em 31 de março de 2027, assim composta: para o cargo de Presidente, o Sr. Marcos Antônio Ribeiro, brasileiro, casado, pastor evangélico, portador do RG nº 987.654 SSP/SE, inscrito no CPF nº 862.247.360-06, residente e domiciliado na Rua João Pessoa, nº 15, Centro, Estância/SE, CEP 49200-000. Para o cargo de Secretária, a Sra. Débora Cristina Lima, brasileira, casada, auxiliar administrativa, portadora do RG nº 876.543 SSP/SE, inscrita no CPF nº 504.618.330-91, residente na Rua Capitão Salomão, nº 302, Bairro Alagoas, Estância/SE, CEP 49200-120. Para o cargo de Tesoureiro, o Sr. Elias Barbosa Neto, brasileiro, solteiro, comerciante, portador do RG nº 765.432 SSP/SE, inscrito no CPF nº 713.892.540-97, residente na Avenida Santo Antônio, nº 77, Bairro Cidade Nova, Estância/SE, CEP 49200-300.\n'


def _por_cargo(ata):
    return {p.cargo: p for p in ata.pessoas}


# ------------------------------------------------------------- Leitura


def test_ata_em_lista_traz_a_qualificacao_completa():
    ata = ler_ata(ATA_EM_LISTA)
    p = _por_cargo(ata)["Presidente"]
    assert p.nome == "José Carlos dos Santos"           # caixa alta vira nome próprio
    assert p.cpf == "529.982.247-25"
    assert (p.rg, p.orgao_expedidor) == ("1.234.567", "SSP/SE")
    assert (p.nacionalidade, p.estado_civil, p.profissao) == ("brasileiro", "casado", "comerciante")
    assert p.endereco == "Rua das Flores, nº 120, Bairro Centro, Aracaju/SE"
    assert p.cep == "49010-000"
    assert _por_cargo(ata)["Vice-Presidente"].profissao == "professora aposentada"
    assert "1º Secretário" in _por_cargo(ata)


def test_convocador_mencionado_nao_vira_eleito():
    for texto, convocador in ((ATA_EM_LISTA, "Antônio"), (ATA_CORRIDA, "Joel")):
        assert not any(convocador in (p.nome or "") for p in ler_ata(texto).pessoas)


def test_falta_de_cpf_e_avisada_e_nao_inventada():
    tesoureira = _por_cargo(ler_ata(ATA_EM_LISTA))["Tesoureira"]
    assert tesoureira.cpf is None
    assert any("CPF não encontrado" in a for a in tesoureira.avisos)


def test_datas_e_presenca_em_numero():
    ata = ler_ata(ATA_EM_LISTA)
    assert ata.data_assembleia == dt.date(2024, 3, 15)
    assert ata.total_presentes == 32
    assert (ata.mandato_inicio, ata.mandato_fim) == (dt.date(2024, 4, 1), dt.date(2026, 3, 31))


def test_ata_corrida_com_datas_e_numeros_por_extenso():
    ata = ler_ata(ATA_CORRIDA)
    assert ata.data_assembleia == dt.date(2024, 3, 10)  # "dois mil e vinte e quatro"
    assert ata.total_presentes == 45                     # "quarenta e cinco membros"
    assert (ata.mandato_inicio, ata.mandato_fim) == (dt.date(2024, 4, 1), dt.date(2027, 3, 31))
    assert [p.cargo for p in ata.pessoas] == ["Presidente", "Secretária", "Tesoureiro"]
    assert _por_cargo(ata)["Presidente"].profissao == "pastor evangélico"


def test_cpf_com_digito_errado_e_avisado():
    # Na ata corrida, o CPF da secretária foi deixado inválido de propósito.
    ata = _por_cargo(ler_ata(ATA_CORRIDA))
    assert any("dígitos verificadores" in a for a in ata["Secretária"].avisos)
    assert not any("dígitos verificadores" in a for a in ata["Presidente"].avisos)


def test_texto_sem_eleicao_avisa_em_vez_de_inventar():
    ata = ler_ata("Ata de reunião ordinária. Foram discutidos assuntos gerais do mês.")
    assert ata.pessoas == []
    assert any("Nenhum eleito" in a for a in ata.avisos)


@pytest.mark.parametrize("texto,valor", [
    ("dois mil e vinte e quatro", 2024), ("quarenta e cinco", 45), ("quinze", 15),
    ("primeiro", 1), ("mil novecentos e noventa e nove", 1999), ("32", 32),
])
def test_numero_por_extenso(texto, valor):
    assert numero_por_extenso(texto) == valor


def test_cpf_valido():
    assert cpf_valido("529.982.247-25") and not cpf_valido("529.982.247-26")


def test_endereco_e_separado_nos_campos_do_cadastro():
    assert partir_endereco("Avenida Beira Mar, nº 500, apto 302, Bairro Treze de Julho, Aracaju/SE") == {
        "logradouro": "Avenida Beira Mar", "numero": "500", "complemento": "apto 302",
        "bairro": "Treze de Julho", "municipio": "Aracaju", "uf": "SE",
    }
    # Bairro sem a palavra "Bairro" — o caso da ata corrida.
    assert partir_endereco("Rua João Pessoa, nº 15, Centro, Estância/SE")["bairro"] == "Centro"


# ------------------------------------------------------------- API real


@pytest.fixture(scope="module")
def api(tmp_path_factory):
    caminho = tmp_path_factory.mktemp("banco") / "importacao.db"
    engine = create_engine(f"sqlite+pysqlite:///{caminho}", connect_args={"check_same_thread": False})
    Sessao = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    with Sessao() as db:
        popular(db, com_demonstracao=True)
        from app.modules.identity.models import Cliente, Perfil, Usuario, UsuarioPerfil
        from app.modules.juridico.models import Pessoa

        demo = db.scalar(select(Cliente).where(Cliente.nome == "Escritório Demonstração"))
        # Já cadastrada, com profissão diferente da ata e sem RG: o RG deve ser
        # preenchido; a profissão não pode ser trocada sem a pessoa decidir.
        db.add(Pessoa(cliente_id=demo.id, nome="Maria das Graças Oliveira",
                      cpf="111.444.777-35", profissao="professora"))
        leitor = Usuario(cliente_id=demo.id, nome="Leitor", email="leitor@demo.local",
                         senha_hash=hash_senha("senha-do-leitor-123"))
        db.add(leitor); db.flush()
        perfil = db.scalar(select(Perfil).where(Perfil.cliente_id.is_(None), Perfil.codigo == "VISUALIZADOR"))
        db.add(UsuarioPerfil(usuario_id=leitor.id, perfil_id=perfil.id))
        db.commit()

    def _db():
        db = Sessao()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    with TestClient(app) as cliente:
        def entrar(email, senha):
            r = cliente.post("/api/v1/auth/login", data={"username": email, "password": senha})
            return {"Authorization": f"Bearer {r.json()['access_token']}"}
        admin = entrar("admin@demo.terceiro360.local", "terceiro360")
        entidade = cliente.get("/api/v1/entidades", headers=admin).json()[0]["id"]
        yield {"c": cliente, "admin": admin, "leitor": entrar("leitor@demo.local", "senha-do-leitor-123"),
               "ent": entidade, "Sessao": Sessao}
    app.dependency_overrides.clear()


def _url(api, fim):
    return f"/api/v1/entidades/{api['ent']}/importar-ata/{fim}"


def test_ler_texto_pela_api(api):
    r = api["c"].post(_url(api, "ler"), headers=api["admin"], json={"texto": ATA_EM_LISTA})
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert len(corpo["pessoas"]) == 4
    assert corpo["mandato_inicio"] == "2024-04-01"
    assert corpo["pessoas"][0]["trecho"].startswith("Presidente: JOSÉ CARLOS")


def test_ler_arquivo_word(api):
    from docx import Document

    documento = Document()
    for paragrafo in ATA_EM_LISTA.split("\n"):
        documento.add_paragraph(paragrafo)
    buffer = io.BytesIO(); documento.save(buffer)
    r = api["c"].post(_url(api, "ler-arquivo"), headers=api["admin"],
                      files={"arquivo": ("ata.docx", buffer.getvalue())})
    assert r.status_code == 200, r.text
    assert len(r.json()["pessoas"]) == 4


def test_pdf_escaneado_e_foto_explicam_por_que_nao_leem(api):
    from fpdf import FPDF

    pdf = FPDF(); pdf.add_page()              # página sem texto: como um escaneado
    r = api["c"].post(_url(api, "ler-arquivo"), headers=api["admin"],
                      files={"arquivo": ("ata.pdf", bytes(pdf.output()))})
    assert r.status_code == 422 and "escaneada" in r.json()["detail"]

    r = api["c"].post(_url(api, "ler-arquivo"), headers=api["admin"],
                      files={"arquivo": ("ata.jpg", b"\xff\xd8\xff")})
    assert r.status_code == 415 and "Foto" in r.json()["detail"]


def test_quem_so_visualiza_nao_importa(api):
    r = api["c"].post(_url(api, "ler"), headers=api["leitor"], json={"texto": ATA_EM_LISTA})
    assert r.status_code == 403


def _gravar(api, registrar=True):
    lidas = api["c"].post(_url(api, "ler"), headers=api["admin"], json={"texto": ATA_EM_LISTA}).json()
    campos = ("nome", "cargo", "cpf", "rg", "orgao_expedidor", "nacionalidade", "estado_civil",
              "profissao", "endereco", "cep")
    r = api["c"].post(_url(api, "gravar"), headers=api["admin"], json={
        "pessoas": [{k: p[k] for k in campos} for p in lidas["pessoas"]],
        "registrar_diretoria": registrar,
        "mandato_inicio": lidas["mandato_inicio"], "mandato_fim": lidas["mandato_fim"],
    })
    assert r.status_code == 200, r.text
    return r.json()


def test_gravar_cria_pessoas_e_diretoria_sem_sobrescrever_cadastro(api):
    r = _gravar(api)
    assert set(r["pessoas_criadas"]) == {"José Carlos dos Santos", "Pedro Henrique Alves", "Ana Lúcia Ferreira"}
    # Maria já existia: ganhou o RG que faltava, mas a profissão não foi trocada.
    completada = next(c for c in r["pessoas_completadas"] if c["pessoa"] == "Maria das Graças Oliveira")
    assert "rg" in completada["campos"]
    assert {"pessoa": "Maria das Graças Oliveira", "campo": "profissao",
            "no_cadastro": "professora", "na_ata": "professora aposentada"} in r["conflitos"]
    assert r["mandatos"] == [{"orgao": "Diretoria", "designacao": "GESTÃO 2024–2026", "criado": True}]
    assert r["membros_incluidos"] == 4

    from app.modules.juridico.models import Pessoa
    with api["Sessao"]() as db:
        jose = db.scalar(select(Pessoa).where(Pessoa.nome == "José Carlos dos Santos"))
        assert (jose.cpf, jose.rg, jose.orgao_expedidor) == ("529.982.247-25", "1.234.567", "SSP/SE")
        assert (jose.logradouro, jose.numero, jose.bairro, jose.municipio, jose.uf, jose.cep) == (
            "Rua das Flores", "120", "Centro", "Aracaju", "SE", "49010-000")
        maria = db.scalar(select(Pessoa).where(Pessoa.nome == "Maria das Graças Oliveira"))
        assert maria.profissao == "professora"


def test_gravar_de_novo_nao_duplica(api):
    r = _gravar(api)
    assert r["pessoas_criadas"] == []
    assert r["membros_incluidos"] == 0
    assert r["mandatos"] == [{"orgao": "Diretoria", "designacao": "GESTÃO 2024–2026", "criado": False}]


def test_pessoa_importada_sai_com_cpf_na_ata_nova_mesmo_digitada_so_pelo_nome(api):
    """O questionário manda "cpf": "" quando o eleito é digitado só pelo nome.
    O cadastro completava só o campo ausente — e a ata nova saía sem CPF."""
    c, h = api["c"], api["admin"]
    ev = c.post(f"/api/v1/entidades/{api['ent']}/eventos", headers=h, json={
        "tipo": "REELEICAO_DIRETORIA", "data_referencia": "2026-03-20",
        "dados": {"data_ato": "2026-03-20", "eleitos": [
            {"nome": "José Carlos dos Santos", "cargo": "Presidente", "cpf": ""}],
            "mandato_inicio": "2026-04-01", "mandato_fim": "2028-03-31"},
    }).json()["id"]
    gerados = c.post(f"/api/v1/eventos/{ev}/gerar-documentos?forcar=true", headers=h).json()["gerados"]
    ata = next(g for g in gerados if g["tipo"] == "ATA")
    texto = c.get(f"/api/v1/documentos/{ata['documento_id']}", headers=h).json()["conteudo"]
    assert "529.982.247-25" in texto


def test_campo_opcional_vazio_nao_deixa_documento_em_branco(api):
    """Data da posse é opcional. Sem ela, o termo de posse saía vazio e era
    gravado como gerado. Agora sai completo, com a lacuna apontada."""
    c, h = api["c"], api["admin"]
    ev = c.post(f"/api/v1/entidades/{api['ent']}/eventos", headers=h, json={
        "tipo": "REELEICAO_DIRETORIA", "data_referencia": "2026-03-20",
        "dados": {"data_ato": "2026-03-20", "eleitos": [{"nome": "Pedro Henrique Alves", "cargo": "Secretário"}],
                  "mandato_inicio": "2026-04-01", "mandato_fim": "2028-03-31"},
    }).json()["id"]
    r = c.post(f"/api/v1/eventos/{ev}/gerar-documentos?forcar=true", headers=h).json()
    assert r["falharam"] == []
    for g in r["gerados"]:
        conteudo = c.get(f"/api/v1/documentos/{g['documento_id']}", headers=h).json()["conteudo"]
        assert conteudo.strip(), f"{g['tipo']} saiu em branco"
    termo = next(g for g in r["gerados"] if g["tipo"] == "TERMO_POSSE")
    assert "DATA_POSSE" in termo["lacunas"]
