from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database.db import (
    get_or_create_user, set_subscription, save_payment, get_subscription,
    add_admin_log
)
from keyboards import payment_methods_keyboard, thanks_keyboard, main_menu
from config import SUBSCRIPTION_DAYS, YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY
from payments.yookassa import YooKassaClient

router = Router()

# Цены для донатов
DONATION_PRICES = {
    100: {"stars": 100, "rub": 100, "days": 0, "name": "100 Stars"},
    250: {"stars": 250, "rub": 250, "days": SUBSCRIPTION_DAYS, "name": "250 Stars"},
    500: {"stars": 500, "rub": 500, "days": 60, "name": "500 Stars"},
}

# Инициализируем ЮKassa клиент
yookassa = None
if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
    yookassa = YooKassaClient(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)

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
        f"⭐ 100 Stars / 100 руб. — простая благодарность\n"
        f"⭐ 250 Stars / 250 руб. — активная поддержка на {SUBSCRIPTION_DAYS} дней\n"
        f"⭐ 500 Stars / 500 руб. — щедрая поддержка на 60 дней\n\n"
        f"*Способы оплаты:*\n"
        f"• Telegram Stars — для всех стран, без комиссии\n"
        f"• Банковская карта — через ЮKassa (Россия)\n\n"
        f"{status_text}",
        reply_markup=payment_methods_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "subscription_info")
async def subscription_info(callback: CallbackQuery):
    """Информация о поддержке"""
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
        f"*Как оплатить:*\n"
        f"1. Выберите сумму и способ оплаты\n"
        f"2. Оплатите через Telegram Stars или банковскую карту\n"
        f"3. Поддержка активируется автоматически\n\n"
        f"Спасибо, что поддерживаете проект! 🙏",
        reply_markup=payment_methods_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("pay_stars_"))
async def handle_stars_payment(callback: CallbackQuery, bot: Bot):
    """Обработка оплаты Telegram Stars"""
    amount = int(callback.data.split("_")[2])
    
    if amount not in DONATION_PRICES:
        await callback.answer("Неверная сумма", show_alert=True)
        return
    
    donation = DONATION_PRICES[amount]
    
    # Создаем инвойс для оплаты Stars
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=f"Поддержка медицинского бота — {donation['name']}",
        description=f"Сумма поддержки: {amount} Stars.\n\nВаша поддержка помогает развивать проект!",
        payload=f"stars_{amount}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=donation['name'], amount=amount)],
        start_parameter=f"stars_{amount}",
        need_name=False,
        need_email=False,
        need_phone_number=False,
        need_shipping_address=False
    )
    
    await callback.answer()

