# Sistema de Leitura de Placas

Sistema de monitoramento de veículos com captura contínua via câmera, detecção de placas por visão computacional e envio automático de relatório diário por e-mail.

---

## Como funciona

```
Câmera → OpenCV (candidatos à placa: bordas + região clara)
       → EasyOCR (lê texto) → Validação padrão BR
       → Banco SQLite → Relatório PDF → E-mail
```

1. A câmera captura frames continuamente (~10 fps)
2. O **OpenCV** propõe retângulos candidatos (Canny + morfologia e, opcionalmente, máscara HSV para fundo reflexivo típico de placa), para localizar a região
3. O EasyOCR lê o texto do recorte (ainda usa modelo de OCR)
4. O sistema verifica se a placa está cadastrada no banco
5. Todo dia no horário configurado, um PDF com as passagens do dia é enviado por e-mail

---

## Estrutura do projeto

```
placa/
├── app/
│   ├── main.py          # API FastAPI + inicialização das threads
│   ├── camera.py        # Loop contínuo de captura
│   ├── detector.py      # Detecção de região candidata (OpenCV)
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
├── .env                 # Credenciais e configurações (não versionar)
├── .env.example         # Template do .env
└── requirements.txt
```

---

## Pré-requisitos

- Python 3.10+
- Câmera USB ou IP (RTSP)
- Conta Gmail com [Senha de App](https://myaccount.google.com/apppasswords) habilitada (apenas para envio do relatório por e-mail)

A detecção da **região** da placa é heurística (iluminação, ângulo e fundo influenciam bastante). Ajuste `PLACA_ASPECT_*`, `PLACA_AREA_*`, `CANNY_*` e `DETECC_USAR_MASCARA_BRANCO` no `.env` se precisar finar para o seu cenário.

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
| `DETECC_MAX_LARGURA` | Largura máxima usada na detecção (0 = frame inteiro) | `960` |
| `PLACA_ASPECT_MIN` / `PLACA_ASPECT_MAX` | Proporção largura/altura aceita | `1.6` / `6.0` |
| `PLACA_AREA_MIN_FRAC` / `PLACA_AREA_MAX_FRAC` | Área do candidato / área do frame | `0.0008` / `0.25` |
| `CANNY_LOW` / `CANNY_HIGH` | Limiares do detector de bordas | `50` / `150` |
| `DETECC_USAR_MASCARA_BRANCO` | `1` = também usa região clara (HSV) | `1` |
| `DETECC_MAX_CANDIDATOS` | Máximo de recortes por frame após NMS | `5` |
| `DETECC_NMS_IOU` | IoU máximo entre caixas antes de fundir | `0.35` |
| `HORARIO_RELATORIO` | Horário de envio do e-mail | `23:59` |
| `COOLDOWN_PLACA` | Segundos entre registros da mesma placa | `60` |

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
