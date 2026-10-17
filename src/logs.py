
import logging
from pathlib import Path


# A raiz do projeto é a pasta acima de src.
PASTA_PROJETO = Path(__file__).resolve().parent.parent
ARQUIVO_LOG = PASTA_PROJETO / "logs_quedas.txt"

logger = logging.getLogger("monitoramento")
logger.setLevel(logging.INFO)
logger.propagate = False

# Evita registrar a mesma mensagem em handlers duplicados.
if not logger.handlers:
    formato = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
    )

    handler = logging.FileHandler(
        ARQUIVO_LOG,
        encoding="utf-8",
    )
    handler.setFormatter(formato)
    logger.addHandler(handler)


def registrar_log(mensagem):
    """Registra mensagens de monitoramento no arquivo de histórico."""
    if "[ERRO]" in mensagem:
        logger.error(mensagem)
    elif "[ALERTA]" in mensagem:
        logger.warning(mensagem)
    else:
        logger.info(mensagem)
