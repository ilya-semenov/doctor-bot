import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from services.ai_service import get_ai_advice
from database.db import init_db, get_or_create_user, update_last_active, get_subscription
from keyboards import main_menu
from handlers import subscription as subscription_router

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Подключаем роутер подписки
dp.include_router(subscription_router.router)

# Хранилище истории для каждого пользователя
user_conversation_history = {}

# Фоновая задача для проверки подписок (простая версия)
async def check_subscriptions_background():
    """Периодическая проверка подписок (каждый день)"""
    while True:
        try:
            from database.db import get_expiring_subscriptions, mark_notified, get_expired_subscriptions, set_status_expired
            
            # Проверяем истекающие через 3 дня
            expiring = get_expiring_subscriptions(3)
            for user_id, end_date in expiring:
                days_left = (end_date - asyncio.get_event_loop().time()).days
                await bot.send_message(
                    user_id,
                    f"⚠️ *Ваша поддержка истекает через {days_left} дня!*\n\n"
                    f"Если бот был полезен, вы можете продлить поддержку командой /support.\n"
                    f"Спасибо, что пользуетесь ботом! 🩺",
                    parse_mode="Markdown"
                )
                mark_notified(user_id)
            
            # Проверяем истекшие
            expired = get_expired_subscriptions()
            for user_id in expired:
                set_status_expired(user_id)
                await bot.send_message(
                    user_id,
                    f"⏰ *Ваша поддержка истекла*\n\n"
                    f"Но бот продолжает работать бесплатно! "
                    f"Если хотите снова поддержать проект, используйте команду /support.",
                    parse_mode="Markdown"
                )
        
        except Exception as e:
            print(f"Ошибка в check_subscriptions_background: {e}")
        
        await asyncio.sleep(86400)  # Раз в день

@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    user_conversation_history[user_id] = []
    
    # Сохраняем пользователя в БД
    get_or_create_user(
        user_id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )
    
    # Проверяем статус подписки (для информации)
    sub = get_subscription(user_id)
    subscription_status = ""
    if sub['active']:
        subscription_status = f"\n\n✨ *Активная поддержка:* до {sub['end_date'].strftime('%d.%m.%Y')}"
    
    await message.answer(
        f"🩺 *Медицинский помощник*\n\n"
        f"Здравствуйте! Я бот-помощник на основе искусственного интеллекта. "
        f"Опишите ваши симптомы, и я постараюсь помочь.\n\n"
        f"⚠️ *Важно:* Я не заменяю врача. При серьезных симптомах обязательно обратитесь к специалисту.\n"
        f"{subscription_status}",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
@dp.message(lambda message: message.text == "ℹ️ О боте")
async def help_command(message: Message):
    await message.answer(
        "🩺 *О медицинском помощнике*\n\n"
        "Я использую искусственный интеллект для анализа симптомов и даю рекомендации.\n\n"
        "*Как пользоваться:*\n"
        "• Опишите свои симптомы простым языком\n"
        "• Я задам уточняющие вопросы\n"
        "• Дам рекомендации по возможным действиям\n\n"
        "*Важно помнить:*\n"
        "• Я не ставлю диагнозы\n"
        "• Не заменяю очного врача\n"
        "• При серьезных симптомах вызывайте скорую\n\n"
        "*Поддержка проекта:*\n"
        "Бот бесплатный, но вы можете поддержать его развитие командой /support",
        parse_mode="Markdown"
    )

@dp.message(lambda message: message.text == "🩺 Задать вопрос врачу")
async def ask_doctor(message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_conversation_history:
        user_conversation_history[user_id] = []
    
    await message.answer(
        "🩺 Опишите ваши симптомы.\n\n"
        "Например: 'У меня болит голова и температура 37.5 уже второй день'",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    user_message = message.text
    
    # Обновляем активность
    update_last_active(user_id)
    
    # Проверяем, есть ли история для пользователя
    if user_id not in user_conversation_history:
        user_conversation_history[user_id] = []
    
    # Получаем историю
    history = user_conversation_history[user_id]
    
    # Показываем, что бот печатает
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Отправляем в AI
    advice = await get_ai_advice(
        user_message=user_message,
        conversation_history=history[-5:] if history else None
    )
    
    # Сохраняем в историю
    user_conversation_history[user_id].append({"role": "user", "content": user_message})
    user_conversation_history[user_id].append({"role": "assistant", "content": advice})
    
    # Ограничиваем историю до 10 сообщений (чтобы не переполнять память)
    if len(user_conversation_history[user_id]) > 20:
        user_conversation_history[user_id] = user_conversation_history[user_id][-20:]
    
    # Добавляем клавиатуру после ответа
    await message.answer(advice, reply_markup=main_menu())

async def main():
    # Инициализируем базу данных
    init_db()
    print("База данных инициализирована")
    
    # Запускаем фоновую задачу проверки подписок
    asyncio.create_task(check_subscriptions_background())
    print("Фоновая задача запущена")
    
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
