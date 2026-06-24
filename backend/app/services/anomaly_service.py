from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
from datetime import datetime, timezone

from app.models.anomaly import DetectedAnomaly
from app.llm.client import OpenRouterClient
from app.llm.prompt_builder import build_anomaly_prompt
from app.websocket.manager import manager

llm_client = OpenRouterClient()

# Simple cooldown cache to prevent alert spam: {metric_name: last_alert_time}
cooldown_cache: Dict[str, datetime] = {}

async def handle_anomaly(db: AsyncSession, anomaly_data: Dict[str, Any]):
    metric_name = anomaly_data["metric_name"]
    now = datetime.now(timezone.utc)
    
    anomaly_type = anomaly_data.get("anomaly_type", "anomaly")
    
    # Check cooldown (e.g. 10 seconds for demo responsiveness)
    if anomaly_type in cooldown_cache:
        last_alert = cooldown_cache[anomaly_type]
        if (now - last_alert).total_seconds() < 10:
            print(f"Suppressing alert for {anomaly_type} (cooldown)")
            return
            
    cooldown_cache[anomaly_type] = now
    
    # 1. Generate Explanation via LLM
    prompt = build_anomaly_prompt(anomaly_data)
    explanation = await llm_client.generate_explanation(prompt)
    
    # 2. Store to Database
    db_anomaly = DetectedAnomaly(
        metric_name=metric_name,
        metric_value=anomaly_data["metric_value"],
        timestamp=now,
        anomaly_type=anomaly_data["anomaly_type"],
        severity=anomaly_data["severity"],
        confidence=anomaly_data["confidence"],
        composite_score=anomaly_data["composite_score"],
        detectors_triggered=anomaly_data["detectors_triggered"],
        context=anomaly_data["context"],
        llm_explanation=explanation,
        llm_model=llm_client.model
    )
    
    db.add(db_anomaly)
    await db.commit()
    await db.refresh(db_anomaly)
    
    # 3. Broadcast to WebSockets
    from app.schemas.anomaly import DetectedAnomalyResponse
    resp = DetectedAnomalyResponse.model_validate(db_anomaly)
    
    alert_payload = {
        "type": "NEW_ANOMALY",
        "data": resp.model_dump(mode='json')
    }
    
    await manager.broadcast(alert_payload)
