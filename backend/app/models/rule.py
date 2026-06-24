import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base

class DetectionRule(Base):
    __tablename__ = "detection_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    metric_name_pattern = Column(String(255), nullable=False, unique=True)

    detectors_enabled = Column(JSON, default=list)  # List of detector names
    detector_weights = Column(JSON, default=dict)  # Key-value overrides
    threshold_config = Column(JSON, default=dict)  # Static limits

    window_size = Column(Integer, default=100)
    cooldown_seconds = Column(Integer, default=300)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
