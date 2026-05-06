import logging

import cv2
import numpy as np

from app.config import (
    CANNY_HIGH,
    CANNY_LOW,
    DETECC_MAX_CANDIDATOS,
    DETECC_MAX_LARGURA,
    DETECC_NMS_IOU,
    DETECC_USAR_MASCARA_BRANCO,
    PLACA_AREA_MAX_FRAC,
    PLACA_AREA_MIN_FRAC,
    PLACA_ASPECT_MAX,
    PLACA_ASPECT_MIN,
)

logger = logging.getLogger(__name__)


def _work_frame(
    frame: np.ndarray, max_largura: int
) -> tuple[np.ndarray, float, float]:
    """Reduz largura para acelerar; retorna (work_bgr, scale_x, scale_y) p/ mapear caixas."""
    h, w = frame.shape[:2]
    if max_largura <= 0 or w <= max_largura:
        return frame, 1.0, 1.0
    nw = max_largura
    nh = max(1, int(round(h * (max_largura / w))))
    work = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
    return work, w / nw, h / nh


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    ua = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / ua if ua > 0 else 0.0


def _nms(
    boxes: list[tuple[int, int, int, int]],
    scores: list[float],
    iou_thresh: float,
    max_keep: int,
) -> list[tuple[int, int, int, int]]:
    if not boxes:
        return []
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    keep: list[tuple[int, int, int, int]] = []
    for i in order:
        b = boxes[i]
        if all(_iou(b, k) < iou_thresh for k in keep):
            keep.append(b)
            if len(keep) >= max_keep:
                break
    return keep


def _score_aspect(ar: float) -> float:
    """Prefere proporções próximas às placas retangulares (~3,1:1)."""
    alvo = 3.15
    return max(0.0, 1.0 - min(abs(ar - alvo) / 4.0, 1.0))


def _caixas_por_bordas(
    work: np.ndarray,
    scale_x: float,
    scale_y: float,
    min_area: float,
    max_area: float,
) -> list[tuple[tuple[int, int, int, int], float]]:
    gray = cv2.cvtColor(work, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    edges = cv2.Canny(gray, CANNY_LOW, CANNY_HIGH)
    sh, sw = gray.shape
    kw = max(15, sw // 18)
    kh = max(3, sh // 100)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kw, kh))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(
        closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    out: list[tuple[tuple[int, int, int, int], float]] = []
    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bh < 10 or bw < 24:
            continue
        ar = bw / float(bh)
        if ar < PLACA_ASPECT_MIN or ar > PLACA_ASPECT_MAX:
            continue
        x0 = int(x * scale_x)
        y0 = int(y * scale_y)
        x1 = int((x + bw) * scale_x)
        y1 = int((y + bh) * scale_y)
        w0, h0 = x1 - x0, y1 - y0
        area0 = float(w0 * h0)
        if area0 < min_area or area0 > max_area:
            continue
        ca = cv2.contourArea(cnt) * scale_x * scale_y
        if ca < 0.08 * area0:
            continue
        score = _score_aspect(ar) + 0.15 * min(ca / area0, 1.0)
        out.append(((x0, y0, x1, y1), score))
    return out


def _caixas_por_mascara_clara(
    work: np.ndarray,
    scale_x: float,
    scale_y: float,
    min_area: float,
    max_area: float,
) -> list[tuple[tuple[int, int, int, int], float]]:
    """Regiões claras e pouco saturadas (fundo reflexivo típico de placa)."""
    hsv = cv2.cvtColor(work, cv2.COLOR_BGR2HSV)
    lower = np.array([0, 0, 130])
    upper = np.array([180, 90, 255])
    mask = cv2.inRange(hsv, lower, upper)
    sh, sw = mask.shape
    k = max(9, sw // 25)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, max(5, sh // 25)))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    out: list[tuple[tuple[int, int, int, int], float]] = []
    for cnt in contours:
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bh < 10 or bw < 24:
            continue
        ar = bw / float(bh)
        if ar < PLACA_ASPECT_MIN or ar > PLACA_ASPECT_MAX:
            continue
        x0 = int(x * scale_x)
        y0 = int(y * scale_y)
        x1 = int((x + bw) * scale_x)
        y1 = int((y + bh) * scale_y)
        area0 = float((x1 - x0) * (y1 - y0))
        if area0 < min_area or area0 > max_area:
            continue
        ca = cv2.contourArea(cnt) * scale_x * scale_y
        if ca < 0.12 * area0:
            continue
        score = _score_aspect(ar) + 0.1 * min(ca / area0, 1.0)
        out.append(((x0, y0, x1, y1), score))
    return out


def _expandir_e_clampar(
    x1: int, y1: int, x2: int, y2: int, w: int, h: int, pad_frac: float = 0.08
) -> tuple[int, int, int, int]:
    pw = int((x2 - x1) * pad_frac)
    ph = int((y2 - y1) * pad_frac)
    x1 = max(0, x1 - pw)
    y1 = max(0, y1 - ph)
    x2 = min(w, x2 + pw)
    y2 = min(h, y2 + ph)
    return x1, y1, x2, y2


def detectar_placas(frame: np.ndarray) -> list[np.ndarray]:
    """
    Localiza regiões candidatas a placa sem rede neural: Canny + fechamento
    morfológico (bordas horizontais da placa) e, opcionalmente, máscara HSV
    para fundo claro. Retorna recortes BGR do frame original.
    """
    if frame is None or frame.size == 0:
        return []

    h, w = frame.shape[:2]
    frame_area = float(h * w)
    min_area = PLACA_AREA_MIN_FRAC * frame_area
    max_area = PLACA_AREA_MAX_FRAC * frame_area

    work, sx, sy = _work_frame(frame, DETECC_MAX_LARGURA)
    candidatos: list[tuple[tuple[int, int, int, int], float]] = []
    candidatos.extend(_caixas_por_bordas(work, sx, sy, min_area, max_area))
    if DETECC_USAR_MASCARA_BRANCO:
        candidatos.extend(
            _caixas_por_mascara_clara(work, sx, sy, min_area, max_area)
        )

    if not candidatos:
        return []

    boxes = [c[0] for c in candidatos]
    scores = [c[1] for c in candidatos]
    kept = _nms(boxes, scores, DETECC_NMS_IOU, DETECC_MAX_CANDIDATOS)

    crops: list[np.ndarray] = []
    for x1, y1, x2, y2 in kept:
        x1, y1, x2, y2 = _expandir_e_clampar(x1, y1, x2, y2, w, h)
        if x2 <= x1 or y2 <= y1:
            continue
        crop = frame[y1:y2, x1:x2]
        if crop.size > 0:
            crops.append(crop)
            logger.debug("Candidato a placa bbox=(%d,%d,%d,%d)", x1, y1, x2, y2)

    return crops


def pre_processar_placa(crop: np.ndarray) -> np.ndarray:
    """
    Pré-processamento do recorte para melhorar a acurácia do OCR:
    redimensiona, converte para cinza e aplica limiarização adaptativa.
    """
    altura_alvo = 64
    proporcao = altura_alvo / crop.shape[0]
    largura_alvo = int(crop.shape[1] * proporcao)
    redimensionado = cv2.resize(
        crop, (largura_alvo, altura_alvo), interpolation=cv2.INTER_CUBIC
    )

    cinza = cv2.cvtColor(redimensionado, cv2.COLOR_BGR2GRAY)
    processado = cv2.adaptiveThreshold(
        cinza,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=11,
        C=2,
    )
    return processado
