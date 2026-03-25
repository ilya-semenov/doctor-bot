import openai
from config import AI_API_KEY, AI_MODEL

client = openai.OpenAI(
    api_key=AI_API_KEY,
    base_url="https://api.deepseek.com/v1"
)

DOCTOR_SYSTEM_PROMPT = """
Ты — опытный врач-терапевт. Твоя задача — проанализировать симптомы и дать предварительную рекомендацию.
Следуй строгим правилам:
1. Не ставь окончательный диагноз. Всегда подчеркивай, что это лишь предположение.
2. На основе симптомов порекомендуй, к какому специалисту обратиться.
3. Определи уровень срочности.
"""

async def get_ai_advice(user_message: str, conversation_history: list = None) -> str:
    """
    Функция принимает:
    - user_message: сообщение пользователя
    - conversation_history: история диалога (опционально)
    """
    
    messages = [{"role": "system", "content": DOCTOR_SYSTEM_PROMPT}]
    
    # Добавляем историю, если она есть
    if conversation_history:
        messages.extend(conversation_history)
    
    # Добавляем текущее сообщение
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Извините, ошибка: {e}"
