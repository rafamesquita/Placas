import logging
import os

import cv2
import numpy as np
from ultralytics import YOLO

from app.config import YOLO_CONFIANCA, YOLO_IMGSZ, YOLO_MODEL_PATH

logger = logging.getLogger(__name__)

_model: YOLO | None = None


def _get_model() -> YOLO:
    global _model
    if _model is not None:
        return _model

    path = os.path.abspath(YOLO_MODEL_PATH)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Modelo YOLO não encontrado em: {path}\n"
            "Coloque um arquivo .pt (YOLOv8 treinado para placas) em models/ "
            "e ajuste YOLO_MODEL_PATH no .env."
        )

    _model = YOLO(path)
    logger.info("Modelo YOLOv8 carregado: %s", path)
    return _model


def detectar_placas(frame: np.ndarray) -> list[np.ndarray]:
    """
    Recebe um frame BGR e retorna uma lista de crops (recortes) de placas detectadas.
    Cada crop é um np.ndarray BGR pronto para ser passado ao OCR.
    """
    model = _get_model()
    results = model.predict(
        source=frame,
        conf=YOLO_CONFIANCA,
        imgsz=YOLO_IMGSZ,
        verbose=False,
    )

    crops: list[np.ndarray] = []
    h, w = frame.shape[:2]

    if not results:
        return crops

    r = results[0]
    if r.boxes is None or len(r.boxes) == 0:
        return crops

    for box in r.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        conf = float(box.conf[0])

        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)

        crop = frame[y1:y2, x1:x2]
        if crop.size > 0:
            logger.debug(
                "Placa detectada — conf: %.2f  bbox: (%d,%d,%d,%d)",
                conf,
                x1,
                y1,
                x2,
                y2,
            )
            crops.append(crop)

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
