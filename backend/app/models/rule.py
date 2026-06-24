import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base

class DetectionRule(Base):
    __tablename__ = "detection_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_name_pattern = Column(String(255), nullable=False, unique=True)
    
    detectors_enabled = Column(JSONB, default=list) # List of detector names
    detector_weights = Column(JSONB, default=dict) # Key-value overrides
    threshold_config = Column(JSONB, default=dict) # Static limits
    
    window_size = Column(Integer, default=100)
    cooldown_seconds = Column(Integer, default=300)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
