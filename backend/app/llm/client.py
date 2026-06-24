import httpx
from app.config import settings

class OpenRouterClient:
    """
    LLM client for anomaly explanations.

    Uses Groq (free, fast, OpenAI-compatible) when GROQ_API_KEY is set,
    otherwise falls back to OpenRouter. Both share the OpenAI chat format.
    """
    def __init__(self):
        if settings.GROQ_API_KEY:
            self.provider = "groq"
            self.api_key = settings.GROQ_API_KEY
            self.base_url = "https://api.groq.com/openai/v1/chat/completions"
            self.model = settings.GROQ_MODEL
        else:
            self.provider = "openrouter"
            self.api_key = settings.OPENROUTER_API_KEY
            self.base_url = "https://openrouter.ai/api/v1/chat/completions"
            self.model = settings.LLM_MODEL

    async def generate_explanation(self, prompt: str) -> str:
        if not self.api_key:
            return "LLM Explanation disabled (no API key configured)."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # OpenRouter-specific (optional) headers; harmless for Groq but we only add for OpenRouter
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://huggingface.co"
            headers["X-Title"] = "Anomaly Detector"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an expert SRE and security analyst. Analyze the anomaly detection report and provide a clear, actionable root cause analysis in plain English. Limit response to 3-4 sentences."},
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
            print(f"Error calling {self.provider}: {e}")
            return f"Error connecting to LLM service: {str(e)}"
