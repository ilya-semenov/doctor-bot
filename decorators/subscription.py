from functools import wraps
from aiogram.types import Message
from database.db import get_subscription
from keyboards import donate_reminder

def premium_feature(func):
    """Декоратор для функций, доступных только подписчикам"""
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        subscription = get_subscription(message.from_user.id)
        
        if subscription['active']:
            return await func(message, *args, **kwargs)
        else:
            await message.answer(
                "🌟 *Эта функция доступна подписчикам*\n\n"
                "Поддержите проект, и получите доступ к расширенным возможностям!",
                reply_markup=donate_reminder(),
                parse_mode="Markdown"
            )
            return None
    return wrapper