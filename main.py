import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from services.ai_service import get_ai_advice

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

@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    user_message = message.text
    
    # Проверяем, есть ли история для пользователя
    if user_id not in user_conversation_history:
        user_conversation_history[user_id] = []
    
    # Получаем историю
    history = user_conversation_history[user_id]
    
    # 👇 ПОКАЗЫВАЕМ, ЧТО БОТ ПЕЧАТАЕТ (как человек)
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Отправляем в AI
    advice = await get_ai_advice(
        user_message=user_message,
        conversation_history=history[-5:]
    )
    
    # Сохраняем в историю
    user_conversation_history[user_id].append({"role": "user", "content": user_message})
    user_conversation_history[user_id].append({"role": "assistant", "content": advice})
    
    await message.answer(advice)

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
