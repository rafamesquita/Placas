import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage

from app.config import EMAIL_DESTINATARIO, EMAIL_REMETENTE, EMAIL_SENHA

logger = logging.getLogger(__name__)


def enviar_email(pdf_path: str):
    """Envia o relatório PDF por e-mail via Gmail SMTP SSL."""
    if not all([EMAIL_REMETENTE, EMAIL_SENHA, EMAIL_DESTINATARIO]):
        raise ValueError(
            "Credenciais de e-mail incompletas. "
            "Verifique EMAIL_REMETENTE, EMAIL_SENHA e EMAIL_DESTINATARIO no arquivo .env."
        )

    data_hoje = datetime.now().strftime("%d/%m/%Y")
    nome_anexo = f"relatorio_{datetime.now().strftime('%Y%m%d')}.pdf"

    msg = EmailMessage()
    msg["Subject"] = f"Relatório de Placas — {data_hoje}"
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = EMAIL_DESTINATARIO
    msg.set_content(
        f"Olá,\n\n"
        f"Segue em anexo o relatório de passagem de veículos do dia {data_hoje}.\n\n"
        f"Atenciosamente,\nSistema de Leitura de Placas"
    )

    with open(pdf_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=nome_anexo,
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_REMETENTE, EMAIL_SENHA)
        smtp.send_message(msg)

    logger.info("E-mail enviado para %s com o anexo '%s'.", EMAIL_DESTINATARIO, nome_anexo)
