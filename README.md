---
title: API Traffic Anomaly Detection
emoji: 📊
colorFrom: blue
colorTo: red
sdk: docker
app_port: 7860
pinned: false
---

# 📊 Real-time API Traffic Anomaly Detection

A full-stack **observability / AIOps dashboard** that ingests live web-API traffic metrics, runs them through an **ensemble of anomaly detectors**, and streams detected incidents to a real-time React dashboard — with optional **LLM-generated root-cause explanations**.

Think of it as a miniature of what Datadog / Grafana / New Relic do: watch an API's **throughput, latency, and error rate**, and alert the moment something behaves abnormally.

Hosted as a **Docker Space** on Hugging Face. A single FastAPI process serves both the REST/WebSocket API **and** the compiled React UI.

> **Live demo:** the Space runs a built-in synthetic traffic generator, so the dashboard fills with data automatically — no setup required.

---

## ✨ Features

- **Real-time dashboard** — live line charts (requests/sec, latency, error rate), API traffic logs, and an incident feed, all updated over WebSockets.
- **Ensemble anomaly engine** — combines Z-Score, Modified Z-Score, IQR, Threshold, Isolation Forest, and missing-data detectors into a weighted composite score.
- **Incident simulation** — built-in generator injects Traffic Surge, Latency Spike, Error Spike, Service Outage, and Brute Force incidents against healthy background traffic.
- **LLM explanations** — each incident is explained in plain English with SRE-style root cause + mitigation steps (optional; degrades gracefully without a key).
- **SLO-based detection** — monitors standard service indicators: requests/sec, average & P95 latency, error rate.
- **CSV replay** — the standalone generator can replay a traffic CSV, and can target a remote (hosted) endpoint with `--url`.

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
│                                    │ + LLM explanations    │   │
│                                    └──────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### Data flow
1. The **in-process synthetic generator** (or any client) creates a traffic sample and feeds it to `process_metric`.
2. The sample is stored in **SQLite** and pushed to all WebSocket clients as a `METRIC_UPDATE`.
3. The sample runs through the **ensemble pipeline** against a sliding window of recent samples.
4. If the composite score crosses the threshold, a **`DetectedAnomaly`** is created, optionally explained by the **LLM**, and broadcast as a `NEW_ANOMALY`.
5. The **React dashboard** renders metrics, traffic logs, and incident alerts in real time.

---

## 📐 Metric schema

Each sample represents one endpoint over a short time window:

| Field | Type | Meaning |
|-------|------|---------|
| `endpoint` | string | API path, e.g. `/api/v1/login` |
| `method` | string | HTTP method (GET/POST/…) |
| `requests_per_sec` | float | throughput |
| `avg_latency_ms` | float | mean response time |
| `p95_latency_ms` | float | 95th-percentile response time |
| `error_rate` | float | fraction of failed requests (0.0–1.0) |
| `total_requests` | int | requests counted in the window |
| `error_count` | int | failed (4xx/5xx) requests in the window |
| `bytes_per_sec` | float | response throughput |
| `label` | string | `NORMAL`, or an incident type |

---

## 🚀 How it runs on Hugging Face Spaces

This Space uses the **Docker SDK**.

### 1. The YAML header (top of this file)
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
- When you see `Application startup complete` and `[synthetic] starting in-process API-traffic generator`, the Space is live.

---

## 🔧 Configuration (Space → Settings)

Set these under **Settings → Variables and secrets**:

| Name | Type | Default | Purpose |
|------|------|---------|---------|
| `GROQ_API_KEY` | **secret** | _(empty)_ | Enables LLM explanations via Groq (free, fast). |
| `OPENROUTER_API_KEY` | **secret** | _(empty)_ | Alternative LLM provider. Without any key, alerts show a placeholder. |
| `ENABLE_SYNTHETIC` | variable | `true` | Built-in traffic generator. Set `false` to ingest only external data. |
| `SYNTHETIC_DELAY` | variable | `2.0` | Seconds between generated samples. |
| `DATABASE_URL` | variable | `sqlite+aiosqlite:///./anomaly.db` | Override to use Postgres etc. |

> SQLite data is stored in the container's ephemeral filesystem and **resets on every rebuild/restart** — appropriate for a live demo.

---

## 🧪 Trying it out

- **Dashboard:** open the Space URL — data streams in automatically.
- **API docs:** `https://<space>.hf.space/docs`
- **Push a sample manually:** `POST /api/v1/metrics` from the Swagger UI.
- **List incidents:** `GET /api/v1/anomalies`

### Stream your own / external traffic to the hosted Space
```bash
cd backend
python mock_data_generator.py --url https://<space>.hf.space/api/v1/metrics/
```

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
python mock_data_generator.py --csv path.csv   # replay a traffic CSV
```

---

## 📦 Tech stack

| Layer | Tech |
|-------|------|
| Frontend | React 19, Vite, Recharts, lucide-react |
| Backend | FastAPI, Uvicorn, WebSockets |
| Database | SQLAlchemy (async) + SQLite (aiosqlite) |
| ML | NumPy, scikit-learn (Isolation Forest) |
| LLM | Groq / OpenRouter |
| Deploy | Docker · Hugging Face Spaces |
