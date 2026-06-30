"""
Standalone API-traffic generator / replayer.

Streams synthetic web/API traffic samples (with periodic incidents) to the
detector's REST endpoint. Point it at a local server or your hosted Hugging
Face Space with --url.

Examples
--------
# Stream synthetic traffic to a local server:
python mock_data_generator.py

# Stream to your hosted Space:
python mock_data_generator.py --url https://sanjaib00001-anomalydetection.hf.space/api/v1/metrics/

# Replay a CSV with columns: endpoint, requests_per_sec, avg_latency_ms,
# p95_latency_ms, error_rate, total_requests, error_count, bytes_per_sec, label
python mock_data_generator.py --csv traffic.csv
"""
import asyncio
import httpx
import random
import math
import argparse
import sys
import os
from datetime import datetime, timezone
import pandas as pd

DEFAULT_URL = "http://localhost:8000/api/v1/metrics/"

ENDPOINTS = [
    ("GET", "/api/v1/products"),
    ("GET", "/api/v1/products/{id}"),
    ("POST", "/api/v1/login"),
    ("POST", "/api/v1/checkout"),
    ("GET", "/api/v1/search"),
    ("GET", "/api/v1/cart"),
]


def parse_args():
    parser = argparse.ArgumentParser(description="API Traffic Anomaly Generator & CSV Replay")
    parser.add_argument("--url", type=str, default=DEFAULT_URL, help="Target metrics endpoint URL")
    parser.add_argument("--csv", type=str, default="", help="Path to a traffic CSV to replay")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between samples in seconds")
    return parser.parse_args()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def send_sample(client, url, sample):
    try:
        response = await client.post(url, json=sample)
        label = sample.get("label", "NORMAL")
        marker = "[INCIDENT]" if label != "NORMAL" else "[NORMAL]"
        print(f"{marker} {sample['method']} {sample['endpoint']} | "
              f"rps={sample['requests_per_sec']:.1f} | "
              f"p95={sample['p95_latency_ms']:.0f}ms | "
              f"err={sample['error_rate']*100:.1f}% | "
              f"label={label} | API: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Error sending sample: {e}")


def _normal() -> dict:
    method, endpoint = random.choice(ENDPOINTS)
    rps = random.uniform(20.0, 120.0)
    total = int(rps * 5)
    err_rate = random.uniform(0.0, 0.02)
    avg_lat = random.uniform(40.0, 180.0)
    return {
        "timestamp": _now(), "endpoint": endpoint, "method": method,
        "requests_per_sec": round(rps, 1),
        "avg_latency_ms": round(avg_lat, 1),
        "p95_latency_ms": round(avg_lat * random.uniform(1.5, 2.5), 1),
        "error_rate": round(err_rate, 4),
        "total_requests": total, "error_count": int(total * err_rate),
        "bytes_per_sec": round(rps * random.uniform(800.0, 4000.0), 1),
        "label": "NORMAL", "tags": {"environment": "production"},
        "source": "external_generator",
    }


def _incident(kind: str) -> dict:
    if kind == "Traffic Surge":
        rps = random.uniform(800.0, 3000.0); err = random.uniform(0.05, 0.25)
        endpoint, method = "/api/v1/products", "GET"
        avg, p95 = random.uniform(400, 900), random.uniform(1500, 3500)
    elif kind == "Latency Spike":
        rps = random.uniform(40.0, 150.0); err = random.uniform(0.02, 0.1)
        endpoint, method = "/api/v1/checkout", "POST"
        avg, p95 = random.uniform(1500, 4000), random.uniform(4000, 9000)
    elif kind == "Error Spike":
        rps = random.uniform(60.0, 200.0); err = random.uniform(0.3, 0.6)
        endpoint, method = "/api/v1/search", "GET"
        avg, p95 = random.uniform(200, 600), random.uniform(800, 2000)
    elif kind == "Service Outage":
        rps = random.uniform(5.0, 40.0); err = random.uniform(0.85, 1.0)
        endpoint, method = "/api/v1/cart", "GET"
        avg, p95 = random.uniform(50, 300), random.uniform(300, 1200)
    else:  # Brute Force
        rps = random.uniform(300.0, 800.0); err = random.uniform(0.6, 0.95)
        endpoint, method = "/api/v1/login", "POST"
        avg, p95 = random.uniform(80, 250), random.uniform(300, 900)

    total = int(rps * 5)
    return {
        "timestamp": _now(), "endpoint": endpoint, "method": method,
        "requests_per_sec": round(rps, 1),
        "avg_latency_ms": round(avg, 1), "p95_latency_ms": round(p95, 1),
        "error_rate": round(err, 4),
        "total_requests": total, "error_count": int(total * err),
        "bytes_per_sec": round(rps * 1500.0, 1),
        "label": kind, "tags": {"incident": kind.lower().replace(" ", "_")},
        "source": "external_generator",
    }


