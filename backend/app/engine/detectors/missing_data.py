import numpy as np
from typing import Dict, Any, Tuple
from app.engine.detectors.base import BaseDetector
from datetime import datetime

class MissingDataDetector(BaseDetector):
    def __init__(self, weight: float = 1.5):
        super().__init__("missing_data", weight)

    def detect(self, values: np.ndarray, current: float, metadata: Dict[str, Any]) -> Tuple[bool, float, str]:
        # This detector specifically looks at the gap between the last known point and 'now'
        # Current 'value' isn't as relevant as the time gap.
        # We rely on metadata to provide 'last_timestamp' and 'expected_interval_seconds'
        
        last_timestamp = metadata.get("last_timestamp")
        expected_interval = metadata.get("expected_interval_seconds", 60) # Default 1 min
        
        if not last_timestamp:
            return False, 0.0, "No previous timestamp"
            
        if isinstance(last_timestamp, str):
            last_timestamp = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00'))
            
        now = datetime.now(last_timestamp.tzinfo)
        gap_seconds = (now - last_timestamp).total_seconds()
        
        threshold = expected_interval * 2.5 # Allow 2.5x the normal interval before alerting
        
        if gap_seconds > threshold:
            score = min(1.0, gap_seconds / (expected_interval * 5))
            return True, score, f"No data for {gap_seconds:.0f}s (expected interval: {expected_interval}s)"
            
        return False, 0.0, f"Gap is {gap_seconds:.0f}s"
