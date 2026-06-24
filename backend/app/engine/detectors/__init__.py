from app.engine.detectors.zscore import ZScoreDetector
from app.engine.detectors.modified_zscore import ModifiedZScoreDetector
from app.engine.detectors.threshold import ThresholdDetector
from app.engine.detectors.iqr import IQRDetector
from app.engine.detectors.isolation_forest import IsolationForestDetector
from app.engine.detectors.missing_data import MissingDataDetector

# For brevity in this implementation, we are exposing 6 core detectors.
# In a fully deployed system, CUSUM, EWMA, LOF, Seasonal, RateOfChange would be added here.
AVAILABLE_DETECTORS = {
    "zscore": ZScoreDetector,
    "modified_zscore": ModifiedZScoreDetector,
    "threshold": ThresholdDetector,
    "iqr": IQRDetector,
    "isolation_forest": IsolationForestDetector,
    "missing_data": MissingDataDetector
}
