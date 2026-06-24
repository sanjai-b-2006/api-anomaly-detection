---
title: Anomaly Detection
emoji: 🛡️
colorFrom: blue
colorTo: red
sdk: docker
app_port: 7860
pinned: false
---

# 🛡️ Real-time Network Anomaly Detection

A full-stack **SOC (Security Operations Center) dashboard** that ingests live network-flow data, runs it through an **ensemble of anomaly detectors**, and streams detected intrusions to a real-time React dashboard — with optional **LLM-generated root-cause explanations**.

Hosted as a **Docker Space** on Hugging Face. A single FastAPI process serves both the REST/WebSocket API **and** the compiled React UI.

> **Live demo:** the Space runs a built-in synthetic traffic generator, so the dashboard fills with data automatically — no setup required.

---

## ✨ Features

- **Real-time dashboard** — live line charts, network-flow logs, and a threat-alert feed, all updated over WebSockets.
- **Ensemble anomaly engine** — combines Z-Score, Modified Z-Score, IQR, Threshold, Isolation Forest, and missing-data detectors into a weighted composite score.
- **Attack simulation** — built-in generator injects DDoS, PortScan, DoS Hulk, and Infiltration attacks against benign background traffic.
- **LLM explanations** — each anomaly can be explained in plain English via OpenRouter (optional; degrades gracefully without a key).
- **CIC-IDS-2017 schema** — uses standard network intrusion features (forward/backward packets, flow bytes/s, flow duration, packet length).
- **CSV replay** — the standalone generator can replay a real Kaggle network-intrusion CSV.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Hugging Face Docker Space (single container, port 7860)       │
│                                                                │
│   ┌────────────────────────┐      ┌──────────────────────┐    │
│   │   React UI (Vite build) │◄────►│   FastAPI (uvicorn)  │    │
│   │   served as static files│  WS  │                      │    │
│   └────────────────────────┘      │  • REST /api/v1      │    │
│                                    │  • WebSocket /ws     │    │
│   ┌────────────────────────┐      │  • Static UI mount   │    │
│   │ Synthetic generator     │─────►│                      │    │
│   │ (in-process asyncio)    │      └──────────┬───────────┘    │
│   └────────────────────────┘                 │                │
│                                    ┌──────────▼───────────┐    │
│                                    │ Ensemble detectors    │   │
│                                    │ + SQLite database     │   │
│                                    │ + OpenRouter LLM      │   │
│                                    └──────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### Data flow
1. The **in-process synthetic generator** (or any client) creates a network flow and feeds it to `process_metric`.
2. The flow is stored in **SQLite** and pushed to all WebSocket clients as a `METRIC_UPDATE`.
3. The flow runs through the **ensemble pipeline** against a sliding window of recent flows.
4. If the composite score crosses the threshold, a **`DetectedAnomaly`** is created, optionally explained by the **LLM**, and broadcast as a `NEW_ANOMALY`.
5. The **React dashboard** renders metrics, flow logs, and threat alerts in real time.

---

## 🚀 How it runs on Hugging Face Spaces

This Space uses the **Docker SDK**. Here's exactly what happens:

### 1. The YAML header (top of this file)
Hugging Face reads the frontmatter to configure the Space:
```yaml
sdk: docker        # build & run from the Dockerfile
app_port: 7860     # HF routes the public URL to this port
```
> Docker Spaces **must** listen on port **7860** — that's why the app binds to `0.0.0.0:7860`.

### 2. The multi-stage Dockerfile
- **Stage 1 (Node):** `npm install` + `npm run build` compiles the React app into `frontend/dist`.
- **Stage 2 (Python):** installs `requirements.txt`, copies the backend, copies the built `frontend/dist`, and launches:
  ```
  uvicorn app.main:app --host 0.0.0.0 --port 7860
  ```
  (run from `/app/backend` so the `app` package imports correctly).

### 3. FastAPI serves everything
`backend/app/main.py` mounts the compiled UI at `/`, so:
- `GET /` → the React dashboard
- `GET /api/v1/...` → REST endpoints
- `GET /api/v1/ws/alerts` → the live WebSocket feed
- `GET /docs` → interactive Swagger API docs

The frontend builds its WebSocket URL dynamically from `window.location`, so it works on `wss://<space>.hf.space` automatically — no hardcoded localhost.

### 4. Build & deploy lifecycle
- Pushing to the Space's git repo (`main` branch) triggers an automatic Docker build.
- Watch progress in the **Build logs** tab; runtime output appears in the **Logs / Container** tab.
- When you see `Application startup complete` and `[synthetic] starting in-process traffic generator`, the Space is live.

---

## 🔧 Configuration (Space → Settings)

Set these under **Settings → Variables and secrets**:

| Name | Type | Default | Purpose |
|------|------|---------|---------|
| `OPENROUTER_API_KEY` | **secret** | _(empty)_ | Enables LLM root-cause explanations. Without it, alerts show a "disabled" placeholder. |
| `ENABLE_SYNTHETIC` | variable | `true` | Built-in traffic generator. Set `false` to ingest only external data. |
| `SYNTHETIC_DELAY` | variable | `2.0` | Seconds between generated flows. |
| `LLM_MODEL` | variable | `openai/gpt-4o` | OpenRouter model used for explanations. |
| `DATABASE_URL` | variable | `sqlite+aiosqlite:///./anomaly.db` | Override to use Postgres etc. |

> SQLite data is stored in the container's ephemeral filesystem and **resets on every rebuild/restart** — appropriate for a live demo.

---

## 🧪 Trying it out

- **Dashboard:** open the Space URL — data streams in automatically.
- **API docs:** `https://<space>.hf.space/docs`
- **Push a flow manually:** `POST /api/v1/metrics` from the Swagger UI.
- **List anomalies:** `GET /api/v1/anomalies`

---

## 💻 Local development

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev        # http://localhost:5173

# Optional: standalone traffic generator
cd backend
python mock_data_generator.py                  # synthetic
python mock_data_generator.py --csv path.csv   # replay a real dataset
```

---

## 📦 Tech stack

| Layer | Tech |
|-------|------|
| Frontend | React 19, Vite, Recharts, lucide-react |
| Backend | FastAPI, Uvicorn, WebSockets |
| Database | SQLAlchemy (async) + SQLite (aiosqlite) |
| ML | NumPy, scikit-learn (Isolation Forest) |
| LLM | OpenRouter (GPT-4o by default) |
| Deploy | Docker · Hugging Face Spaces |
