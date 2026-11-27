import sqlite3
import os
from datetime import datetime
from app.config import DB_PATH

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def _conectar():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = _conectar()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS placas_cadastradas (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        placa       TEXT    UNIQUE NOT NULL,
        proprietario TEXT   DEFAULT '',
        observacao  TEXT    DEFAULT '',
        criado_em   TEXT    DEFAULT (datetime('now','localtime'))
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deteccoes (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        placa       TEXT    NOT NULL,
        data_hora   TEXT    NOT NULL,
        imagem_path TEXT    DEFAULT '',
        cadastrada  INTEGER DEFAULT 0
    )
    """)

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_deteccoes_data ON deteccoes (date(data_hora))"
    )

    conn.commit()
    conn.close()


def placa_cadastrada(placa: str) -> bool:
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM placas_cadastradas WHERE placa = ?", (placa.upper(),)
    )
    result = cursor.fetchone() is not None
    conn.close()
    return result


def salvar_deteccao(placa: str, imagem_path: str):
    cadastrada = placa_cadastrada(placa)
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO deteccoes (placa, data_hora, imagem_path, cadastrada)
        VALUES (?, ?, ?, ?)
        """,
        (placa.upper(), datetime.now().isoformat(), imagem_path, int(cadastrada)),
    )
    conn.commit()
    conn.close()
    return cadastrada


def listar_deteccoes_dia(data: str | None = None):
    """Retorna (placa, data_hora, imagem_path, cadastrada) do dia informado (padrão: hoje)."""
    conn = _conectar()
    cursor = conn.cursor()
    dia = data or datetime.now().date().isoformat()
    cursor.execute(
        """
        SELECT placa, data_hora, imagem_path, cadastrada
        FROM deteccoes
        WHERE date(data_hora) = ?
        ORDER BY data_hora
        """,
        (dia,),
    )
    dados = cursor.fetchall()
    conn.close()
    return dados


def listar_ultimas_deteccoes(limite: int = 100):
    """Retorna os registros (id, placa, data_hora, imagem_path, cadastrada), mais recentes primeiro."""
    limite = max(1, min(limite, 500))
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, placa, data_hora, imagem_path, cadastrada
        FROM deteccoes
        ORDER BY data_hora DESC
        LIMIT ?
        """,
        (limite,),
    )
    dados = cursor.fetchall()
    conn.close()
    return dados


def remover_deteccao(deteccao_id: int):
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT imagem_path FROM deteccoes WHERE id = ?", (deteccao_id,)
    )
    registro = cursor.fetchone()
    if registro is None:
        conn.close()
        return None

    cursor.execute("DELETE FROM deteccoes WHERE id = ?", (deteccao_id,))
    conn.commit()
    conn.close()
    return registro[0]


def cadastrar_placa(placa: str, proprietario: str = "", observacao: str = ""):
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO placas_cadastradas (placa, proprietario, observacao)
        VALUES (?, ?, ?)
        """,
        (placa.upper(), proprietario, observacao),
    )
    conn.commit()
    conn.close()


def remover_placa_cadastrada(placa: str):
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM placas_cadastradas WHERE placa = ?", (placa.upper(),)
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def listar_placas_cadastradas():
    conn = _conectar()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT placa, proprietario, observacao, criado_em FROM placas_cadastradas ORDER BY placa"
    )
    dados = cursor.fetchall()
    conn.close()
    return dados
