import numpy as np
from typing import Dict, Any, Tuple
from app.engine.detectors.base import BaseDetector

class ZScoreDetector(BaseDetector):
    def __init__(self, weight: float = 1.0):
        super().__init__("zscore", weight)

    def detect(self, values: np.ndarray, current: float, metadata: Dict[str, Any]) -> Tuple[bool, float, str]:
        if len(values) < 2:
            return False, 0.0, "Insufficient data"
            
        mean = np.mean(values)
        std = np.std(values)
        
        if std == 0:
            std = 1e-6
            
        z = abs(current - mean) / std
        threshold = metadata.get("zscore_threshold", 3.0)
        
        is_anomaly = bool(z > threshold)
        
        # Scale score from 0 to 1 based on how far past threshold we are
        score = min(1.0, z / (threshold * 2)) if is_anomaly else min(0.49, z / threshold)
        
        return is_anomaly, score, f"Z-score: {z:.2f} (threshold: {threshold})"
