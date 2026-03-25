import sys
import io
import openai
from config import AI_API_KEY, AI_MODEL

# Принудительно устанавливаем UTF-8 для вывода
if sys.stdout.encoding != 'UTF-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

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

def safe_encode_text(text):
    """Безопасное кодирование текста в UTF-8"""
    if text is None:
        return ""
    if isinstance(text, bytes):
        text = text.decode('utf-8', errors='replace')
    # Принудительно конвертируем в UTF-8 и обратно, заменяя проблемные символы
    return text.encode('utf-8', errors='replace').decode('utf-8')

async def get_ai_advice(user_message: str, conversation_history: list = None) -> str:
    """
    Функция принимает:
    - user_message: сообщение пользователя
    - conversation_history: история диалога (опционально)
    """
    
    # Безопасное кодирование входного сообщения
    user_message = safe_encode_text(user_message)
    
    messages = [{"role": "system", "content": DOCTOR_SYSTEM_PROMPT}]
    
    # Добавляем историю, если она есть
    if conversation_history:
        for msg in conversation_history:
            # Безопасное кодирование каждого сообщения в истории
            if isinstance(msg, dict):
                safe_msg = {
                    "role": msg.get("role", "user"),
                    "content": safe_encode_text(msg.get("content", ""))
                }
                messages.append(safe_msg)
    
    # Добавляем текущее сообщение
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            temperature=0.8,
            top_p=0.9
        )
        
        # Получаем ответ
        answer = response.choices[0].message.content
        
        # Безопасное кодирование ответа
        answer = safe_encode_text(answer)
        
        # Дополнительная очистка от звездочек (на всякий случай)
        answer = answer.replace('*', '')
        answer = answer.replace('**', '')
        answer = answer.replace('__', '')
        
        return answer
        
    except UnicodeEncodeError as e:
        # Специфичная обработка ошибки кодировки
        print(f"Unicode encode error: {e}")
        return "Извините, произошла ошибка кодировки. Пожалуйста, попробуйте задать вопрос иначе."
    
    except Exception as e:
        print(f"Error in get_ai_advice: {e}")
        return f"Извините, ошибка: {str(e)}"
