from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database.db import get_or_create_user, set_subscription, save_payment, get_subscription
from keyboards import subscription_keyboard, thanks_keyboard, main_menu
from config import SUBSCRIPTION_PRICE_STARS, SUBSCRIPTION_DAYS

router = Router()

# Цены для разных сумм доната
DONATION_PRICES = {
    100: LabeledPrice(label="100 Stars - поддержка", amount=100),
    250: LabeledPrice(label="250 Stars - поддержка", amount=250),
    500: LabeledPrice(label="500 Stars - поддержка", amount=500),
}

@router.message(Command("support"))
@router.message(F.text == "💎 Поддержать проект")
async def support_command(message: Message):
    """Команда для поддержки проекта"""
    user = get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )
    
    # Проверяем текущую подписку
    sub = get_subscription(message.from_user.id)
    
    if sub['active']:
        status_text = f"\n\n✅ *Ваша активная поддержка:* до {sub['end_date'].strftime('%d.%m.%Y')}"
    else:
        status_text = "\n\nℹ️ *Сейчас у вас нет активной поддержки*"
    
    await message.answer(
        f"💎 *Поддержать проект*\n\n"
        f"Этот бот работает бесплатно для всех. "
        f"Если он помог вам, вы можете поддержать его развитие.\n\n"
        f"*Суммы поддержки:*\n"
        f"⭐ 100 Stars — простая благодарность\n"
        f"⭐ 250 Stars — активная поддержка на {SUBSCRIPTION_DAYS} дней\n"
        f"⭐ 500 Stars — щедрая поддержка на 60 дней\n\n"
        f"*Как это работает:*\n"
        f"Вы покупаете Stars в Telegram, затем нажимаете кнопку ниже. "
        f"Все Stars идут на развитие бота (оплату API, серверов).\n\n"
        f"{status_text}",
        reply_markup=subscription_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "subscription_info")
async def subscription_info(callback: CallbackQuery):
    """Информация о подписке"""
    await callback.message.edit_text(
        f"📖 *Что дает поддержка?*\n\n"
        f"1. *Доступ к расширенным возможностям*\n"
        f"   — Более детальные ответы от AI\n"
        f"   — Приоритетная обработка запросов\n"
        f"   — Сохранение истории консультаций\n\n"
        f"2. *Поддержка проекта*\n"
        f"   — Оплата API ключей\n"
        f"   — Развитие новых функций\n"
        f"   — Серверное обслуживание\n\n"
        f"3. *Специальный статус*\n"
        f"   — Значок в диалоге\n"
        f"   — Возможность задавать больше вопросов\n\n"
        f"*Как оплатить?*\n"
        f"1. Нажмите на сумму поддержки\n"
        f"2. Оплатите через Telegram Stars\n"
        f"3. Подписка активируется автоматически\n\n"
        f"Спасибо, что поддерживаете проект! 🙏",
        reply_markup=subscription_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("subscribe_"))
async def handle_subscribe(callback: CallbackQuery, bot: Bot):
    """Обработка выбора суммы поддержки"""
    amount = int(callback.data.split("_")[1])
    
    if amount not in DONATION_PRICES:
        await callback.answer("Неверная сумма", show_alert=True)
        return
    
    # Определяем количество дней подписки (бонус)
    if amount == 100:
        days_text = ""
        days_bonus = 0
    elif amount == 250:
        days_text = f"\nВы получите активную поддержку на {SUBSCRIPTION_DAYS} дней в подарок!"
        days_bonus = SUBSCRIPTION_DAYS
    elif amount == 500:
        days_text = f"\nВы получите активную поддержку на 60 дней в подарок!"
        days_bonus = 60
    else:
        days_bonus = 0
        days_text = ""
    
    # Создаем инвойс для оплаты
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="Поддержка медицинского бота",
        description=f"Сумма поддержки: {amount} Stars.{days_text}\n\nВаша поддержка помогает развивать проект и делает бесплатную медицинскую помощь доступнее!",
        payload=f"donation_{amount}",  # идентификатор платежа
        provider_token="",  # для Stars оставляем пустым
        currency="XTR",  # Telegram Stars
        prices=[DONATION_PRICES[amount]],
        start_parameter=f"donation_{amount}",
        need_name=False,
        need_email=False,
        need_phone_number=False,
        need_shipping_address=False
    )
    
    await callback.answer()

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    """Подтверждение платежа"""
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message, bot: Bot):
    """Обработка успешного платежа"""
    payment = message.successful_payment
    user_id = message.from_user.id
    amount = payment.total_amount
    
    # Сохраняем платеж
    save_payment(
        user_id=user_id,
        amount=amount,
        currency=payment.currency,
        payment_id=payment.telegram_payment_charge_id
    )
    
    # Получаем информацию о пользователе
    user = get_or_create_user(
        user_id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )
    
    # Определяем бонусные дни
    if amount == 250:
        bonus_days = SUBSCRIPTION_DAYS
        status_text = f"активна на {bonus_days} дней"
    elif amount == 500:
        bonus_days = 60
        status_text = f"активна на {bonus_days} дней"
    else:
        bonus_days = 0
        status_text = "неактивна (поддержка без бонуса)"
    
    # Если есть бонусные дни, активируем подписку
    if bonus_days > 0:
        new_end = set_subscription(
            user_id=user_id,
            days=bonus_days,
            amount=amount,
            payment_id=payment.telegram_payment_charge_id
        )
        
        subscription_text = f"\n\n✨ *Ваша поддержка активна!*\nДействует до: {new_end.strftime('%d.%m.%Y')}"
    else:
        # Просто сохраняем платеж без подписки
        subscription_text = "\n\n🙏 *Спасибо за поддержку!*"
    
    # Благодарственное сообщение
    await message.answer(
        f"🌟 *Спасибо за поддержку!*\n\n"
        f"Сумма: {amount} Stars\n"
        f"Ваша поддержка очень важна для развития проекта. "
        f"Благодаря таким людям, как вы, бот остается бесплатным для всех!\n"
        f"{subscription_text}\n\n"
        f"Можете продолжать задавать вопросы врачу. Я всегда рядом! 🩺",
        reply_markup=thanks_keyboard(),
        parse_mode="Markdown"
    )
    
    # Логируем в консоль
    print(f"💰 Донат: {message.from_user.first_name} (@{message.from_user.username}) — {amount} Stars")

@router.callback_query(F.data == "ask_question")
async def ask_question(callback: CallbackQuery):
    """Кнопка 'Задать вопрос'"""
    await callback.message.answer(
        "🩺 Опишите ваши симптомы, и я постараюсь помочь.\n\n"
        "Пожалуйста, помните: я не заменяю врача, при серьезных симптомах обязательно обратитесь к специалисту.",
        reply_markup=main_menu()
    )
    await callback.answer()
