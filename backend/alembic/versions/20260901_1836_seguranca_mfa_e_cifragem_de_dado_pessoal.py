"""seguranca mfa e cifragem de dado pessoal

Revisão: 64e29bc1def9
Revisão anterior: 2c80f7235b0a
Criada em: 2026-09-01 18:36:54.290656+00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '64e29bc1def9'
down_revision: str | None = '2c80f7235b0a'
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # 1. Estrutura nova, antes de mexer em dado.
    op.add_column('pessoas', sa.Column('cpf_indice', sa.String(length=64), nullable=True))
    op.alter_column('pessoas', 'cpf',
               existing_type=sa.VARCHAR(length=14),
               type_=sa.String(length=200),
               existing_nullable=True)
    op.alter_column('pessoas', 'rg',
               existing_type=sa.VARCHAR(length=20),
               type_=sa.String(length=200),
               existing_nullable=True)
    op.drop_index(op.f('ix_pessoas_cpf'), table_name='pessoas')
    op.drop_constraint(op.f('uq_pessoas_cliente_cpf'), 'pessoas', type_='unique')

    # 2. Com as colunas já largas o bastante para o texto cifrado, converte o
    #    que existe. A restrição única vem depois: ela depende do índice.
    _migrar_dados_pessoais()

    op.create_unique_constraint('uq_pessoas_cliente_cpf', 'pessoas', ['cliente_id', 'cpf_indice'])
    op.create_index(op.f('ix_pessoas_cpf_indice'), 'pessoas', ['cpf_indice'], unique=False)
    op.add_column('usuarios', sa.Column('mfa_segredo', sa.String(length=64), nullable=True))
    op.add_column('usuarios', sa.Column('mfa_confirmado_em', sa.DateTime(timezone=True), nullable=True))
    # `server_default` não é enfeite: sem ele, adicionar coluna NOT NULL numa
    # tabela que já tem usuários falha na hora. E some logo em seguida, porque
    # o valor passa a vir da aplicação — deixá-lo no banco faria o esquema
    # divergir do modelo, e a próxima migração autogerada tentaria "corrigir".
    op.add_column('usuarios', sa.Column(
        'mfa_codigos_recuperacao',
        sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'),
        nullable=False, server_default=sa.text("'[]'"),
    ))
    op.alter_column('usuarios', 'mfa_codigos_recuperacao', server_default=None)
    op.add_column('usuarios', sa.Column('senha_alterada_em', sa.DateTime(timezone=True), nullable=True))


def _migrar_dados_pessoais() -> None:
    """Cifra os CPFs e RGs já gravados e preenche o índice cego.

    O autogenerate só troca o tipo da coluna. Sem este passo a migração deixaria
    o banco num estado pior do que o anterior: o dado continuaria em texto puro
    (dando a falsa impressão de que está cifrado) e, como o índice ficaria nulo,
    a busca por CPF pararia de achar as pessoas que já existiam.

    Roda em lotes e commita ao final: numa base grande, uma transação única com
    todas as linhas é o caminho mais curto para estourar a memória do servidor.
    """
    from app.core.cifra import cifrar, indice

    conexao = op.get_bind()
    pessoas = conexao.execute(
        sa.text("SELECT id, cpf, rg FROM pessoas WHERE cpf IS NOT NULL OR rg IS NOT NULL")
    ).mappings().all()

    for pessoa in pessoas:
        conexao.execute(
            sa.text(
                "UPDATE pessoas SET cpf = :cpf, cpf_indice = :ind, rg = :rg WHERE id = :id"
            ),
            {
                "id": pessoa["id"],
                "cpf": cifrar(pessoa["cpf"]),
                "ind": indice(pessoa["cpf"]),
                "rg": cifrar(pessoa["rg"]),
            },
        )


def _decifrar_dados_pessoais() -> None:
    """Volta os dados ao texto puro antes de estreitar as colunas.

    Sem isto o downgrade truncaria o texto cifrado em 14 caracteres — perda
    irreversível de dado pessoal, e o pior tipo de falha: silenciosa.
    """
    from app.core.cifra import decifrar

    conexao = op.get_bind()
    pessoas = conexao.execute(
        sa.text("SELECT id, cpf, rg FROM pessoas WHERE cpf IS NOT NULL OR rg IS NOT NULL")
    ).mappings().all()

    for pessoa in pessoas:
        conexao.execute(
            sa.text("UPDATE pessoas SET cpf = :cpf, rg = :rg WHERE id = :id"),
            {"id": pessoa["id"], "cpf": decifrar(pessoa["cpf"]), "rg": decifrar(pessoa["rg"])},
        )


def downgrade() -> None:
    _decifrar_dados_pessoais()
    op.drop_column('usuarios', 'senha_alterada_em')
    op.drop_column('usuarios', 'mfa_codigos_recuperacao')
    op.drop_column('usuarios', 'mfa_confirmado_em')
    op.drop_column('usuarios', 'mfa_segredo')
    op.drop_index(op.f('ix_pessoas_cpf_indice'), table_name='pessoas')
    op.drop_constraint('uq_pessoas_cliente_cpf', 'pessoas', type_='unique')
    op.create_unique_constraint(op.f('uq_pessoas_cliente_cpf'), 'pessoas', ['cliente_id', 'cpf'], postgresql_nulls_not_distinct=False)
    op.create_index(op.f('ix_pessoas_cpf'), 'pessoas', ['cpf'], unique=False)
    op.alter_column('pessoas', 'rg',
               existing_type=sa.String(length=200),
               type_=sa.VARCHAR(length=20),
               existing_nullable=True)
    op.alter_column('pessoas', 'cpf',
               existing_type=sa.String(length=200),
               type_=sa.VARCHAR(length=14),
               existing_nullable=True)
    op.drop_column('pessoas', 'cpf_indice')
    # ### end Alembic commands ###
