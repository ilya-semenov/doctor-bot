from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Главное меню (обычное)
def main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🩺 Задать вопрос врачу")],
            [KeyboardButton(text="💎 Поддержать проект")],
            [KeyboardButton(text="ℹ️ О боте")]
        ],
        resize_keyboard=True
    )
    return keyboard

# Инлайн-клавиатура для подписки
def subscription_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Поддержать (100 Stars)", callback_data="subscribe_100")],
        [InlineKeyboardButton(text="⭐ Поддержать (250 Stars)", callback_data="subscribe_250")],
        [InlineKeyboardButton(text="⭐ Поддержать (500 Stars)", callback_data="subscribe_500")],
        [InlineKeyboardButton(text="📖 Что я получу?", callback_data="subscription_info")]
    ])
    return keyboard

# Кнопка после подписки
def thanks_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🩺 Задать вопрос", callback_data="ask_question")],
        [InlineKeyboardButton(text="💎 Поддержать еще", callback_data="subscribe")]
    ])
    return keyboard

# Кнопка для тех, у кого нет подписки (но бот и так бесплатный, это для донатов)
def donate_reminder():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Поддержать проект", callback_data="subscribe")]
    ])
    return keyboard
