import openai
from config import AI_API_KEY, AI_MODEL

client = openai.OpenAI(
    api_key=AI_API_KEY,
    base_url="https://api.deepseek.com/v1"
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

Пример правильного ответа:
"Здравствуйте! Судя по вашим симптомам, это похоже на обычную простуду. Температура 37.5 и насморк - типичные признаки ОРВИ.

Попробуйте пить больше теплой жидкости, отдыхать и принимать витамин С. Если температура поднимется выше 38.5, можно выпить жаропонижающее.

Обязательно покажитесь терапевту, если симптомы не пройдут через 3-4 дня. Выздоравливайте!"
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
            temperature=0.8,  # Чуть выше для более естественной речи
            top_p=0.9  # Добавляем для разнообразия речи
        )
        
        # Получаем ответ
        answer = response.choices[0].message.content
        
        # Дополнительная очистка от звездочек (на всякий случай)
        answer = answer.replace('*', '')
        answer = answer.replace('**', '')
        answer = answer.replace('__', '')
        
        return answer
        
    except Exception as e:
        return f"Извините, ошибка: {e}"