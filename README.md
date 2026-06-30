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

A full-stack **observability / AIOps dashboard** that ingests live web-API traffic metrics, runs every sample through an **ensemble of anomaly detectors**, and streams detected incidents to a real-time React dashboard — each one accompanied by an **LLM-generated root-cause analysis and mitigation plan**.

Think of it as a miniature of what Datadog / Grafana / New Relic do: continuously watch an API's **throughput, latency, and error rate**, and raise an explained alert the moment something behaves abnormally.

It is packaged as a single **Docker container** and hosted on **Hugging Face Spaces** — one FastAPI process serves both the REST/WebSocket API **and** the compiled React UI.

> **Live demo:** a built-in synthetic traffic generator runs inside the container, so the dashboard fills with data and periodically injects incidents automatically — no setup required.

---

## 📑 Table of contents

1. [What problem it solves](#-what-problem-it-solves)
2. [System architecture](#-system-architecture)
3. [The complete workflow (step by step)](#-the-complete-workflow-step-by-step)
4. [The metric schema](#-the-metric-schema)
5. [The detection engine explained](#-the-detection-engine-explained)
6. [Incident classification & severity](#-incident-classification--severity)
7. [LLM root-cause explanations](#-llm-root-cause-explanations)
8. [Real-time delivery (WebSockets)](#-real-time-delivery-websockets)
9. [Storage, persistence & RAM fallback](#-storage-persistence--ram-fallback)
10. [The frontend dashboard](#-the-frontend-dashboard)
11. [API reference](#-api-reference)
12. [Configuration](#-configuration)
13. [How it runs on Hugging Face Spaces](#-how-it-runs-on-hugging-face-spaces)
14. [Local development](#-local-development)
15. [Streaming your own traffic](#-streaming-your-own-traffic)
16. [Project structure](#-project-structure)
17. [Tech stack](#-tech-stack)

---

## 🎯 What problem it solves

A live web service emits thousands of metrics per minute. No human can watch them all. This system watches them automatically and only speaks up when something is genuinely abnormal — *before* it becomes an outage. Concretely it catches:

- **Traffic surges** — a viral spike or a DDoS flooding an endpoint.
- **Latency degradation** — responses slowing past their SLO because of a slow dependency or DB contention.
- **Error spikes** — a bad deploy pushing the error rate above the error budget.
- **Service outages** — the backend returning mostly 5xx with collapsed throughput.
- **Brute-force / credential stuffing** — a flood of failed auth attempts on the login endpoint.

The same streaming-ensemble approach generalizes to fraud detection, infrastructure observability, and predictive maintenance — this project is the API-traffic instance of it.

---

## 🏗️ System architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  Hugging Face Docker Space  ·  single container  ·  port 7860          │
│                                                                        │
│   ┌─────────────────────────┐        ┌────────────────────────────┐   │
│   │   React UI (Vite build)  │◄──WS──►│   FastAPI (uvicorn, async) │   │
│   │   served as static files │  REST  │                            │   │
│   └─────────────────────────┘        │  GET  /                     │   │
│                                       │  POST /api/v1/metrics       │   │
│   ┌─────────────────────────┐        │  GET  /api/v1/anomalies     │   │
│   │  Synthetic generator     │──────► │  WS   /api/v1/ws/alerts     │   │
│   │  (in-process asyncio)    │        │  GET  /api/v1/health        │   │
│   └─────────────────────────┘        └──────────────┬─────────────┘   │
│                                                      │                 │
│                          ┌───────────────────────────▼──────────────┐ │
│                          │  process_metric()  (metric_service)        │ │
│                          │   1. store sample   2. broadcast live      │ │
│                          │   3. run pipeline   4. handle incident     │ │
│                          └───────┬───────────────────────┬───────────┘ │
│                                  │                        │             │
│                  ┌───────────────▼────────┐   ┌───────────▼──────────┐ │
│                  │  Anomaly pipeline       │   │  Database (SQLAlchemy)│ │
│                  │   • 4 univariate dets   │   │   Neon Postgres OR    │ │
│                  │   • Isolation Forest    │   │   in-memory fallback  │ │
│                  │   • ensemble voter      │   └──────────────────────┘ │
│                  └───────────────┬────────┘                             │
│                                  │ incident                             │
│                          ┌───────▼────────┐                             │
│                          │  LLM client     │  Groq / OpenRouter         │
│                          │  (explanation)  │                            │
│                          └────────────────┘                             │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 The complete workflow (step by step)

This is the full life of a single traffic sample, from creation to appearing on your screen.

### Step 0 — A sample is created
A **traffic sample** describes one API endpoint over a short (~5s) window: its request rate, latencies, error rate, and throughput. Samples enter the system in one of two ways:

- **Built-in generator** (`app/ingestion/synthetic_runner.py`) — an asyncio background task started on app boot. Every ~2 seconds it emits a healthy sample; every 20th cycle it injects a burst of one incident type (Traffic Surge / Latency Spike / Error Spike / Service Outage / Brute Force). It calls `process_metric` directly (no HTTP), so the demo is self-contained.
- **External clients** — anything that does `POST /api/v1/metrics` with the [schema](#-the-metric-schema): the standalone generator, your own app, a monitoring agent, a CSV replay.

### Step 1 — Ingestion endpoint
`POST /api/v1/metrics` ([`api/routes/metrics.py`](backend/app/api/routes/metrics.py)) validates the body against the Pydantic `MetricDataPointCreate` schema and hands the work to a **FastAPI background task** so the HTTP caller gets an instant `{"status": "accepted"}` and never waits for detection.

### Step 2 — Persist the raw sample
`process_metric` ([`services/metric_service.py`](backend/app/services/metric_service.py)) writes the sample to the **`metric_data_points`** table via async SQLAlchemy.

### Step 3 — Load the detection rule
The service looks up an active `DetectionRule` named `api_traffic`. If none exists in the DB, it uses a sensible **default rule** defined in code: which detectors to run, their weights, the SLO thresholds, and the sliding-window size (100).

### Step 4 — Update the sliding window
The service keeps the **last 100 samples in memory** (`flow_history`). The detectors compare the *current* sample against this rolling baseline. (Note: a copy of the history *before* the current sample is passed to the pipeline, so a sample is never compared against itself.)

### Step 5 — Broadcast the live metric
Immediately, the sample is pushed to every connected dashboard over WebSocket as a **`METRIC_UPDATE`** message. This is what makes the charts and the live-traffic table move in real time — independent of whether it turns out to be anomalous.

### Step 6 — Run the anomaly pipeline
`AnomalyPipeline.process` ([`engine/pipeline.py`](backend/app/engine/pipeline.py)) scores the sample. See [the detection engine](#-the-detection-engine-explained) for the full math. In short:
- Each of 4 **univariate detectors** runs on each of 4 **monitored features**.
- One **multivariate Isolation Forest** runs across all 4 features together.
- An **ensemble voter** combines all detector verdicts into one decision.

### Step 7 — Decide & classify
If the ensemble flags an anomaly (or the sample carries an incident label), the pipeline computes a **severity** and the service assigns a human-readable **incident type** (e.g. "Latency Spike"). See [classification](#-incident-classification--severity).

### Step 8 — Cooldown guard
`handle_anomaly` ([`services/anomaly_service.py`](backend/app/services/anomaly_service.py)) suppresses repeat alerts of the *same incident type* within a 10-second window, so a sustained incident produces one alert, not a flood.

### Step 9 — Generate the LLM explanation
A rich prompt (metrics + baselines + which detectors fired) is built and sent to the LLM, which returns an **SRE-style root-cause analysis + 2-3 mitigation actions**. Without an API key this step degrades to a placeholder string — nothing breaks.

### Step 10 — Persist & broadcast the incident
The incident (with its explanation) is written to the **`detected_anomalies`** table and broadcast to all dashboards as a **`NEW_ANOMALY`** message.

### Step 11 — The dashboard renders it
The React app receives the WebSocket messages and updates the live charts, the traffic log, and the **Active Incident Alerts** feed — including the LLM explanation card. On first load it also pulls historical incidents from `GET /api/v1/anomalies` so the Incident Feed isn't empty after a refresh.

---

## 📐 The metric schema

Each sample represents one endpoint over a short time window:

| Field | Type | Meaning |
|-------|------|---------|
| `timestamp` | datetime | when the window was measured |
| `endpoint` | string | API path, e.g. `/api/v1/login` |
| `method` | string | HTTP method (GET/POST/…) |
| `requests_per_sec` | float | throughput |
| `avg_latency_ms` | float | mean response time |
| `p95_latency_ms` | float | 95th-percentile response time |
| `error_rate` | float | fraction of failed requests (0.0–1.0) |
| `total_requests` | int | requests counted in the window |
| `error_count` | int | failed (4xx/5xx) requests in the window |
| `bytes_per_sec` | float | response throughput |
| `label` | string | `NORMAL`, or an incident type (for simulation/replay) |
| `tags` | object | free-form metadata |
| `source` | string | origin tag (`synthetic_generator`, `csv_replay`, …) |

The **4 monitored features** the engine actually scores are: `requests_per_sec`, `avg_latency_ms`, `p95_latency_ms`, `error_rate`.

---

## 🧠 The detection engine explained

The engine combines **statistical**, **rule-based**, and **machine-learning** detectors so no single method's blind spot lets an incident through. Six detectors are implemented; four are active by default for API traffic.

### The detectors

| Detector | Type | How it works | Default weight |
|----------|------|--------------|:---:|
| **Z-Score** | statistical | flags when `|x − mean| / std` exceeds 3.0 — i.e. the value is >3 standard deviations from the rolling mean. Good for normally-distributed metrics. | 1.0 |
| **Modified Z-Score** | statistical | uses the **median** and **MAD** (median absolute deviation) instead of mean/std, so a few extreme outliers don't poison the baseline. Threshold 3.5. *(implemented; not in the default API set)* | 1.2 |
| **IQR** | statistical | flags values outside `[Q1 − 1.5·IQR, Q3 + 1.5·IQR]` — the classic box-plot outlier rule. Distribution-agnostic. | 1.0 |
| **Threshold** | rule-based | hard SLO limits (e.g. `error_rate > 0.2`, `p95 > 2000ms`). When breached, scores a maximal 1.0 — these are non-negotiable business limits. | 2.0 |
| **Isolation Forest** | ML (sklearn) | trains on the window and isolates points that are easy to "cut off" from the rest. Runs **multivariately** across all 4 features, so it catches abnormal *combinations* no single metric reveals. Needs ≥15 samples of history. | 1.5 |
| **Missing Data** | rule-based | detects gaps where expected samples stopped arriving (a dead service). *(implemented; not in the default API set)* | 1.5 |

Each detector returns `(is_anomaly, score 0–1, human-readable detail)`.

### How they're combined — the ensemble voter

[`engine/ensemble.py`](backend/app/engine/ensemble.py) performs a **weighted vote**:

1. Every detector result carries a weight (Threshold counts double, Isolation Forest 1.5×, etc.).
2. `vote_ratio = (sum of weights that flagged anomaly) / (sum of all weights)`.
3. If `vote_ratio ≥ 0.35` (the quorum), the sample is an **anomaly**.
4. **Composite score** = weighted average of the *triggered* detectors' scores → drives severity.
5. **Confidence** = the vote ratio → how unanimous the detectors were.

The 0.35 quorum makes the system deliberately sensitive: a strong signal from the high-weight Threshold + Isolation Forest detectors alone can raise an alert.

### Default SLO thresholds

| Feature | Limit |
|---------|-------|
| `requests_per_sec` | 500 |
| `avg_latency_ms` | 1000 (1s) |
| `p95_latency_ms` | 2000 (2s) |
| `error_rate` | 0.20 (20%) |

These live in the default rule and can be overridden by inserting a `DetectionRule` row named `api_traffic`.

---

## 🏷️ Incident classification & severity

Once flagged, the incident gets a **type** (in `metric_service.py`) — if the sample is labelled, that label wins; otherwise it's inferred from the metrics:

| Condition | Incident type |
|-----------|---------------|
| `error_rate ≥ 0.5` | **Service Outage** |
| `error_rate ≥ 0.2` | **Error Spike** |
| `requests_per_sec > 500` | **Traffic Surge** |
| `p95 > 2000ms` or `avg > 1000ms` | **Latency Spike** |
| otherwise | **Abnormal Traffic** |

…and a **severity** from the composite score: `≥0.85` critical · `≥0.7` high · `≥0.5` medium · else low.

---

## 🤖 LLM root-cause explanations

For each incident, [`llm/prompt_builder.py`](backend/app/llm/prompt_builder.py) assembles a prompt containing the incident type, severity, the current metrics **vs. their rolling baselines**, and exactly which detectors fired. [`llm/client.py`](backend/app/llm/client.py) sends it to:

- **Groq** (free, fast) when `GROQ_API_KEY` is set, else
- **OpenRouter** when `OPENROUTER_API_KEY` is set, else
- a graceful `"LLM Explanation disabled"` placeholder.

The model is asked for a concise **root-cause analysis** plus **2-3 immediate mitigation actions** (rate-limit, roll back, fail over, block IPs, add caching…), written for an on-call SRE.

---

## 📡 Real-time delivery (WebSockets)

A single WebSocket endpoint, `GET /api/v1/ws/alerts`, managed by [`websocket/manager.py`](backend/app/websocket/manager.py), pushes two message types to every connected browser:

| Type | When | Payload |
|------|------|---------|
| `METRIC_UPDATE` | every sample | the live metrics (drives charts + traffic log) |
| `NEW_ANOMALY` | on a detected incident | the full incident + LLM explanation (drives the alert feed) |

The frontend builds its WS URL from `window.location`, so it automatically uses `wss://<space>.hf.space` in production — no hardcoded host.

---

## 💾 Storage, persistence & RAM fallback

The data layer ([`database.py`](backend/app/database.py)) chooses its backend automatically at startup:

1. **External Postgres** (Neon / Supabase / Railway) — set `DATABASE_URL` → data **persists** across restarts. The code normalizes provider URLs (rewrites the scheme to `postgresql+asyncpg://` and strips libpq-only params like `sslmode`/`channel_binding` that asyncpg rejects) and enables TLS automatically.
2. **In-memory SQLite fallback** — if the configured DB is **unreachable or errors at startup**, the app logs a warning and runs on an in-memory store (via `StaticPool`, shared for the whole process) so it **keeps working for the session** instead of crashing. Data is lost on restart.
3. **Ephemeral file SQLite** — the local-dev default when nothing is configured.

Two tables: **`metric_data_points`** (every sample) and **`detected_anomalies`** (every incident + explanation).

👉 Check which backend is live at any time via `GET /api/v1/health`:
```json
{ "status": "ok", "database": "...neon.tech/neondb", "persistent": true, "llm": "enabled" }
```

---

## 🖥️ The frontend dashboard

A single-page React app ([`frontend/src/App.jsx`](frontend/src/App.jsx)) with two views, switched from the sidebar:

- **Traffic Dashboard** — KPI cards (incidents flagged, live samples, uptime), a live line chart you can toggle between Req/s · Avg Latency · P95 · Error Rate (anomalous points are marked red), the **Active Incident Alerts** feed with LLM cards, and a scrolling **Live API Traffic Log** table.
- **Incident Feed** — the full history of incidents, hydrated from `GET /api/v1/anomalies` and merged (deduped by id) with live WebSocket arrivals.

---

## 🔌 API reference

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/metrics` | ingest one traffic sample |
| `GET` | `/api/v1/anomalies?skip=&limit=&resolved=` | list detected incidents |
| `GET` | `/api/v1/health` | active DB backend, persistence, LLM status |
| `WS` | `/api/v1/ws/alerts` | live `METRIC_UPDATE` / `NEW_ANOMALY` stream |
| `GET` | `/docs` | interactive Swagger UI |
| `GET` | `/` | the React dashboard |

---

## ⚙️ Configuration

Set these under **Space → Settings → Variables and secrets** (or in a local `backend/.env` — see [`.env.example`](backend/.env.example)). Everything is optional; with nothing set, the app runs on ephemeral SQLite with LLM disabled.

| Name | Type | Default | Purpose |
|------|------|---------|---------|
| `DATABASE_URL` | **secret** | _(empty)_ | external Postgres for persistence; falls back to RAM if unreachable |
| `GROQ_API_KEY` | **secret** | _(empty)_ | enables LLM explanations via Groq (free, fast) |
| `OPENROUTER_API_KEY` | **secret** | _(empty)_ | alternative LLM provider |
| `ENABLE_SYNTHETIC` | variable | `true` | built-in traffic generator; set `false` to ingest only external data |
| `SYNTHETIC_DELAY` | variable | `2.0` | seconds between generated samples |

---

## 🚀 How it runs on Hugging Face Spaces

This Space uses the **Docker SDK** (declared in the YAML header at the top of this file).

### The multi-stage Dockerfile
- **Stage 1 (`node:20-slim`):** `npm install` + `npm run build` compiles the React app into `frontend/dist`.
- **Stage 2 (`python:3.11-slim`):** creates a non-root user, installs `requirements.txt`, copies the backend and the built `frontend/dist`, exposes **7860**, and launches from `/app/backend`:
  ```
  uvicorn app.main:app --host 0.0.0.0 --port 7860
  ```
  > Docker Spaces **must** listen on port **7860** — that's why the app binds there.

### What happens on boot (`app/main.py` lifespan)
1. `init_db()` connects to the configured database (or falls back to RAM) and creates tables.
2. If `ENABLE_SYNTHETIC`, the in-process traffic generator starts as a background task.
3. FastAPI mounts the API under `/api/v1` and the compiled UI at `/`.

### Build & deploy lifecycle
- Pushing to the Space's git repo (`main` branch) triggers an automatic Docker build.
- Watch the **Build logs**; runtime output is in the **Logs** tab.
- When you see `Application startup complete`, `[db] connected …`, and `[synthetic] starting in-process API-traffic generator`, the Space is live.

> If a new build **fails**, Hugging Face keeps the **previous** version running — so always confirm the new UI (sidebar reads **"API Watch"**) actually loaded.

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
npm run dev        # http://localhost:5173 (proxies API to :8000)
```

---

## 🌐 Streaming your own traffic

The standalone generator ([`backend/mock_data_generator.py`](backend/mock_data_generator.py)) can target a local server **or** your hosted Space:

```bash
# Synthetic traffic to a local server
python mock_data_generator.py

# Stream to the hosted Space
python mock_data_generator.py --url https://<space>.hf.space/api/v1/metrics/

# Replay a CSV (columns: endpoint, requests_per_sec, avg_latency_ms,
# p95_latency_ms, error_rate, total_requests, error_count, bytes_per_sec, label)
python mock_data_generator.py --csv traffic.csv
```

Or POST a single sample directly:
```bash
curl -X POST https://<space>.hf.space/api/v1/metrics \
  -H "Content-Type: application/json" \
  -d '{"timestamp":"2026-01-01T00:00:00Z","endpoint":"/api/v1/login","method":"POST",
       "requests_per_sec":650,"avg_latency_ms":120,"p95_latency_ms":400,
       "error_rate":0.8,"total_requests":3250,"error_count":2600,"bytes_per_sec":260000}'
```

---

## 🗂️ Project structure

```
anomalydetection/
├── Dockerfile                     # multi-stage: build React → run FastAPI
├── README.md
├── backend/
│   ├── requirements.txt
│   ├── .env.example               # settings template
│   ├── mock_data_generator.py     # standalone traffic generator / CSV replay
│   └── app/
│       ├── main.py                # FastAPI app, lifespan, static mount, /health
│       ├── config.py              # env-driven settings
│       ├── database.py            # engine, async sessions, Postgres→RAM fallback
│       ├── api/
│       │   ├── deps.py            # get_db dependency
│       │   └── routes/            # metrics, anomalies, ws
│       ├── models/                # SQLAlchemy tables (metric, anomaly, rule)
│       ├── schemas/               # Pydantic request/response models
│       ├── engine/
│       │   ├── pipeline.py        # orchestrates detectors + voting
│       │   ├── ensemble.py        # weighted-quorum voter
│       │   └── detectors/         # zscore, mod-zscore, iqr, threshold, iforest, missing
│       ├── services/              # process_metric, handle_anomaly
│       ├── ingestion/             # in-process synthetic generator
│       ├── llm/                   # prompt builder + Groq/OpenRouter client
│       └── websocket/             # connection manager / broadcast
└── frontend/
    ├── index.html
    └── src/App.jsx                # the dashboard (Traffic + Incident Feed views)
```

---

## 📦 Tech stack

| Layer | Tech |
|-------|------|
| Frontend | React 19, Vite, Recharts, lucide-react |
| Backend | FastAPI, Uvicorn, WebSockets, async SQLAlchemy |
| Database | Postgres (asyncpg) / SQLite (aiosqlite) |
| ML / stats | NumPy, scikit-learn (Isolation Forest) |
| LLM | Groq / OpenRouter (OpenAI-compatible) |
| Deploy | Docker · Hugging Face Spaces |
