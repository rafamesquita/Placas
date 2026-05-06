import logging
import os
import threading
import time
from datetime import datetime

import cv2

from app.config import (
    CAMERA_BAD_FRAMES_REOPEN,
    CAMERA_INDEX,
    CAMERA_RECONNECT_SEC,
    IMAGES_PATH,
    COOLDOWN_PLACA,
)
from app.database import salvar_deteccao
from app.detector import detectar_placas, pre_processar_placa
from app.ocr import ler_placa

os.makedirs(IMAGES_PATH, exist_ok=True)

logger = logging.getLogger(__name__)

# Registra o timestamp da última vez que cada placa foi salva
_ultima_deteccao: dict[str, float] = {}

_captura_ativa = True

_frame_lock = threading.Lock()
_latest_jpeg: bytes | None = None


def gerar_stream_mjpeg():
    """Gera frames multipart MJPEG a partir do último frame capturado (para o navegador)."""
    while True:
        with _frame_lock:
            jpeg = _latest_jpeg
        if jpeg:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
            )
        time.sleep(1 / 20)


def parar_captura():
    global _captura_ativa
    _captura_ativa = False


def _pode_registrar(placa: str) -> bool:
    agora = time.time()
    if agora - _ultima_deteccao.get(placa, 0) >= COOLDOWN_PLACA:
        _ultima_deteccao[placa] = agora
        return True
    return False


def _salvar_frame(frame) -> str:
    nome = os.path.join(
        IMAGES_PATH,
        datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".jpg",
    )
    cv2.imwrite(nome, frame)
    return nome


def _abrir_video_capture():
    """Abre a câmera e aplica resolução padrão. Retorna None se não abrir."""
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        cap.release()
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    return cap


def iniciar_captura_continua():
    """
    Loop principal de leitura da câmera.
    Deve ser executado em uma thread separada (daemon=True).
    Reconecta automaticamente: não encerra se a câmera sumir ou falhar ao abrir.
    Fluxo por frame:
      1. Captura frame da câmera
      2. Detecção de placas (OpenCV) + OCR
      3. Valida padrão e cooldown
      4. Salva frame completo + registra no banco
    """
    global _captura_ativa, _latest_jpeg
    _captura_ativa = True

    while _captura_ativa:
        cap = None
        while _captura_ativa and cap is None:
            cap = _abrir_video_capture()
            if cap is None:
                logger.warning(
                    "Câmera indisponível (índice %s). Nova tentativa em %.1f s.",
                    CAMERA_INDEX,
                    CAMERA_RECONNECT_SEC,
                )
                time.sleep(CAMERA_RECONNECT_SEC)

        if not _captura_ativa:
            break

        logger.info("Câmera conectada (índice %s). Aguardando veículos...", CAMERA_INDEX)
        frames_ruins = 0

        try:
            while _captura_ativa:
                ret, frame = cap.read()

                if not ret or frame is None or frame.size == 0:
                    frames_ruins += 1
                    logger.warning(
                        "Frame inválido (%s consecutivos).",
                        frames_ruins,
                    )
                    time.sleep(0.5)
                    if frames_ruins >= CAMERA_BAD_FRAMES_REOPEN:
                        logger.warning(
                            "Limite de frames inválidos — reconectando câmera (índice %s).",
                            CAMERA_INDEX,
                        )
                        break
                    continue

                frames_ruins = 0

                ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ok:
                    with _frame_lock:
                        _latest_jpeg = buf.tobytes()

                try:
                    crops = detectar_placas(frame)
                except Exception as exc:
                    logger.warning("Falha na detecção (frame ignorado): %s", exc)
                    crops = []

                for crop in crops:
                    placa_processada = pre_processar_placa(crop)
                    placa = ler_placa(placa_processada)

                    if placa and _pode_registrar(placa):
                        imagem_path = _salvar_frame(frame)
                        cadastrada = salvar_deteccao(placa, imagem_path)
                        status = "CADASTRADA" if cadastrada else "NÃO CADASTRADA"
                        logger.info("Placa: %s | %s | %s", placa, status, imagem_path)

                # ~10 FPS — ajuste conforme a velocidade dos veículos
                time.sleep(0.1)

        finally:
            cap.release()
            if _captura_ativa:
                logger.info(
                    "Sessão da câmera encerrada; nova conexão em %.1f s.",
                    CAMERA_RECONNECT_SEC,
                )
                time.sleep(CAMERA_RECONNECT_SEC)

    logger.info("Captura contínua finalizada.")
