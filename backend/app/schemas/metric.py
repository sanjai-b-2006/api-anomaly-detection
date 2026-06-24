from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID

class MetricDataPointCreate(BaseModel):
    timestamp: datetime
    destination_port: int
    flow_duration: float
    total_fwd_packets: int
    total_bwd_packets: int
    fwd_packets_s: float
    bwd_packets_s: float
    flow_bytes_s: float
    packet_length_mean: float
    label: Optional[str] = "BENIGN"
    tags: Optional[Dict[str, Any]] = {}
    source: Optional[str] = "mock"

class MetricDataPointResponse(MetricDataPointCreate):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
