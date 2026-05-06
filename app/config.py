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

# YOLOv8 (Ultralytics) — pesos locais (.pt) para detecção de placas
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "models/placa.pt")
# Tamanho de inferência (múltiplo de 32; menor = mais rápido, pode perder placas pequenas)
YOLO_IMGSZ = int(os.getenv("YOLO_IMGSZ", "640"))
# Confiança mínima do YOLO para aceitar uma detecção (0.0–1.0)
YOLO_CONFIANCA = float(os.getenv("YOLO_CONFIANCA", "0.5"))

DB_PATH = os.getenv("DB_PATH", "data/database.db")
IMAGES_PATH = os.getenv("IMAGES_PATH", "data/images")
REPORTS_PATH = os.getenv("REPORTS_PATH", "data/relatorios")

HORARIO_RELATORIO = os.getenv("HORARIO_RELATORIO", "23:59")

# Segundos antes que a mesma placa possa ser registrada novamente
COOLDOWN_PLACA = int(os.getenv("COOLDOWN_PLACA", "60"))
