import logging
import re
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Padrão antigo (ABC-1234) e Mercosul (ABC1D23)
_PADRAO_PLACA = re.compile(
    r"^[A-Z]{3}[0-9]{4}$"       # padrão antigo  → AAA9999
    r"|^[A-Z]{3}[0-9][A-Z][0-9]{2}$"  # Mercosul  → AAA9A99
)

_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(["en", "pt"], gpu=False)
        logger.info("EasyOCR inicializado.")
    return _reader


def _normalizar(texto: str) -> str:
    """Remove caracteres fora do conjunto alfanumérico e converte para maiúsculas."""
    limpo = re.sub(r"[^A-Z0-9]", "", texto.upper())
    # Corrige confusões comuns de OCR em placas brasileiras
    substituicoes = {"O": "0", "I": "1", "S": "5", "B": "8"}
    resultado = []
    for i, c in enumerate(limpo):
        # Posições 0-2: letras → converte dígitos que parecem letras
        # Posições 3-6 (antigo) / 3,5,6 (Mercosul): dígitos → converte letras que parecem dígitos
        if i < 3 and c.isdigit():
            resultado.append(c)  # mantém; será validado depois
        elif i >= 3 and c.isalpha() and c in substituicoes:
            resultado.append(substituicoes[c])
        else:
            resultado.append(c)
    return "".join(resultado)


def ler_placa(imagem: np.ndarray) -> Optional[str]:
    """
    Recebe um crop (BGR ou cinza) da placa e retorna o texto identificado,
    validado contra o padrão de placas brasileiras, ou None se inválido.
    """
    reader = _get_reader()

    resultados = reader.readtext(imagem, detail=0, paragraph=False)
    if not resultados:
        return None

    texto_bruto = "".join(resultados)
    texto = _normalizar(texto_bruto)

    if len(texto) < 7:
        logger.debug("OCR retornou texto curto demais: '%s'", texto_bruto)
        return None

    candidato = texto[:7]

    if _PADRAO_PLACA.match(candidato):
        return candidato

    logger.debug("Texto '%s' não corresponde ao padrão de placa.", candidato)
    return None
