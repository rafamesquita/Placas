import logging
import os
import threading

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import IMAGES_PATH
from app.database import (
    cadastrar_placa,
    init_db,
    listar_deteccoes_dia,
    listar_placas_cadastradas,
    listar_ultimas_deteccoes,
    placa_cadastrada,
    remover_deteccao,
    remover_placa_cadastrada,
)
from app.camera import gerar_stream_mjpeg, iniciar_captura_continua
from app.scheduler import start as start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Sistema de Leitura de Placas",
    description="Captura contínua via câmera, detecção OpenCV + OCR e relatório diário por e-mail.",
    version="2.0.0",
)

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
_IMAGES_ABS = os.path.abspath(IMAGES_PATH)
os.makedirs(_IMAGES_ABS, exist_ok=True)
app.mount("/imagens", StaticFiles(directory=_IMAGES_ABS), name="imagens")


def _imagem_public_url(imagem_path: str | None) -> str | None:
    if not imagem_path:
        return None
    base = os.path.basename(imagem_path.replace("\\", "/"))
    if not base:
        return None
    return f"/imagens/{base}"


def _serializar_deteccao(row):
    if len(row) == 5:
        identificador, p, d, i, c = row
    else:
        identificador = None
        p, d, i, c = row
    return {
        "id": identificador,
        "placa": p,
        "data_hora": d,
        "imagem": i,
        "imagem_url": _imagem_public_url(i),
        "cadastrada": bool(c),
    }


@app.on_event("startup")
def startup():
    init_db()
    threading.Thread(
        target=iniciar_captura_continua, daemon=True, name="camera"
    ).start()
    threading.Thread(
        target=start_scheduler, daemon=True, name="scheduler"
    ).start()


# ── Visão (dashboard) ────────────────────────────────────────────────────────

@app.get("/visao", summary="Página HTML: câmera ao vivo e histórico de passagens")
def pagina_visao():
    html_path = os.path.join(_STATIC_DIR, "visao.html")
    if not os.path.isfile(html_path):
        raise HTTPException(status_code=404, detail="visao.html não encontrado.")
    return FileResponse(html_path, media_type="text/html; charset=utf-8")


@app.get("/stream/camera", summary="Fluxo MJPEG ao vivo da câmera")
def stream_camera():
    return StreamingResponse(
        gerar_stream_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# ── Detecções ────────────────────────────────────────────────────────────────

@app.get("/deteccoes/hoje", summary="Lista todas as detecções do dia atual")
def deteccoes_hoje():
    dados = listar_deteccoes_dia()
    return [_serializar_deteccao(row) for row in dados]


@app.get("/deteccoes/ultimas", summary="Últimas passagens registradas (histórico recente)")
def deteccoes_ultimas(limite: int = Query(100, ge=1, le=500)):
    dados = listar_ultimas_deteccoes(limite)
    return [_serializar_deteccao(row) for row in dados]


@app.delete("/deteccoes/{deteccao_id}", summary="Remove um registro de passagem")
def remover_deteccao_registro(deteccao_id: int):
    imagem_path = remover_deteccao(deteccao_id)
    if imagem_path is None:
        raise HTTPException(status_code=404, detail="Registro não encontrado.")

    if imagem_path and os.path.isfile(imagem_path):
        os.remove(imagem_path)

    return {"mensagem": "Registro removido com sucesso."}


# ── Placas cadastradas ────────────────────────────────────────────────────────

class PlacaInput(BaseModel):
    placa: str
    proprietario: str = ""
    observacao: str = ""


@app.get("/placas", summary="Lista todas as placas cadastradas")
def listar_placas():
    dados = listar_placas_cadastradas()
    return [
        {
            "placa": p,
            "proprietario": pr,
            "observacao": obs,
            "criado_em": cr,
        }
        for p, pr, obs, cr in dados
    ]


@app.post("/placas", status_code=201, summary="Cadastra uma nova placa")
def cadastrar(body: PlacaInput):
    if placa_cadastrada(body.placa):
        raise HTTPException(status_code=409, detail=f"Placa '{body.placa}' já cadastrada.")
    cadastrar_placa(body.placa, body.proprietario, body.observacao)
    return {"mensagem": f"Placa '{body.placa.upper()}' cadastrada com sucesso."}


@app.delete("/placas/{placa}", summary="Remove uma placa cadastrada")
def remover(placa: str):
    removida = remover_placa_cadastrada(placa)
    if not removida:
        raise HTTPException(status_code=404, detail=f"Placa '{placa}' não encontrada.")
    return {"mensagem": f"Placa '{placa.upper()}' removida com sucesso."}
