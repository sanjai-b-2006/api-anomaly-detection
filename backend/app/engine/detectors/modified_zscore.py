import numpy as np
from typing import Dict, Any, Tuple
from app.engine.detectors.base import BaseDetector

class ModifiedZScoreDetector(BaseDetector):
    def __init__(self, weight: float = 1.2): # Slightly higher weight as it's more robust
        super().__init__("modified_zscore", weight)

    def detect(self, values: np.ndarray, current: float, metadata: Dict[str, Any]) -> Tuple[bool, float, str]:
        if len(values) < 3:
            return False, 0.0, "Insufficient data"
            
        median = np.median(values)
        
        # Median Absolute Deviation (MAD)
        mad = np.median(np.abs(values - median))
        if mad == 0:
            mad = 1e-6
            
        # 0.6745 is the 75th percentile of the standard normal distribution
        mod_z = 0.6745 * abs(current - median) / mad
        threshold = metadata.get("mod_zscore_threshold", 3.5)
        
        is_anomaly = bool(mod_z > threshold)
        score = min(1.0, mod_z / (threshold * 2)) if is_anomaly else min(0.49, mod_z / threshold)
        
        return is_anomaly, score, f"Mod Z-score: {mod_z:.2f} (threshold: {threshold})"
