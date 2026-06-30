"""
In-process synthetic API-traffic generator.

Runs as an asyncio background task inside the FastAPI app so the live dashboard
shows data without any external generator process. Feeds the existing
`process_metric` pipeline directly (no HTTP self-calls).
"""
import asyncio
import random
from datetime import datetime, timezone

from app.database import AsyncSessionLocal
from app.schemas.metric import MetricDataPointCreate
from app.services.metric_service import process_metric

ENDPOINTS = [
    ("GET", "/api/v1/products"),
    ("GET", "/api/v1/products/{id}"),
    ("POST", "/api/v1/login"),
    ("POST", "/api/v1/checkout"),
    ("GET", "/api/v1/search"),
    ("GET", "/api/v1/cart"),
]


async def _send(payload: dict):
    """Push one traffic sample through the real pipeline using a fresh DB session."""
    try:
        async with AsyncSessionLocal() as db:
            await process_metric(db, MetricDataPointCreate(**payload))
    except Exception as e:  # keep the loop alive on any single failure
        print(f"[synthetic] error processing sample: {e}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normal() -> dict:
    method, endpoint = random.choice(ENDPOINTS)
    rps = random.uniform(20.0, 120.0)
    total = int(rps * 5)                       # ~5s window
    err_rate = random.uniform(0.0, 0.02)       # healthy: under 2% errors
    avg_lat = random.uniform(40.0, 180.0)
    return {
        "timestamp": _now(),
        "endpoint": endpoint,
        "method": method,
        "requests_per_sec": round(rps, 1),
        "avg_latency_ms": round(avg_lat, 1),
        "p95_latency_ms": round(avg_lat * random.uniform(1.5, 2.5), 1),
        "error_rate": round(err_rate, 4),
        "total_requests": total,
        "error_count": int(total * err_rate),
        "bytes_per_sec": round(rps * random.uniform(800.0, 4000.0), 1),
        "label": "NORMAL",
        "tags": {"environment": "production"},
        "source": "synthetic_generator",
    }


async def run_synthetic_traffic(delay: float = 2.0):
    print("[synthetic] starting in-process API-traffic generator")
    step = 0
    while True:
        try:
            is_incident = step > 0 and step % 20 == 0
            incident = random.choice(
                ["Traffic Surge", "Latency Spike", "Error Spike", "Service Outage", "Brute Force"]
            ) if is_incident else "NORMAL"

            if not is_incident:
                await _send(_normal())
                await asyncio.sleep(delay)

            elif incident == "Traffic Surge":
                # Sudden 10x+ flood of requests (viral spike or DDoS)
                for _ in range(8):
                    rps = random.uniform(800.0, 3000.0)
                    total = int(rps * 5)
                    err = random.uniform(0.05, 0.25)
                    await _send({
                        "timestamp": _now(), "endpoint": "/api/v1/products", "method": "GET",
                        "requests_per_sec": round(rps, 1),
                        "avg_latency_ms": round(random.uniform(400.0, 900.0), 1),
                        "p95_latency_ms": round(random.uniform(1500.0, 3500.0), 1),
                        "error_rate": round(err, 4),
                        "total_requests": total, "error_count": int(total * err),
                        "bytes_per_sec": round(rps * 2500.0, 1),
                        "label": "Traffic Surge", "tags": {"incident": "traffic_surge"},
                        "source": "synthetic_generator",
                    })
                    await asyncio.sleep(0.4)

            elif incident == "Latency Spike":
                # Response times blow past SLO (slow dependency / DB contention)
                for _ in range(5):
                    rps = random.uniform(40.0, 150.0)
                    total = int(rps * 5)
                    err = random.uniform(0.02, 0.1)
                    await _send({
                        "timestamp": _now(), "endpoint": "/api/v1/checkout", "method": "POST",
                        "requests_per_sec": round(rps, 1),
                        "avg_latency_ms": round(random.uniform(1500.0, 4000.0), 1),
                        "p95_latency_ms": round(random.uniform(4000.0, 9000.0), 1),
                        "error_rate": round(err, 4),
                        "total_requests": total, "error_count": int(total * err),
                        "bytes_per_sec": round(rps * 1500.0, 1),
                        "label": "Latency Spike", "tags": {"incident": "latency_spike"},
                        "source": "synthetic_generator",
                    })
                    await asyncio.sleep(0.5)

            elif incident == "Error Spike":
                # A bad deploy: error rate jumps well above the budget
                for _ in range(5):
                    rps = random.uniform(60.0, 200.0)
                    total = int(rps * 5)
                    err = random.uniform(0.3, 0.6)
                    await _send({
                        "timestamp": _now(), "endpoint": "/api/v1/search", "method": "GET",
                        "requests_per_sec": round(rps, 1),
                        "avg_latency_ms": round(random.uniform(200.0, 600.0), 1),
                        "p95_latency_ms": round(random.uniform(800.0, 2000.0), 1),
                        "error_rate": round(err, 4),
                        "total_requests": total, "error_count": int(total * err),
                        "bytes_per_sec": round(rps * 1200.0, 1),
                        "label": "Error Spike", "tags": {"incident": "error_spike"},
                        "source": "synthetic_generator",
                    })
                    await asyncio.sleep(0.5)

            elif incident == "Service Outage":
                # Backend down: almost everything 5xx, throughput collapses
                for _ in range(4):
                    rps = random.uniform(5.0, 40.0)
                    total = int(rps * 5)
                    err = random.uniform(0.85, 1.0)
                    await _send({
                        "timestamp": _now(), "endpoint": "/api/v1/cart", "method": "GET",
                        "requests_per_sec": round(rps, 1),
                        "avg_latency_ms": round(random.uniform(50.0, 300.0), 1),
                        "p95_latency_ms": round(random.uniform(300.0, 1200.0), 1),
                        "error_rate": round(err, 4),
                        "total_requests": total, "error_count": int(total * err),
                        "bytes_per_sec": round(rps * 200.0, 1),
                        "label": "Service Outage", "tags": {"incident": "outage"},
                        "source": "synthetic_generator",
                    })
                    await asyncio.sleep(0.5)

            elif incident == "Brute Force":
                # Credential-stuffing on the login endpoint: high rate, high 401s
                for _ in range(6):
                    rps = random.uniform(300.0, 800.0)
                    total = int(rps * 5)
                    err = random.uniform(0.6, 0.95)
                    await _send({
                        "timestamp": _now(), "endpoint": "/api/v1/login", "method": "POST",
                        "requests_per_sec": round(rps, 1),
                        "avg_latency_ms": round(random.uniform(80.0, 250.0), 1),
                        "p95_latency_ms": round(random.uniform(300.0, 900.0), 1),
                        "error_rate": round(err, 4),
                        "total_requests": total, "error_count": int(total * err),
                        "bytes_per_sec": round(rps * 400.0, 1),
                        "label": "Brute Force", "tags": {"incident": "brute_force"},
                        "source": "synthetic_generator",
                    })
                    await asyncio.sleep(0.4)

            step += 1
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            print("[synthetic] generator stopped")
            break
        except Exception as e:
            print(f"[synthetic] loop error: {e}")
            await asyncio.sleep(delay)
