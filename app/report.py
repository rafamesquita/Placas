import logging
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.config import REPORTS_PATH

os.makedirs(REPORTS_PATH, exist_ok=True)

logger = logging.getLogger(__name__)

_VERDE = colors.HexColor("#2e7d32")
_VERMELHO = colors.HexColor("#c62828")
_CINZA_CLARO = colors.HexColor("#f5f5f5")
_CINZA_TITULO = colors.HexColor("#424242")


def _estilo_status(cadastrada: int) -> str:
    if cadastrada:
        return '<font color="#2e7d32"><b>CADASTRADA</b></font>'
    return '<font color="#c62828"><b>NÃO CADASTRADA</b></font>'


def gerar_pdf(dados: list) -> str:
    """
    Gera o PDF do relatório diário.

    Parâmetros
    ----------
    dados : list of (placa, data_hora, imagem_path, cadastrada)

    Retorna
    -------
    str : caminho do arquivo PDF gerado
    """
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    nome_arquivo = os.path.join(
        REPORTS_PATH,
        f"relatorio_{datetime.now().strftime('%Y%m%d')}.pdf",
    )

    doc = SimpleDocTemplate(
        nome_arquivo,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        "titulo",
        parent=styles["Title"],
        fontSize=18,
        textColor=_CINZA_TITULO,
        spaceAfter=0.3 * cm,
    )
    estilo_subtitulo = ParagraphStyle(
        "subtitulo",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.grey,
        spaceAfter=0.8 * cm,
    )
    estilo_placa = ParagraphStyle(
        "placa",
        parent=styles["Normal"],
        fontSize=13,
        leading=18,
        spaceAfter=0.2 * cm,
    )
    estilo_detalhe = ParagraphStyle(
        "detalhe",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=0.5 * cm,
    )

    total = len(dados)
    cadastradas = sum(1 for _, _, _, c in dados if c)

    # Cabeçalho do relatório
    story = [
        Paragraph("Relatório de Passagem de Veículos", estilo_titulo),
        Paragraph(
            f"Data: {data_hoje}  |  Total: {total} registro(s)  |  "
            f"Cadastradas: {cadastradas}  |  Desconhecidas: {total - cadastradas}",
            estilo_subtitulo,
        ),
        _tabela_resumo(dados),
        Spacer(1, 1 * cm),
    ]

    # Detalhes com foto de cada detecção
    for placa, data_hora, imagem_path, cadastrada in dados:
        dt = datetime.fromisoformat(data_hora)
        hora_fmt = dt.strftime("%H:%M:%S")

        story.append(
            Paragraph(
                f"<b>{placa}</b>  {_estilo_status(cadastrada)}",
                estilo_placa,
            )
        )
        story.append(
            Paragraph(f"Horário: {hora_fmt}", estilo_detalhe)
        )

        if imagem_path and os.path.exists(imagem_path):
            try:
                img = Image(imagem_path, width=12 * cm, height=7 * cm)
                img.hAlign = "LEFT"
                story.append(img)
            except Exception as exc:
                logger.warning("Não foi possível inserir imagem '%s': %s", imagem_path, exc)
                story.append(Paragraph(f"[imagem indisponível: {imagem_path}]", estilo_detalhe))

        story.append(Spacer(1, 0.6 * cm))

    doc.build(story)
    logger.info("PDF gerado: %s", nome_arquivo)
    return nome_arquivo


def _tabela_resumo(dados: list) -> Table:
    cabecalho = [["Placa", "Horário", "Status"]]
    linhas = []
    for placa, data_hora, _, cadastrada in dados:
        dt = datetime.fromisoformat(data_hora)
        linhas.append([
            placa,
            dt.strftime("%H:%M:%S"),
            "Cadastrada" if cadastrada else "Desconhecida",
        ])

    tabela = Table(
        cabecalho + linhas,
        colWidths=[5 * cm, 4 * cm, 5 * cm],
    )
    tabela.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _CINZA_TITULO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _CINZA_CLARO]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    return tabela
