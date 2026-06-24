import numpy as np
from sklearn.ensemble import IsolationForest
from typing import Dict, Any, Tuple
from app.engine.detectors.base import BaseDetector

class IsolationForestDetector(BaseDetector):
    def __init__(self, weight: float = 1.5): # ML gets higher weight
        super().__init__("isolation_forest", weight)

    def detect(self, values: np.ndarray, current: Any, metadata: Dict[str, Any]) -> Tuple[bool, float, str]:
        min_points = metadata.get("if_min_points", 15)
        if len(values) < min_points:
            return False, 0.0, f"Insufficient data (needs >={min_points})"
            
        # Check if values is 2D (multivariate)
        if len(values.shape) > 1 and values.shape[1] > 1:
            X_train = values
            X_test = np.array(current).reshape(1, -1)
            feat_type = "Multivariate"
        else:
            X_train = values.reshape(-1, 1)
            X_test = np.array([[current]])
            feat_type = "Univariate"
            
        contamination = metadata.get("if_contamination", 0.05)
        
        try:
            clf = IsolationForest(contamination=contamination, random_state=42)
            clf.fit(X_train)
            
            prediction = clf.predict(X_test)[0]
            score_raw = clf.score_samples(X_test)[0] # negative, lower is more anomalous
            
            is_anomaly = bool(prediction == -1)
            
            # Map raw score to 0-1
            # score_samples returns typical values between [-1, 0.5]
            normalized_score = max(0.0, min(1.0, (0.5 - score_raw) / 1.0)) if is_anomaly else 0.0
            
            return is_anomaly, normalized_score, f"IForest {feat_type} anomaly (raw score: {score_raw:.2f})"
        except Exception as e:
            return False, 0.0, f"IForest error: {str(e)}"
