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

# In-memory cache for sliding window of network flow records
flow_history: List[Dict[str, Any]] = []
pipeline = AnomalyPipeline()

async def process_metric(db: AsyncSession, metric_in: MetricDataPointCreate) -> Optional[Dict[str, Any]]:
    # 1. Store the network flow in PostgreSQL
    db_metric = MetricDataPoint(**metric_in.model_dump())
    db.add(db_metric)
    await db.commit()
    await db.refresh(db_metric)
    
    # 2. Get active rule (using 'network_flow' as standard rule name)
    result = await db.execute(
        select(DetectionRule).where(
            DetectionRule.metric_name_pattern == "network_flow",
            DetectionRule.is_active == True
        )
    )
    rule = result.scalars().first()
    
    # Use default rule for network flow if none found
    if not rule:
        from app.schemas.rule import DetectionRuleResponse
        rule_resp = DetectionRuleResponse(
            id=uuid.uuid4(),
            metric_name_pattern="network_flow",
            detectors_enabled=["zscore", "threshold", "iqr", "isolation_forest"],
            detector_weights={
                "threshold": 2.0, 
                "isolation_forest": 1.5,
                "zscore": 1.0,
                "iqr": 1.0
            },
            threshold_config={
                "fwd_packets_s": {"max": 8000.0},
                "flow_bytes_s": {"max": 2000000.0},
                "flow_duration": {"max": 6000000.0},
                "packet_length_mean": {"max": 1100.0}
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

    # 3. Manage sliding window of flow dicts
    window_size = rule_resp.window_size
    current_flow_dict = {
        "destination_port": metric_in.destination_port,
        "flow_duration": metric_in.flow_duration,
        "total_fwd_packets": metric_in.total_fwd_packets,
        "total_bwd_packets": metric_in.total_bwd_packets,
        "fwd_packets_s": metric_in.fwd_packets_s,
        "bwd_packets_s": metric_in.bwd_packets_s,
        "flow_bytes_s": metric_in.flow_bytes_s,
        "packet_length_mean": metric_in.packet_length_mean,
        "label": metric_in.label,
        "source": metric_in.source
    }
    
    historical_flows = flow_history.copy()
    
    # Update in-memory window
    flow_history.append(current_flow_dict)
    if len(flow_history) > window_size:
        flow_history.pop(0)
        
    # 4. Broadcast live flow metrics to all WebSocket clients for live SOC monitoring
    timestamp_str = metric_in.timestamp.isoformat() if hasattr(metric_in.timestamp, 'isoformat') else str(metric_in.timestamp)
    await manager.broadcast({
        "type": "METRIC_UPDATE",
        "data": {
            "timestamp": timestamp_str,
            "destination_port": metric_in.destination_port,
            "flow_duration": metric_in.flow_duration,
            "total_fwd_packets": metric_in.total_fwd_packets,
            "total_bwd_packets": metric_in.total_bwd_packets,
            "fwd_packets_s": metric_in.fwd_packets_s,
            "bwd_packets_s": metric_in.bwd_packets_s,
            "flow_bytes_s": metric_in.flow_bytes_s,
            "packet_length_mean": metric_in.packet_length_mean,
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
        anomaly_result["metric_name"] = "network_flow"
        
        # Primary trigger feature value
        anomaly_result["metric_value"] = metric_in.fwd_packets_s
        
        # Determine anomaly type based on label or triggering features
        label = metric_in.label
        if label != "BENIGN":
            anomaly_result["anomaly_type"] = label
        elif metric_in.fwd_packets_s > 5000.0:
            anomaly_result["anomaly_type"] = "DDoS Flood"
        elif metric_in.flow_duration < 5000 and metric_in.fwd_packets_s > 1000:
            anomaly_result["anomaly_type"] = "PortScan"
        else:
            anomaly_result["anomaly_type"] = "Abnormal Flow"
            
        await handle_anomaly(db, anomaly_result)
        
    return anomaly_result
