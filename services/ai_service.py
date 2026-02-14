import openai
from config import AI_API_KEY, AI_MODEL

# Исправленный способ создания клиента для новых версий openai
client = openai.OpenAI(
    api_key=AI_API_KEY,
    base_url="https://api.deepseek.com/v1"
    # Убираем http_client и proxies - они больше не нужны!
)

DOCTOR_SYSTEM_PROMPT = """
Ты — опытный врач-терапевт. Твоя задача — анализировать симптомы и давать рекомендации.

ВАЖНЫЕ ПРАВИЛА ОФОРМЛЕНИЯ ОТВЕТОВ:
1. Никогда не используй звездочки (*) в тексте
2. Не используй markdown, жирный шрифт, курсив
3. Пиши обычным текстом, как человек в мессенджере
4. Используй обычные запятые и точки
5. Разбивай текст на абзацы для удобства чтения
6. Пиши дружелюбно и по-человечески
7. Избегай шаблонных фраз и канцелярита
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
            temperature=0.8
        )
        
        # Получаем ответ
        answer = response.choices[0].message.content
        
        # Дополнительная очистка от звездочек
        answer = answer.replace('*', '')
        answer = answer.replace('**', '')
        answer = answer.replace('__', '')
        
        return answer
        
    except Exception as e:
        return f"Извините, ошибка: {e}"