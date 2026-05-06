import os
from dotenv import load_dotenv

load_dotenv()

EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE", "")
EMAIL_SENHA = os.getenv("EMAIL_SENHA", "")
EMAIL_DESTINATARIO = os.getenv("EMAIL_DESTINATARIO", "")

CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))

# Manter câmera sempre ativa: reconectar se falhar ao abrir ou após frames inválidos
CAMERA_RECONNECT_SEC = float(os.getenv("CAMERA_RECONNECT_SEC", "2"))
CAMERA_BAD_FRAMES_REOPEN = int(os.getenv("CAMERA_BAD_FRAMES_REOPEN", "45"))

# Detecção de região (OpenCV, sem modelo de deep learning)
# Largura máxima do frame usado na detecção (0 = sempre tamanho original; menor = mais rápido)
DETECC_MAX_LARGURA = int(os.getenv("DETECC_MAX_LARGURA", "960"))
# Proporção largura/altura aceita para o retângulo da placa (Mercosul ~3,1:1)
PLACA_ASPECT_MIN = float(os.getenv("PLACA_ASPECT_MIN", "1.6"))
PLACA_ASPECT_MAX = float(os.getenv("PLACA_ASPECT_MAX", "6.0"))
# Área mínima/máxima do candidato em relação ao quadro inteiro
PLACA_AREA_MIN_FRAC = float(os.getenv("PLACA_AREA_MIN_FRAC", "0.0008"))
PLACA_AREA_MAX_FRAC = float(os.getenv("PLACA_AREA_MAX_FRAC", "0.25"))
CANNY_LOW = int(os.getenv("CANNY_LOW", "50"))
CANNY_HIGH = int(os.getenv("CANNY_HIGH", "150"))
# 1 = também procura retângulos claros (fundo reflexivo típico de placa)
DETECC_USAR_MASCARA_BRANCO = os.getenv("DETECC_USAR_MASCARA_BRANCO", "1").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
# Máximo de recortes por frame após supressão de sobreposição
DETECC_MAX_CANDIDATOS = int(os.getenv("DETECC_MAX_CANDIDATOS", "5"))
DETECC_NMS_IOU = float(os.getenv("DETECC_NMS_IOU", "0.35"))

DB_PATH = os.getenv("DB_PATH", "data/database.db")
IMAGES_PATH = os.getenv("IMAGES_PATH", "data/images")
REPORTS_PATH = os.getenv("REPORTS_PATH", "data/relatorios")

HORARIO_RELATORIO = os.getenv("HORARIO_RELATORIO", "23:59")

# Segundos antes que a mesma placa possa ser registrada novamente
COOLDOWN_PLACA = int(os.getenv("COOLDOWN_PLACA", "60"))
