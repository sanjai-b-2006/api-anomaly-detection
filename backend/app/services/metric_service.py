from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from app.models.metric import MetricDataPoint
from app.models.rule import DetectionRule
from app.schemas.metric import MetricDataPointCreate
from app.engine.pipeline import AnomalyPipeline
from app.services.anomaly_service import handle_anomaly
from app.websocket.manager import manager

# In-memory cache for sliding window of API traffic samples
flow_history: List[Dict[str, Any]] = []
pipeline = AnomalyPipeline()

async def process_metric(db: AsyncSession, metric_in: MetricDataPointCreate) -> Optional[Dict[str, Any]]:
    # 1. Store the traffic sample
    db_metric = MetricDataPoint(**metric_in.model_dump())
    db.add(db_metric)
    await db.commit()
    await db.refresh(db_metric)

    # 2. Get active rule (using 'api_traffic' as standard rule name)
    result = await db.execute(
        select(DetectionRule).where(
            DetectionRule.metric_name_pattern == "api_traffic",
            DetectionRule.is_active == True
        )
    )
    rule = result.scalars().first()

    # Use default rule for API traffic if none found
    if not rule:
        from app.schemas.rule import DetectionRuleResponse
        rule_resp = DetectionRuleResponse(
            id=uuid.uuid4(),
            metric_name_pattern="api_traffic",
            detectors_enabled=["zscore", "threshold", "iqr", "isolation_forest"],
            detector_weights={
                "threshold": 2.0,
                "isolation_forest": 1.5,
                "zscore": 1.0,
                "iqr": 1.0
            },
            threshold_config={
                "requests_per_sec": {"max": 500.0},
                "avg_latency_ms": {"max": 1000.0},
                "p95_latency_ms": {"max": 2000.0},
                "error_rate": {"max": 0.2}
            },
            window_size=100,
            cooldown_seconds=10,  # 10s cooldown for demo responsiveness
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    else:
        from app.schemas.rule import DetectionRuleResponse
        rule_resp = DetectionRuleResponse.model_validate(rule)

    # 3. Manage sliding window of traffic-sample dicts
    window_size = rule_resp.window_size
    current_flow_dict = {
        "endpoint": metric_in.endpoint,
        "method": metric_in.method,
        "requests_per_sec": metric_in.requests_per_sec,
        "avg_latency_ms": metric_in.avg_latency_ms,
        "p95_latency_ms": metric_in.p95_latency_ms,
        "error_rate": metric_in.error_rate,
        "total_requests": metric_in.total_requests,
        "error_count": metric_in.error_count,
        "bytes_per_sec": metric_in.bytes_per_sec,
        "label": metric_in.label,
        "source": metric_in.source
    }

    historical_flows = flow_history.copy()

    # Update in-memory window
    flow_history.append(current_flow_dict)
    if len(flow_history) > window_size:
        flow_history.pop(0)

    # 4. Broadcast live traffic metrics to all WebSocket clients for the live dashboard
    timestamp_str = metric_in.timestamp.isoformat() if hasattr(metric_in.timestamp, 'isoformat') else str(metric_in.timestamp)
    await manager.broadcast({
        "type": "METRIC_UPDATE",
        "data": {
            "timestamp": timestamp_str,
            "endpoint": metric_in.endpoint,
            "method": metric_in.method,
            "requests_per_sec": metric_in.requests_per_sec,
            "avg_latency_ms": metric_in.avg_latency_ms,
            "p95_latency_ms": metric_in.p95_latency_ms,
            "error_rate": metric_in.error_rate,
            "total_requests": metric_in.total_requests,
            "error_count": metric_in.error_count,
            "bytes_per_sec": metric_in.bytes_per_sec,
            "label": metric_in.label,
            "source": metric_in.source
        }
    })

    # 5. Run through Anomaly Engine
    anomaly_result = pipeline.process(
        current_flow=current_flow_dict,
        historical_flows=historical_flows,
        rule=rule_resp,
        metadata={"timestamp": timestamp_str}
    )

    # 6. Handle Anomaly if detected
    if anomaly_result:
        # Map values to anomaly table format
        anomaly_result["metric_name"] = "api_traffic"

        # Primary trigger feature value
        anomaly_result["metric_value"] = metric_in.requests_per_sec

        # Determine incident type based on label or triggering features
        label = metric_in.label
        if label != "NORMAL":
            anomaly_result["anomaly_type"] = label
        elif metric_in.error_rate >= 0.5:
            anomaly_result["anomaly_type"] = "Service Outage"
        elif metric_in.error_rate >= 0.2:
            anomaly_result["anomaly_type"] = "Error Spike"
        elif metric_in.requests_per_sec > 500.0:
            anomaly_result["anomaly_type"] = "Traffic Surge"
        elif metric_in.p95_latency_ms > 2000.0 or metric_in.avg_latency_ms > 1000.0:
            anomaly_result["anomaly_type"] = "Latency Spike"
        else:
            anomaly_result["anomaly_type"] = "Abnormal Traffic"

        await handle_anomaly(db, anomaly_result)

    return anomaly_result
