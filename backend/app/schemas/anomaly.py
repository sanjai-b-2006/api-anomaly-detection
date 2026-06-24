from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID

class DetectorResultSchema(BaseModel):
    name: str
    is_anomaly: bool
    score: float
    detail: str

class DetectedAnomalyCreate(BaseModel):
    metric_name: str
    metric_value: float
    timestamp: datetime
    anomaly_type: str
    severity: str
    confidence: float
    composite_score: float
    detectors_triggered: List[Dict[str, Any]] # e.g. [{"name": "zscore", ...}]
    context: Dict[str, Any]
    llm_explanation: Optional[str] = None
    llm_model: Optional[str] = None

class DetectedAnomalyResponse(DetectedAnomalyCreate):
    id: UUID
    resolved: bool
    resolved_at: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
