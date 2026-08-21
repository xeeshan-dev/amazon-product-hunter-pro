from groq import Groq
from typing import List, Dict, Any
import logging
from config.settings import get_settings

logger = logging.getLogger("llm_service")

class LLMService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.GROQ_API_KEY
        if not self.api_key:
            logger.warning("GROQ_API_KEY not found in environment variables.")

        self.client = Groq(api_key=self.api_key) if self.api_key else None
        self.model = settings.LLM_MODEL

    async def get_chat_response(self, messages: List[Dict[str, str]]) -> str:
        if not self.client:
            return "Error: Groq API client not initialized. Please check your GROQ_API_KEY."

        try:
            # Add system prompt if not present
            if not any(m.get("role") == "system" for m in messages):
                messages.insert(0, {
                    "role": "system",
                    "content": "You are a helpful assistant for Amazon Hunter Pro, an advanced Amazon product research tool. You help users analyze market trends, evaluate product opportunities, and understand metrics like demand, competition, and profit. Be concise and professional."
                })

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2048,
                top_p=1,
                stream=False,
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return f"I'm sorry, I'm having trouble connecting to my brain right now. (Error: {str(e)})"
