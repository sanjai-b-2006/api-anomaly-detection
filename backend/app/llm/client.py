import httpx
import json
from app.config import settings

class OpenRouterClient:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = settings.LLM_MODEL
        
    async def generate_explanation(self, prompt: str) -> str:
        if not self.api_key:
            return "LLM Explanation disabled (no OpenRouter API key configured)."
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8000", # Required by OpenRouter
            "X-Title": "Anomaly Detector", # Required by OpenRouter
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an expert SRE and data engineer. Analyze the anomaly detection report and provide a clear, actionable root cause analysis in plain English. Limit response to 3-4 sentences."},
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                return "Failed to generate explanation from LLM."
        except Exception as e:
            print(f"Error calling OpenRouter: {e}")
            return f"Error connecting to LLM service: {str(e)}"
