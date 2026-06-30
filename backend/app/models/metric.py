import uuid
from sqlalchemy import Column, String, Float, Integer, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base

class MetricDataPoint(Base):
    __tablename__ = "metric_data_points"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)

    # Web / API traffic metrics (per endpoint, per time window)
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), default="GET")
    requests_per_sec = Column(Float, nullable=False)
    avg_latency_ms = Column(Float, nullable=False)
    p95_latency_ms = Column(Float, nullable=False)
    error_rate = Column(Float, nullable=False)
    total_requests = Column(Integer, nullable=False)
    error_count = Column(Integer, nullable=False)
    bytes_per_sec = Column(Float, nullable=False)

    label = Column(String(100), default="NORMAL", index=True)

    tags = Column(JSON, default=dict)
    source = Column(String(100), default="mock")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
