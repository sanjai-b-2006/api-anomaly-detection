import numpy as np
from typing import Dict, Any, Tuple
from app.engine.detectors.base import BaseDetector

class ThresholdDetector(BaseDetector):
    def __init__(self, weight: float = 2.0): # High weight since these are user-defined hard limits
        super().__init__("threshold", weight)

    def detect(self, values: np.ndarray, current: float, metadata: Dict[str, Any]) -> Tuple[bool, float, str]:
        config = metadata.get("threshold_config", {})
        if not config:
            return False, 0.0, "No threshold config"
            
        min_val = config.get("min")
        max_val = config.get("max")
        
        is_anomaly = False
        msg = []
        score = 0.0
        
        if min_val is not None and current < min_val:
            is_anomaly = True
            msg.append(f"Value < min ({min_val})")
            score = 1.0 # Absolute limit broken
            
        if max_val is not None and current > max_val:
            is_anomaly = True
            msg.append(f"Value > max ({max_val})")
            score = 1.0
            
        if not is_anomaly:
            return False, 0.0, "Within limits"
            
        return is_anomaly, score, " and ".join(msg)
