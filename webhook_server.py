from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from aiogram import Bot
import hashlib
import hmac
import json
from typing import Dict

from config import (
    YOOKASSA_SECRET_KEY, YOOKASSA_WEBHOOK_SECRET,
    BOT_TOKEN, WEBHOOK_HOST, WEBHOOK_PATH
)
from database.db import (
    get_pending_payment, update_payment_status, set_subscription,
    save_payment, add_admin_log
)

app = FastAPI()
bot = Bot(token=BOT_TOKEN)

def verify_yookassa_signature(request_body: bytes, signature: str) -> bool:
    """Проверяет подпись запроса от ЮKassa"""
    if not YOOKASSA_WEBHOOK_SECRET:
        return True  # Если секрет не задан, пропускаем проверку
    
    expected_signature = hmac.new(
        YOOKASSA_WEBHOOK_SECRET.encode(),
        request_body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)

@app.post(WEBHOOK_PATH)
async def yookassa_webhook(request: Request, background_tasks: BackgroundTasks):
    """Эндпоинт для приема вебхуков от ЮKassa"""
    
    # Получаем тело запроса
    body = await request.body()
    
    # Проверяем подпись (если есть)
    signature = request.headers.get('X-Yoo-Signature')
    if signature and not verify_yookassa_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    # Парсим данные
    try:
        data = json.loads(body)
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Обрабатываем событие
    event = data.get('event')
    payment_obj = data.get('object', {})
    payment_id = payment_obj.get('id')
    
    if event == 'payment.succeeded':
        # Платеж успешен
        background_tasks.add_task(handle_successful_payment, payment_obj)
        return {"status": "ok"}
    
    elif event == 'payment.canceled':
        # Платеж отменен
        background_tasks.add_task(handle_canceled_payment, payment_id)
        return {"status": "ok"}
    
    elif event == 'payment.waiting_for_capture':
        # Ожидает подтверждения (для двухстадийных платежей)
        background_tasks.add_task(handle_waiting_payment, payment_obj)
        return {"status": "ok"}
    
    return {"status": "ok"}

async def handle_successful_payment(payment_obj: Dict):
    """Обрабатывает успешный платеж"""
    payment_id = payment_obj.get('id')
    amount = int(float(payment_obj.get('amount', {}).get('value', 0)))
    currency = payment_obj.get('amount', {}).get('currency', 'RUB')
    metadata = payment_obj.get('metadata', {})
    user_id = int(metadata.get('user_id', 0))
    
    if not user_id:
        # Пробуем найти по pending платежу
        pending = get_pending_payment(payment_id)
        if pending:
            user_id = pending['user_id']
            amount = pending['amount']
    
    if not user_id:
        print(f"⚠️ Не удалось определить user_id для платежа {payment_id}")
        return
    
    # Обновляем статус платежа
    update_payment_status(payment_id, 'completed')
    
    # Определяем бонусные дни
    if amount == 250:
        bonus_days = 30
    elif amount == 500:
        bonus_days = 60
    else:
        bonus_days = 0
    
    # Если есть бонусные дни, активируем подписку
    if bonus_days > 0:
        new_end = set_subscription(
            user_id=user_id,
            days=bonus_days,
            amount=amount,
            payment_id=payment_id
        )
        
        # Отправляем сообщение пользователю
        try:
            await bot.send_message(
                user_id,
                f"✅ *Платеж подтвержден!*\n\n"
                f"Сумма: {amount} руб.\n"
                f"Активная поддержка до: {new_end.strftime('%d.%m.%Y')}\n\n"
                f"Спасибо за поддержку! 🩺",
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"⚠️ Не удалось отправить сообщение пользователю {user_id}: {e}")
    
    else:
        # Отправляем сообщение пользователю без подписки
        try:
            await bot.send_message(
                user_id,
                f"✅ *Спасибо за поддержку!*\n\n"
                f"Сумма: {amount} руб.\n\n"
                f"Ваша поддержка очень важна для развития проекта! 🙏",
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"⚠️ Не удалось отправить сообщение пользователю {user_id}: {e}")
    
    # Логируем
    print(f"💰 Донат через ЮKassa: user {user_id} — {amount} RUB")
    
    # Сохраняем в админ-лог
    add_admin_log(
        admin_id=0,  # Системное действие
        action='yookassa_payment',
        target_user_id=user_id,
        details=f'Payment {payment_id}: {amount} RUB'
    )

async def handle_canceled_payment(payment_id: str):
    """Обрабатывает отмененный платеж"""
    update_payment_status(payment_id, 'canceled')
    print(f"❌ Платеж {payment_id} отменен")

async def handle_waiting_payment(payment_obj: Dict):
    """Обрабатывает ожидающий платеж (для двухстадийных)"""
    payment_id = payment_obj.get('id')
    # Можно отправить напоминание или просто залогировать
    print(f"⏳ Платеж {payment_id} ожидает подтверждения")

@app.get("/webhook/health")
async def health_check():
    """Проверка работоспособности вебхук-сервера"""
    return {"status": "ok", "webhook_path": WEBHOOK_PATH}

def run_webhook_server():
    """Запускает вебхук-сервер"""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)