# 🌎 GeoRisk – Back-end API

> MVP para análise de risco de alagamento usando dados geográficos e inteligência artificial.

## 🚀 Visão geral

O **GeoRisk** é uma API desenvolvida em **FastAPI** que calcula e classifica o **risco de alagamento** de uma área geográfica.
Ela combina informações espaciais (distância até rios, elevação e declividade) com um motor de **IA verticalizada** (LangChain + GPT-4o) para gerar avaliações técnicas, explicáveis e contextualizadas.

### 🧩 Funcionalidades principais

* **/geo/distance** → calcula a distância até o rio mais próximo e retorna o nome e tipo do corpo d’água.
* **/geo/risk** → estima o risco de alagamento combinando altitude e distância; utiliza a IA para classificar (Baixo / Médio / Alto).
* **/ai/ask-ai** → interface direta com a IA, respondendo perguntas técnicas baseadas nos relatórios `flood_risk_brazil.txt` e `bart_flood_model.txt`.
---
### 📊 Dados geoespaciais

Os dados de corpos d’água (rios, córregos e canais de CURITIBA inicialmente) utilizados neste projeto foram extraídos diretamente da plataforma Overpass Turbo
 — um ambiente de consulta da base OpenStreetMap (OSM).

🔹 Origem dos dados: OpenStreetMap (via Overpass API) <br/>
🔹 Ferramenta de extração: Overpass Turbo<br/>
🔹 Formato: GeoJSON (exportCuritiba.geojson)<br/>
🔹 Confiabilidade: As informações são fidedignas, pois refletem dados abertos e constantemente atualizados pela comunidade OSM, reconhecida por sua precisão cartográfica em aplicações geoespaciais e urbanas.<br/>

#### Esses dados servem como base para:

Calcular a distância até o rio mais próximo.

Identificar o nome e tipo do corpo d’água (campo waterway).

Realizar análises espaciais de risco de alagamento.

---

## ⚙️ Tecnologias utilizadas

* **Python 3.11+ / 3.12**
* **FastAPI + Uvicorn**
* **Shapely** — geometria geoespacial
* **PyProj** — projeções UTM / conversão geodésica
* **Requests** — API externa de elevação (Open-Meteo)
* **LangChain 1.x**
* **OpenAI API (GPT-4o)**
* **FAISS (ou cálculo em memória)** — busca vetorial
* **dotenv** — gerenciamento de variáveis de ambiente

---

## 🗂️ Estrutura do projeto

```
backend/
├── main.py                 # ponto de entrada (FastAPI)
├── routers/
│   ├── ai_vertical.py      # rota /ai/ask-ai
│   ├── distance.py         # rota /geo/distance
│   └── risk.py             # rota /geo/risk
├── services/
│   ├── ai_service.py       # pipeline LangChain + GPT-4o
│   ├── elevation_service.py# consumo da API Open-Meteo
│   └── water_service.py    # cálculos geográficos (rios)
├── data/
│   ├── exportCuritiba.geojson
│   ├── flood_risk_brazil.txt
│   └── bart_flood_model.txt
├── .env                    # variável OPENAI_API_KEY
└── requirements.txt
```

---

## 🧰 Instalação e execução

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/georisk-backend.git
cd georisk-backend/backend
```

### 2. Crie e ative o ambiente virtual

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # Windows
# ou
source .venv/bin/activate        # Linux / macOS
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure suas variáveis de ambiente

Crie um arquivo `.env` na raiz do backend:

```bash
OPENAI_API_KEY=sk-proj-sua_chave_aqui
```

### 5. Execute o servidor

```bash
python -m uvicorn main:app --reload
```

O servidor rodará em
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

---

## 📡 Endpoints principais

| Rota            | Método | Descrição                                            |
| --------------- | ------ | ---------------------------------------------------- |
| `/geo/distance` | POST   | Calcula distância até o rio mais próximo             |
| `/geo/risk`     | POST   | Retorna avaliação de risco de alagamento (usando IA) |
| `/ai/ask-ai`    | POST   | Interface direta com o modelo GPT-4o                 |

---

### Exemplo de requisição `/geo/risk`

```json
{
  "polygon": {
    "type": "Polygon",
    "coordinates": [
      [
        [-49.283, -25.461],
        [-49.282, -25.461],
        [-49.282, -25.460],
        [-49.283, -25.460],
        [-49.283, -25.461]
      ]
    ]
  }
}
```

**Resposta:**

```json
{
  "distancia_rio_m": 1750.7,
  "queda_relativa_m": 9,
  "rio_mais_proximo": "Rio Água Verde",
  "avaliacao_ia": "Risco Médio — distância considerável do rio e elevação moderada reduzem a probabilidade de alagamento."
}
```

---

## 💡 Próximos passos

* 🔗 Integrar com o **front-end Mapbox** (página `/map`)
* 📊 Gerar relatórios em PDF com a avaliação técnica
* 🧠 Adicionar histórico de análises (banco SQLite/Postgres)
* 🛰️ Integrar dados de chuva e permeabilidade urbana

---

## 🧑‍💻 Autor

**Guilherme Serafim (@Guiler)**
[LinkedIn](https://linkedin.com/in/guiserafim) · [GitHub](https://github.com/GuilhermeSerafim)