async def generate_synthetic_traffic(url, delay):
    print("[START] Synthetic API-traffic generator")
    incidents = ["Traffic Surge", "Latency Spike", "Error Spike", "Service Outage", "Brute Force"]
    async with httpx.AsyncClient(timeout=10.0) as client:
        step = 0
        while True:
            if step > 0 and step % 20 == 0:
                kind = random.choice(incidents)
                print(f"\n[WARN] >>> INJECTING INCIDENT: {kind.upper()} <<<\n")
                for _ in range(6):
                    await send_sample(client, url, _incident(kind))
                    await asyncio.sleep(0.4)
            else:
                await send_sample(client, url, _normal())
            step += 1
            await asyncio.sleep(delay)


def normalize_csv_columns(df):
    mapping = {}
    for col in df.columns:
        c = col.strip().lower()
        if c in ("endpoint", "path", "route"): mapping[col] = "endpoint"
        elif c in ("method", "http_method"): mapping[col] = "method"
        elif "requests" in c and ("sec" in c or "rate" in c): mapping[col] = "requests_per_sec"
        elif "p95" in c: mapping[col] = "p95_latency_ms"
        elif ("avg" in c or "mean" in c) and "lat" in c: mapping[col] = "avg_latency_ms"
        elif "error" in c and ("rate" in c or "ratio" in c): mapping[col] = "error_rate"
        elif "error" in c and "count" in c: mapping[col] = "error_count"
        elif "total" in c and "request" in c: mapping[col] = "total_requests"
        elif "bytes" in c: mapping[col] = "bytes_per_sec"
        elif c == "label": mapping[col] = "label"
    df.rename(columns=mapping, inplace=True)
    return df


async def replay_csv(url, csv_path, delay):
    print(f"[REPLAY] Replaying traffic from: {csv_path}")
    if not os.path.exists(csv_path):
        print(f"[ERROR] CSV not found at {csv_path}")
        return
    df = normalize_csv_columns(pd.read_csv(csv_path))
    required = ["endpoint", "requests_per_sec", "avg_latency_ms", "p95_latency_ms",
                "error_rate", "total_requests", "error_count", "bytes_per_sec"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"[ERROR] CSV missing columns: {missing}. Found: {list(df.columns)}")
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        for _, row in df.iterrows():
            def num(v, default=0.0):
                v = float(v)
                return default if (math.isnan(v) or math.isinf(v)) else v
            sample = {
                "timestamp": _now(),
                "endpoint": str(row["endpoint"]),
                "method": str(row.get("method", "GET")),
                "requests_per_sec": num(row["requests_per_sec"]),
                "avg_latency_ms": num(row["avg_latency_ms"]),
                "p95_latency_ms": num(row["p95_latency_ms"]),
                "error_rate": num(row["error_rate"]),
                "total_requests": int(num(row["total_requests"])),
                "error_count": int(num(row["error_count"])),
                "bytes_per_sec": num(row["bytes_per_sec"]),
                "label": str(row.get("label", "NORMAL")).strip(),
                "tags": {"mode": "csv_replay", "filename": os.path.basename(csv_path)},
                "source": "csv_replay",
            }
            await send_sample(client, url, sample)
            await asyncio.sleep(delay)


if __name__ == "__main__":
    args = parse_args()
    print("====================================================")
    print("API TRAFFIC ANOMALY GENERATOR")
    print(f"Target API: {args.url}")
    print("====================================================")
    try:
        if args.csv:
            asyncio.run(replay_csv(args.url, args.csv, args.delay))
        else:
            asyncio.run(generate_synthetic_traffic(args.url, args.delay))
    except KeyboardInterrupt:
        print("\nStopped generator.")
        sys.exit(0)
