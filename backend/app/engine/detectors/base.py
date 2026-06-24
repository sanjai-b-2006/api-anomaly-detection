from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, Any, Tuple

class BaseDetector(ABC):
    def __init__(self, name: str, weight: float = 1.0):
        self.name = name
        self.weight = weight

    @abstractmethod
    def detect(self, values: np.ndarray, current: float, metadata: Dict[str, Any]) -> Tuple[bool, float, str]:
        """
        Analyzes the current value against historical values.
        
        Args:
            values (np.ndarray): Historical values window.
            current (float): The current value to evaluate.
            metadata (Dict[str, Any]): Additional context or configuration.
            
        Returns:
            Tuple[bool, float, str]: (is_anomaly, anomaly_score_0_to_1, detail_message)
        """
        pass
