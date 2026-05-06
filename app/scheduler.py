import logging
import time

import schedule

from app.config import HORARIO_RELATORIO
from app.database import listar_deteccoes_dia
from app.email_sender import enviar_email
from app.report import gerar_pdf

logger = logging.getLogger(__name__)


def job():
    logger.info("Iniciando geração do relatório diário...")
    dados = listar_deteccoes_dia()

    if not dados:
        logger.info("Nenhuma detecção registrada hoje. Relatório não enviado.")
        return

    try:
        pdf = gerar_pdf(dados)
        enviar_email(pdf)
        logger.info("Relatório diário enviado com sucesso.")
    except Exception:
        logger.exception("Erro ao gerar/enviar o relatório diário.")


def start():
    schedule.every().day.at(HORARIO_RELATORIO).do(job)
    logger.info("Scheduler iniciado. Relatório será enviado às %s.", HORARIO_RELATORIO)

    while True:
        schedule.run_pending()
        time.sleep(30)
