import openai
import logging
import asyncio
from config import AI_API_KEY, AI_MODEL

# Настройка логирования
logger = logging.getLogger(__name__)

# Инициализация клиента DeepSeek
client = openai.OpenAI(
    api_key=AI_API_KEY,
    base_url="https://api.deepseek.com/v1",
    timeout=60.0,  # Увеличиваем таймаут
    max_retries=3  # Добавляем повторные попытки
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
        logger.info(f"Отправка запроса в DeepSeek API. Длина сообщения: {len(user_message)}")
        
        # Используем run_in_executor для асинхронного вызова
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=AI_MODEL,
                messages=messages,
                temperature=0.8,
                top_p=0.9,
                max_tokens=1000  # Добавляем ограничение на длину ответа
            )
        )
        
        # Получаем ответ
        answer = response.choices[0].message.content
        
        # Очистка от звездочек
        answer = answer.replace('*', '')
        answer = answer.replace('**', '')
        answer = answer.replace('__', '')
        
        logger.info(f"Получен ответ от DeepSeek, длина: {len(answer)} символов")
        return answer
        
    except openai.APIConnectionError as e:
        logger.error(f"Ошибка подключения к DeepSeek API: {e}")
        return "Извините, проблема с подключением к серверу. Проверьте интернет-соединение и попробуйте позже."
        
    except openai.APITimeoutError as e:
        logger.error(f"Таймаут DeepSeek API: {e}")
        return "Извините, сервер не отвечает. Попробуйте повторить запрос через минуту."
        
    except openai.AuthenticationError as e:
        logger.error(f"Ошибка аутентификации DeepSeek: {e}")
        return "Извините, проблема с API ключом. Пожалуйста, обратитесь к администратору."
        
    except openai.RateLimitError as e:
        logger.error(f"Превышен лимит запросов: {e}")
        return "Извините, слишком много запросов. Подождите немного и попробуйте снова."
        
    except Exception as e:
        logger.error(f"Неожиданная ошибка в get_ai_advice: {e}")
        return f"Извините, ошибка: {str(e)}"
