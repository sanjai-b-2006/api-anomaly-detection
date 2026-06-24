import numpy as np
from typing import Dict, Any, Tuple
from app.engine.detectors.base import BaseDetector

class IQRDetector(BaseDetector):
    def __init__(self, weight: float = 1.0):
        super().__init__("iqr", weight)

    def detect(self, values: np.ndarray, current: float, metadata: Dict[str, Any]) -> Tuple[bool, float, str]:
        if len(values) < 4:
            return False, 0.0, "Insufficient data"
            
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        
        multiplier = metadata.get("iqr_multiplier", 1.5)
        lower_bound = q1 - (multiplier * iqr)
        upper_bound = q3 + (multiplier * iqr)
        
        is_anomaly = bool(current < lower_bound or current > upper_bound)
        
        # Calculate score based on distance from bounds
        if not is_anomaly:
            return False, 0.0, f"Within bounds [{lower_bound:.2f}, {upper_bound:.2f}]"
            
        distance = min(abs(current - lower_bound), abs(current - upper_bound))
        # Arbitrary scaling for score: map distance relative to IQR size to [0.5, 1.0]
        score_component = min(0.5, distance / (iqr if iqr > 0 else 1.0))
        score = 0.5 + score_component
        
        return True, score, f"Outside bounds [{lower_bound:.2f}, {upper_bound:.2f}]"
