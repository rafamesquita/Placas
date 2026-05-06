# Sistema de Leitura de Placas

Sistema de monitoramento de veículos com captura contínua via câmera, detecção de placas por visão computacional e envio automático de relatório diário por e-mail.

---

## Como funciona

```
Câmera → YOLOv8 local (detecta placa) → OpenCV (pré-processamento)
       → EasyOCR (lê texto) → Validação padrão BR
       → Banco SQLite → Relatório PDF → E-mail
```

1. A câmera captura frames continuamente (~10 fps)
2. O modelo YOLOv8 (Ultralytics, arquivo `.pt` local) detecta a região da placa em cada frame
3. O EasyOCR lê o texto da placa recortada
4. O sistema verifica se a placa está cadastrada no banco
5. Todo dia no horário configurado, um PDF com as passagens do dia é enviado por e-mail

---

## Estrutura do projeto

```
placa/
├── app/
│   ├── main.py          # API FastAPI + inicialização das threads
│   ├── camera.py        # Loop contínuo de captura
│   ├── detector.py      # Detecção de placas via YOLOv8 (Ultralytics)
│   ├── ocr.py           # Leitura de texto com EasyOCR
│   ├── database.py      # Operações SQLite
│   ├── report.py        # Geração do PDF
│   ├── email_sender.py  # Envio de e-mail
│   ├── scheduler.py     # Agendamento do relatório diário
│   └── config.py        # Configurações via .env
├── data/
│   ├── images/          # Frames salvos no momento da detecção
│   ├── relatorios/      # PDFs gerados
│   └── database.db      # Banco de dados SQLite
├── models/              # Pesos do YOLOv8 (.pt) — ver YOLO_MODEL_PATH no .env
├── .env                 # Credenciais e configurações (não versionar)
├── .env.example         # Template do .env
└── requirements.txt
```

---

## Pré-requisitos

- Python 3.10+
- Câmera USB ou IP (RTSP)
- Arquivo de pesos **YOLOv8** (`.pt`) treinado para detecção de placas, no caminho definido por `YOLO_MODEL_PATH` (padrão: `models/placa.pt`)
- Conta Gmail com [Senha de App](https://myaccount.google.com/apppasswords) habilitada (apenas para envio do relatório por e-mail)

---

## Instalação

**1. Clone o repositório e entre na pasta:**
```bash
cd placa
```

**2. Crie e ative um ambiente virtual:**
```bash
python -m venv venv
venv\Scripts\activate      # Windows
```

**3. Instale as dependências:**
```bash
pip install -r requirements.txt
```

**4. Configure o ambiente:**
```bash
copy .env.example .env
```
Edite o arquivo `.env` com suas credenciais (veja a seção abaixo).

---

## Configuração (.env)

| Variável | Descrição | Exemplo |
|---|---|---|
| `EMAIL_REMETENTE` | E-mail que envia o relatório | `seuemail@gmail.com` |
| `EMAIL_SENHA` | Senha de App do Gmail | `xxxx xxxx xxxx xxxx` |
| `EMAIL_DESTINATARIO` | E-mail que recebe o relatório | `destino@gmail.com` |
| `CAMERA_INDEX` | Índice da câmera (0 = padrão) | `0` |
| `YOLO_MODEL_PATH` | Caminho do arquivo `.pt` (YOLOv8) | `models/placa.pt` |
| `YOLO_CONFIANCA` | Confiança mínima para detecção (0.0–1.0) | `0.5` |
| `YOLO_IMGSZ` | Tamanho de entrada da inferência (ex. 640) | `640` |
| `HORARIO_RELATORIO` | Horário de envio do e-mail | `23:59` |
| `COOLDOWN_PLACA` | Segundos entre registros da mesma placa | `60` |

### Modelo YOLOv8 (`.pt`)
Coloque um modelo treinado para **detecção de placas** (formato Ultralytics YOLOv8) em `models/` e aponte `YOLO_MODEL_PATH` no `.env`. Sem esse arquivo o sistema não consegue localizar placas nos frames.

### Como gerar a Senha de App do Gmail
1. Acesse [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Crie uma senha para "Outro aplicativo"
3. Cole o código gerado em `EMAIL_SENHA` no `.env`

---

## Executando

```bash
uvicorn app.main:app --reload
```

Ao iniciar, o sistema:
- Cria o banco de dados automaticamente
- Liga a câmera e começa a detectar placas
- Agenda o envio do relatório no horário configurado

Acesse a documentação interativa da API em: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API REST

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/deteccoes/hoje` | Lista todas as detecções do dia atual |
| `GET` | `/placas` | Lista placas cadastradas |
| `POST` | `/placas` | Cadastra uma nova placa |
| `DELETE` | `/placas/{placa}` | Remove uma placa cadastrada |

### Exemplos

**Cadastrar uma placa:**
```bash
curl -X POST http://localhost:8000/placas \
  -H "Content-Type: application/json" \
  -d '{"placa": "ABC1D23", "proprietario": "João Silva", "observacao": "Carro da empresa"}'
```

**Ver detecções de hoje:**
```bash
curl http://localhost:8000/deteccoes/hoje
```

**Remover uma placa:**
```bash
curl -X DELETE http://localhost:8000/placas/ABC1D23
```

---

## Relatório PDF

O relatório gerado diariamente contém:
- Tabela resumo com todas as passagens do dia
- Para cada passagem: placa, horário, status (cadastrada / não cadastrada) e foto do momento

Os PDFs ficam salvos em `data/relatorios/relatorio_YYYYMMDD.pdf`.

---

## Banco de dados

Duas tabelas SQLite em `data/database.db`:

**`placas_cadastradas`** — veículos autorizados
| Campo | Tipo | Descrição |
|---|---|---|
| placa | TEXT | Placa do veículo (ex: ABC1D23) |
| proprietario | TEXT | Nome do proprietário |
| observacao | TEXT | Observações livres |
| criado_em | TEXT | Data/hora do cadastro |

**`deteccoes`** — histórico de passagens
| Campo | Tipo | Descrição |
|---|---|---|
| placa | TEXT | Placa detectada |
| data_hora | TEXT | Data e hora da passagem |
| imagem_path | TEXT | Caminho da foto salva |
| cadastrada | INTEGER | 1 = cadastrada, 0 = desconhecida |

---

## Padrões de placa suportados

| Formato | Exemplo | Descrição |
|---|---|---|
| Antigo | `ABC1234` | 3 letras + 4 dígitos |
| Mercosul | `ABC1D23` | 3 letras + 1 dígito + 1 letra + 2 dígitos |
