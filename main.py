import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from services.ai_service import get_ai_advice

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Хранилище истории для каждого пользователя
user_conversation_history = {}

@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    user_conversation_history[user_id] = []
    await message.answer(
        "Здравствуйте! Я медицинский помощник.\n"
        "Опишите ваши симптомы, и я постараюсь помочь."
    )
    logger.info(f"Пользователь {user_id} начал диалог")

@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    user_message = message.text
    
    logger.info(f"Получено сообщение от {user_id}: {user_message[:100]}...")
    
    # Проверяем, есть ли история для пользователя
    if user_id not in user_conversation_history:
        user_conversation_history[user_id] = []
    
    # Получаем историю
    history = user_conversation_history[user_id]
    
    # Показываем, что бот печатает
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        # Отправляем в AI
        advice = await get_ai_advice(
            user_message=user_message,
            conversation_history=history[-5:]
        )
        
        # Сохраняем в историю
        user_conversation_history[user_id].append({"role": "user", "content": user_message})
        user_conversation_history[user_id].append({"role": "assistant", "content": advice})
        
        # Отправляем ответ (разбиваем если слишком длинный)
        if len(advice) > 4096:
            for i in range(0, len(advice), 4000):
                await message.answer(advice[i:i+4000])
        else:
            await message.answer(advice)
            
        logger.info(f"Ответ отправлен пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения от {user_id}: {e}", exc_info=True)
        await message.answer("Извините, произошла ошибка. Попробуйте позже.")

async def main():
    logger.info("🚀 Бот запускается...")
    print("Бот запущен!")
    print(f"Токен бота: {BOT_TOKEN[:15]}...")
    
    try:
        # Проверяем подключение к Telegram API
        me = await bot.get_me()
        print(f"✅ Бот @{me.username} успешно подключен!")
        logger.info(f"Бот @{me.username} запущен")
    except Exception as e:
        print(f"❌ Ошибка подключения к Telegram: {e}")
        logger.error(f"Ошибка подключения к Telegram: {e}")
        return
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
        print("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        print(f"Критическая ошибка: {e}")
