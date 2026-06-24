import uuid
from sqlalchemy import Column, String, Float, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.database import Base

class MetricDataPoint(Base):
    """
    Represents a network flow data point matching the CIC-IDS-2017 schema.
    We retain the class name 'MetricDataPoint' for compatibility but structure it
    specifically for network intrusion features.
    """
    __tablename__ = "metric_data_points"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)
    
    # Network Flow features from CIC-IDS-2017
    destination_port = Column(Integer, nullable=False)
    flow_duration = Column(Float, nullable=False)
    total_fwd_packets = Column(Integer, nullable=False)
    total_bwd_packets = Column(Integer, nullable=False)
    fwd_packets_s = Column(Float, nullable=False)
    bwd_packets_s = Column(Float, nullable=False)
    flow_bytes_s = Column(Float, nullable=False)
    packet_length_mean = Column(Float, nullable=False)
    
    # Classification labels (e.g. BENIGN, DDoS, PortScan, etc.)
    label = Column(String(100), default="BENIGN", index=True)
    
    tags = Column(JSONB, default=dict)
    source = Column(String(100), default="mock")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
