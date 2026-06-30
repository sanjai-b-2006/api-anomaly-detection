from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import UUID

class MetricDataPointCreate(BaseModel):
    timestamp: datetime
    endpoint: str                       # e.g. "/api/v1/login"
    method: Optional[str] = "GET"       # HTTP method
    requests_per_sec: float             # traffic volume
    avg_latency_ms: float               # mean response time
    p95_latency_ms: float               # tail (95th percentile) response time
    error_rate: float                   # fraction of failed requests (0.0 - 1.0)
    total_requests: int                 # requests counted in this window
    error_count: int                    # failed (4xx/5xx) requests in window
    bytes_per_sec: float                # response throughput
    label: Optional[str] = "NORMAL"     # NORMAL, or an incident type
    tags: Optional[Dict[str, Any]] = {}
    source: Optional[str] = "mock"

class MetricDataPointResponse(MetricDataPointCreate):
    id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
