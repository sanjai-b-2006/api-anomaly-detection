from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Real-time API Traffic Anomaly Detector"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./anomaly.db"
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_METRICS: str = "metrics.raw"
    KAFKA_CONSUMER_GROUP: str = "anomaly-detector-group"
    
    # LLM provider — Groq (free, fast) or OpenRouter.
    # If GROQ_API_KEY is set, Groq is used automatically.
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OPENROUTER_API_KEY: str = ""
    LLM_MODEL: str = "meta-llama/llama-3.2-3b-instruct:free" # OpenRouter free model, configurable
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # Ensemble Engine settings
    ANOMALY_CONFIDENCE_THRESHOLD: float = 0.5
    COOLDOWN_SECONDS: int = 300 # Wait 5 minutes before alerting on same metric

    # Built-in synthetic traffic generator (for live demo on hosted deployments)
    ENABLE_SYNTHETIC: bool = True
    SYNTHETIC_DELAY: float = 2.0

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
