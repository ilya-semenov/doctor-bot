from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Главное меню
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

# Инлайн-клавиатура для выбора способа оплаты
def payment_methods_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="pay_stars_250")],
        [InlineKeyboardButton(text="💳 Банковская карта (ЮKassa)", callback_data="pay_card_250")],
        [InlineKeyboardButton(text="📖 Что я получу?", callback_data="subscription_info")]
    ])
    return keyboard

# Клавиатура для админ-панели
def admin_panel_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика донатов", callback_data="admin_stats")],
        [InlineKeyboardButton(text="💰 Последние платежи", callback_data="admin_payments")],
        [InlineKeyboardButton(text="🏆 Топ донатеров", callback_data="admin_top")],
        [InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_users")],
        [InlineKeyboardButton(text="🔍 Поиск пользователя", callback_data="admin_search")],
        [InlineKeyboardButton(text="📤 Экспорт в Excel", callback_data="admin_export")]
    ])
    return keyboard

# Клавиатура для пагинации платежей
def payments_pagination_keyboard(page: int, total_pages: int):
    buttons = []
    
    if page > 1:
        buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_payments_page_{page-1}"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"admin_payments_page_{page+1}"))
    
    buttons.append(InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin_back"))
    
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

def admin_users_pagination_keyboard(page: int, total_pages: int):
    buttons = []
    
    if page > 1:
        buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_users_page_{page-1}"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"admin_users_page_{page+1}"))
    
    buttons.append(InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin_back"))
    
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

def user_actions_keyboard(user_id: int):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 История платежей", callback_data=f"admin_user_payments_{user_id}")],
        [InlineKeyboardButton(text="✨ Продлить подписку (30 дней)", callback_data=f"admin_extend_{user_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    return keyboard

def back_to_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin_back")]
    ])

# Клавиатура для благодарности после оплаты
def thanks_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🩺 Задать вопрос врачу")],
            [KeyboardButton(text="💎 Поддержать проект")],
            [KeyboardButton(text="ℹ️ О боте")]
        ],
        resize_keyboard=True
    )
    return keyboard
