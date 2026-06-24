from typing import List, Dict, Any, Tuple
from app.schemas.anomaly import DetectorResultSchema

class EnsembleVoter:
    def __init__(self, quorum_threshold: float = 0.5):
        self.quorum_threshold = quorum_threshold

    def evaluate(self, results: List[DetectorResultSchema], detector_weights: Dict[str, float]) -> Tuple[bool, float, float]:
        """
        Evaluates the results from all detectors and returns the final verdict.
        
        Returns:
            Tuple[bool, float, float]: (is_anomaly, composite_score, confidence)
        """
        if not results:
            return False, 0.0, 0.0
            
        total_weight = 0.0
        anomaly_weight = 0.0
        weighted_score_sum = 0.0
        
        for res in results:
            # Use override weight if provided, else default to 1.0 
            # (In reality, we'd pull the detector's default weight)
            weight = detector_weights.get(res.name, 1.0)
            
            total_weight += weight
            if res.is_anomaly:
                anomaly_weight += weight
                weighted_score_sum += (res.score * weight)
                
        if total_weight == 0:
            return False, 0.0, 0.0
            
        vote_ratio = anomaly_weight / total_weight
        is_anomaly = vote_ratio >= self.quorum_threshold
        
        # Composite score is the weighted average score of the detectors that triggered
        composite_score = (weighted_score_sum / anomaly_weight) if anomaly_weight > 0 else 0.0
        
        # Confidence is based on how unanimous the vote was
        confidence = vote_ratio
        
        return is_anomaly, composite_score, confidence
