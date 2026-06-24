import uuid
from sqlalchemy import Column, String, Float, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base

class DetectedAnomaly(Base):
    __tablename__ = "detected_anomalies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_name = Column(String(255), index=True, nullable=False)
    metric_value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)
    
    anomaly_type = Column(String(50)) # spike, drop, missing, drift
    severity = Column(String(20)) # low, medium, high, critical
    confidence = Column(Float) # 0.0 - 1.0
    composite_score = Column(Float)
    
    detectors_triggered = Column(JSONB) # list of dicts
    context = Column(JSONB) # baseline stats, time context
    
    llm_explanation = Column(String) # Text explanation
    llm_model = Column(String(100))
    
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