@router.callback_query(F.data.startswith("pay_card_"))
async def handle_card_payment(callback: CallbackQuery, bot: Bot):
    """Обработка оплаты банковской картой через ЮKassa"""
    if not yookassa:
        await callback.answer("ЮKassa не настроена. Используйте Telegram Stars.", show_alert=True)
        return
    
    amount = int(callback.data.split("_")[2])
    
    if amount not in DONATION_PRICES:
        await callback.answer("Неверная сумма", show_alert=True)
        return
    
    donation = DONATION_PRICES[amount]
    
    await callback.message.edit_text(
        "🔄 *Создаем платеж...*\n\n"
        "Пожалуйста, подождите несколько секунд.",
        parse_mode="Markdown"
    )
    
    try:
        # Создаем платеж в ЮKassa
        payment = await yookassa.create_payment(
            amount=amount,
            description=f"Поддержка медицинского бота — {donation['name']}",
            user_id=callback.from_user.id,
            return_url=f"https://t.me/{bot.username}?start=payment_success",
            metadata={"amount": amount, "type": "donation"}
        )
        
        if "confirmation" in payment and "confirmation_url" in payment["confirmation"]:
            payment_url = payment["confirmation"]["confirmation_url"]
            payment_id = payment["id"]
            
            # Сохраняем информацию о платеже как pending
            save_payment(
                user_id=callback.from_user.id,
                amount=amount,
                currency="RUB",
                payment_method="yookassa_pending",
                payment_id=payment_id
            )
            
            await callback.message.edit_text(
                f"💳 *Оплата через банковскую карту*\n\n"
                f"Сумма: {amount} руб.\n\n"
                f"[Оплатить]({payment_url})\n\n"
                f"После оплаты нажмите /check_payment_{payment_id} для проверки статуса.\n\n"
                f"*Важно:* платеж может обрабатываться до нескольких минут.",
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        else:
            await callback.message.edit_text(
                "❌ *Ошибка при создании платежа*\n\n"
                "Попробуйте позже или используйте Telegram Stars.",
                parse_mode="Markdown",
                reply_markup=payment_methods_keyboard()
            )
    
    except Exception as e:
        await callback.message.edit_text(
            f"❌ *Ошибка:* {str(e)}\n\nПопробуйте позже или используйте Telegram Stars.",
            parse_mode="Markdown",
            reply_markup=payment_methods_keyboard()
        )
    
    await callback.answer()

@router.message(F.text.startswith("/check_payment_"))
async def check_payment(message: Message):
    """Проверка статуса платежа ЮKassa"""
    if not yookassa:
        await message.answer("ЮKassa не настроена.")
        return
    
    payment_id = message.text.split("_")[2]
    
    await message.answer("🔄 *Проверяем статус платежа...*", parse_mode="Markdown")
    
    try:
        payment = await yookassa.get_payment(payment_id)
        
        if payment["status"] == "succeeded":
            amount = int(payment["amount"]["value"])
            
            # Сохраняем платеж как успешный
            save_payment(
                user_id=message.from_user.id,
                amount=amount,
                currency="RUB",
                payment_method="yookassa",
                payment_id=payment_id
            )
            
            # Определяем бонусные дни
            if amount == 250:
                bonus_days = SUBSCRIPTION_DAYS
            elif amount == 500:
                bonus_days = 60
            else:
                bonus_days = 0
            
            if bonus_days > 0:
                new_end = set_subscription(
                    user_id=message.from_user.id,
                    days=bonus_days,
                    amount=amount,
                    payment_id=payment_id
                )
                
                await message.answer(
                    f"✅ *Платеж подтвержден!*\n\n"
                    f"Сумма: {amount} руб.\n"
                    f"Активная поддержка до: {new_end.strftime('%d.%m.%Y')}\n\n"
                    f"Спасибо за поддержку! 🩺",
                    parse_mode="Markdown",
                    reply_markup=thanks_keyboard()
                )
            else:
                await message.answer(
                    f"✅ *Спасибо за поддержку!*\n\n"
                    f"Сумма: {amount} руб.\n\n"
                    f"Ваша поддержка очень важна для развития проекта! 🙏",
                    parse_mode="Markdown",
                    reply_markup=thanks_keyboard()
                )
        elif payment["status"] == "pending":
            await message.answer(
                "⏳ *Платеж еще не подтвержден*\n\n"
                "Попробуйте проверить статус через несколько минут.",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                f"❌ *Статус платежа:* {payment['status']}\n\n"
                "Если деньги были списаны, обратитесь в поддержку.",
                parse_mode="Markdown"
            )
    
    except Exception as e:
        await message.answer(f"❌ *Ошибка:* {str(e)}", parse_mode="Markdown")

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    """Подтверждение платежа Stars"""
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: Message, bot: Bot):
    """Обработка успешного платежа Stars"""
    payment = message.successful_payment
    user_id = message.from_user.id
    amount = payment.total_amount
    payload = payment.invoice_payload
    
    # Сохраняем платеж
    save_payment(
        user_id=user_id,
        amount=amount,
        currency=payment.currency,
        payment_method="telegram_stars",
        payment_id=payment.telegram_payment_charge_id
    )
    
    # Определяем бонусные дни
    if amount == 250:
        bonus_days = SUBSCRIPTION_DAYS
    elif amount == 500:
        bonus_days = 60
    else:
        bonus_days = 0
    
    if bonus_days > 0:
        new_end = set_subscription(
            user_id=user_id,
            days=bonus_days,
            amount=amount,
            payment_id=payment.telegram_payment_charge_id
        )
        
        await message.answer(
            f"✅ *Спасибо за поддержку!*\n\n"
            f"Сумма: {amount} Stars\n"
            f"Активная поддержка до: {new_end.strftime('%d.%m.%Y')}\n\n"
            f"Можете продолжать задавать вопросы врачу! 🩺",
            parse_mode="Markdown",
            reply_markup=thanks_keyboard()
        )
    else:
        await message.answer(
            f"✅ *Спасибо за поддержку!*\n\n"
            f"Сумма: {amount} Stars\n\n"
            f"Ваша поддержка очень важна для развития проекта! 🙏",
            parse_mode="Markdown",
            reply_markup=thanks_keyboard()
        )
    
    print(f"💰 Донат: {message.from_user.first_name} (@{message.from_user.username}) — {amount} Stars")