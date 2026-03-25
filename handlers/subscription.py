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
    
    # Исправленный print с обработкой ошибки кодировки
    try:
        print(f"💰 Донат: {message.from_user.first_name} (@{message.from_user.username}) — {amount} Stars")
    except UnicodeEncodeError:
        # Если не удается вывести с эмодзи и русскими символами, выводим без них
        print(f"Donation: {message.from_user.first_name} (@{message.from_user.username}) - {amount} Stars")
