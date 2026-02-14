import openai
from config import AI_API_KEY, AI_MODEL

# ПРОСТЕЙШАЯ ВЕРСИЯ - БЕЗ PROXIES!
client = openai.OpenAI(
    api_key=AI_API_KEY,
    base_url="https://api.deepseek.com/v1"
)

DOCTOR_SYSTEM_PROMPT = """
Ты — опытный врач-терапевт. Твоя задача — анализировать симптомы и давать рекомендации.
Пиши обычным текстом, без звездочек.
"""

async def get_ai_advice(user_message: str, conversation_history: list = None) -> str:
    messages = [{"role": "system", "content": DOCTOR_SYSTEM_PROMPT}]
    
    if conversation_history:
        messages.extend(conversation_history)
    
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            temperature=0.8
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Извините, ошибка: {e}"