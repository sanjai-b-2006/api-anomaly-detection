import uuid
from sqlalchemy import Column, String, Float, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.database import Base

class DetectedAnomaly(Base):
    __tablename__ = "detected_anomalies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    metric_name = Column(String(255), index=True, nullable=False)
    metric_value = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)

    anomaly_type = Column(String(50))
    severity = Column(String(20))
    confidence = Column(Float)
    composite_score = Column(Float)

    detectors_triggered = Column(JSON)
    context = Column(JSON)

    llm_explanation = Column(String)
    llm_model = Column(String(100))

    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
