"""Registro único de modelos — importa todos os mapeamentos na ordem correta."""
from app.core.db import Base  # noqa: F401
from app.modules.identity.models import Cliente, Perfil, Usuario, UsuarioPerfil  # noqa: F401
from app.modules.entidades.models import Entidade, NaturezaJuridica  # noqa: F401
from app.modules.registral.models import (  # noqa: F401
    RCPJ,
    Checklist,
    ChecklistItem,
    Protocolo,
    RegraRCPJ,
)
from app.modules.documentos.models import (  # noqa: F401
    Assinatura,
    Certidao,
    Documento,
    DocumentoVersao,
    Template,
)
from app.modules.juridico.models import (  # noqa: F401
    Assembleia,
    Associado,
    Cargo,
    ConvocacaoAto,
    Deliberacao,
    Estatuto,
    EstatutoParametro,
    EstatutoVersao,
    Evento,
    Mandato,
    MandatoMembro,
    Orgao,
    ParecerJuridico,
    Pessoa,
    Presenca,
)
from app.modules.normativo.models import (  # noqa: F401
    AtualizacaoNormativa,
    Dispositivo,
    FonteJuridica,
    FonteVersao,
    ImpactoNormativo,
    MonitoramentoNormativo,
    VinculoNormativo,
)
from app.modules.prazos.models import Notificacao, Pendencia, Prazo  # noqa: F401
from app.modules.governanca.models import (  # noqa: F401
    ConfiguracaoScore,
    EventoLinhaTempo,
    ScoreSnapshot,
)
from app.modules.igrejas.models import (  # noqa: F401
    Ministro,
    ModeloGovernancaEclesiastica,
    UnidadeEclesiastica,
)
from app.modules.compliance.models import LogAcesso, RegistroAuditoria  # noqa: F401
from app.modules.agendador.models import ExecucaoTarefa  # noqa: F401
from app.modules.ia.models import AnaliseIA, SugestaoIA  # noqa: F401

__all__ = ["Base"]
