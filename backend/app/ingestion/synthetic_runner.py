"""
In-process synthetic network-traffic generator.

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

SCAN_PORTS = [21, 22, 23, 25, 53, 80, 110, 135, 139, 443, 445, 1433, 3306, 3389, 8080]


async def _send(payload: dict):
    """Push one flow through the real pipeline using a fresh DB session."""
    try:
        async with AsyncSessionLocal() as db:
            await process_metric(db, MetricDataPointCreate(**payload))
    except Exception as e:  # keep the loop alive on any single failure
        print(f"[synthetic] error processing flow: {e}")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _benign() -> dict:
    return {
        "timestamp": _now(),
        "destination_port": random.choice([80, 443, 53, 22]),
        "flow_duration": float(random.randint(15000, 1500000)),
        "total_fwd_packets": random.randint(2, 15),
        "total_bwd_packets": random.randint(1, 15),
        "fwd_packets_s": float(random.uniform(5.0, 150.0)),
        "bwd_packets_s": float(random.uniform(5.0, 150.0)),
        "flow_bytes_s": float(random.uniform(500.0, 25000.0)),
        "packet_length_mean": float(random.uniform(64.0, 320.0)),
        "label": "BENIGN",
        "tags": {"environment": "production"},
        "source": "synthetic_generator",
    }


async def run_synthetic_traffic(delay: float = 2.0):
    print("[synthetic] starting in-process traffic generator")
    step = 0
    while True:
        try:
            is_attack = step > 0 and step % 20 == 0
            attack_type = random.choice(["DDoS", "PortScan", "DoS Hulk", "Infiltration"]) if is_attack else "BENIGN"

            if not is_attack:
                await _send(_benign())
                await asyncio.sleep(delay)

            elif attack_type == "DDoS":
                for _ in range(8):
                    await _send({
                        "timestamp": _now(), "destination_port": 80,
                        "flow_duration": float(random.randint(100, 1000)),
                        "total_fwd_packets": random.randint(500, 3000),
                        "total_bwd_packets": random.randint(0, 2),
                        "fwd_packets_s": float(random.uniform(50000.0, 250000.0)),
                        "bwd_packets_s": float(random.uniform(0, 10.0)),
                        "flow_bytes_s": float(random.uniform(10000000.0, 50000000.0)),
                        "packet_length_mean": float(random.uniform(40.0, 64.0)),
                        "label": "DDoS", "tags": {"attack_category": "DDoS_Flood"},
                        "source": "synthetic_generator",
                    })
                    await asyncio.sleep(0.4)

            elif attack_type == "PortScan":
                for scan_port in SCAN_PORTS[:8]:
                    await _send({
                        "timestamp": _now(), "destination_port": scan_port,
                        "flow_duration": float(random.randint(50, 800)),
                        "total_fwd_packets": 1, "total_bwd_packets": 0,
                        "fwd_packets_s": float(random.uniform(10000.0, 20000.0)),
                        "bwd_packets_s": 0.0, "flow_bytes_s": 40.0,
                        "packet_length_mean": 40.0, "label": "PortScan",
                        "tags": {"attack_category": "Port_Scanning"},
                        "source": "synthetic_generator",
                    })
                    await asyncio.sleep(0.3)

            elif attack_type == "DoS Hulk":
                for _ in range(4):
                    await _send({
                        "timestamp": _now(), "destination_port": 443,
                        "flow_duration": float(random.randint(100000, 800000)),
                        "total_fwd_packets": random.randint(80, 250),
                        "total_bwd_packets": random.randint(80, 250),
                        "fwd_packets_s": float(random.uniform(1200.0, 4500.0)),
                        "bwd_packets_s": float(random.uniform(1200.0, 4500.0)),
                        "flow_bytes_s": float(random.uniform(1500000.0, 4000000.0)),
                        "packet_length_mean": float(random.uniform(800.0, 1400.0)),
                        "label": "DoS Hulk", "tags": {"attack_category": "DoS_Hulk"},
                        "source": "synthetic_generator",
                    })
                    await asyncio.sleep(0.5)

            elif attack_type == "Infiltration":
                await _send({
                    "timestamp": _now(), "destination_port": 4444,
                    "flow_duration": 9000000.0, "total_fwd_packets": 6,
                    "total_bwd_packets": 4, "fwd_packets_s": 0.66,
                    "bwd_packets_s": 0.44, "flow_bytes_s": 120.0,
                    "packet_length_mean": 60.0, "label": "Infiltration",
                    "tags": {"attack_category": "Remote_Access_Backdoor"},
                    "source": "synthetic_generator",
                })
                await asyncio.sleep(delay)

            step += 1
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            print("[synthetic] generator stopped")
            break
        except Exception as e:
            print(f"[synthetic] loop error: {e}")
            await asyncio.sleep(delay)
