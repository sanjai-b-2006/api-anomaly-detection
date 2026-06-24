from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID

class DetectionRuleCreate(BaseModel):
    metric_name_pattern: str
    detectors_enabled: Optional[List[str]] = []
    detector_weights: Optional[Dict[str, float]] = {}
    threshold_config: Optional[Dict[str, Any]] = {}
    window_size: Optional[int] = 100
    cooldown_seconds: Optional[int] = 300
    is_active: Optional[bool] = True

class DetectionRuleUpdate(BaseModel):
    detectors_enabled: Optional[List[str]] = None
    detector_weights: Optional[Dict[str, float]] = None
    threshold_config: Optional[Dict[str, Any]] = None
    window_size: Optional[int] = None
    cooldown_seconds: Optional[int] = None
    is_active: Optional[bool] = None

class DetectionRuleResponse(DetectionRuleCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
