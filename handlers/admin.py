from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database.db import (
    get_all_payments, get_payments_stats, get_top_donors,
    get_all_users, get_user_payments, get_user_by_username_or_id,
    manual_set_subscription, add_admin_log
)
from keyboards import (
    admin_panel_keyboard, payments_pagination_keyboard,
    admin_users_pagination_keyboard, user_actions_keyboard,
    back_to_admin_keyboard
)
from config import ADMIN_IDS
import io
import csv
from datetime import datetime

router = Router()

# Состояния для поиска пользователя
class AdminSearchState(StatesGroup):
    waiting_for_search = State()

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Админ-панель"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return
    
    await message.answer(
        "👑 *Админ-панель*\n\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=admin_panel_keyboard()
    )

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Возврат в админ-панель"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    await callback.message.edit_text(
        "👑 *Админ-панель*\n\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=admin_panel_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Статистика донатов"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    stats = get_payments_stats(30)
    
    # Формируем сообщение
    text = f"📊 *Статистика донатов (за 30 дней)*\n\n"
    text += f"💰 Всего платежей: {stats['total_count']}\n"
    text += f"💎 Общая сумма: {stats['total_amount']} Stars/RUB\n"
    text += f"👥 Уникальных донатеров: {stats['unique_users']}\n\n"
    
    text += "*По способам оплаты:*\n"
    for method in stats['by_method']:
        method_name = "Telegram Stars" if method['method'] == 'telegram_stars' else "ЮKassa"
        text += f"• {method_name}: {method['count']} платежей, {method['total']} ед.\n"
    
    if stats['by_day']:
        text += "\n*Последние 7 дней:*\n"
        for day in stats['by_day'][:7]:
            text += f"• {day['day']}: {day['count']} платежей, {day['total']} ед.\n"
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_admin_keyboard())
    await callback.answer()

@router.callback_query(F.data == "admin_payments")
async def admin_payments(callback: CallbackQuery):
    """Последние платежи"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    await show_payments_page(callback.message, 1)

async def show_payments_page(message, page: int, edit: bool = True):
    """Показать страницу с платежами"""
    payments_per_page = 10
    offset = (page - 1) * payments_per_page
    
    payments = get_all_payments(limit=payments_per_page, offset=offset)
    total_payments = len(get_all_payments(limit=10000))  # Упрощенно
    total_pages = (total_payments // payments_per_page) + 1
    
    if not payments:
        text = "📜 *Платежи не найдены*"
    else:
        text = f"📜 *Последние платежи (страница {page}/{total_pages})*\n\n"
        for p in payments[:10]:
            method = "⭐ Stars" if p['payment_method'] == 'telegram_stars' else "💳 Карта"
            name = p['first_name'] or p['username'] or str(p['user_id'])
            text += f"• {p['created_at'][:10]} | {name}: {p['amount']} {p['currency']} ({method})\n"
    
    if edit:
        await message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=payments_pagination_keyboard(page, total_pages)
        )
    else:
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=payments_pagination_keyboard(page, total_pages)
        )

@router.callback_query(F.data.startswith("admin_payments_page_"))
async def admin_payments_page(callback: CallbackQuery):
    """Пагинация платежей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    page = int(callback.data.split("_")[3])
    await show_payments_page(callback.message, page)
    await callback.answer()

@router.callback_query(F.data == "admin_top")
async def admin_top(callback: CallbackQuery):
    """Топ донатеров"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    top = get_top_donors(10)
    
    text = "🏆 *Топ донатеров*\n\n"
    for i, donor in enumerate(top, 1):
        name = donor['first_name'] or donor['username'] or str(donor['user_id'])
        text += f"{i}. {name} — {donor['total_donations']} ед. ({donor['donations_count']} платежей)\n"
        if donor.get('last_donation'):
            text += f"   Последний: {donor['last_donation'][:10]}\n"
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_admin_keyboard())
    await callback.answer()

@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    """Список пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    await show_users_page(callback.message, 1)

async def show_users_page(message, page: int, edit: bool = True):
    """Показать страницу с пользователями"""
    users_per_page = 15
    offset = (page - 1) * users_per_page
    
    users = get_all_users(limit=users_per_page, offset=offset)
    total_users = len(get_all_users(limit=10000))  # Упрощенно
    total_pages = (total_users // users_per_page) + 1
    
    if not users:
        text = "👥 *Пользователи не найдены*"
    else:
        text = f"👥 *Пользователи (страница {page}/{total_pages})*\n\n"
        for u in users:
            name = u['first_name'] or u['username'] or str(u['user_id'])
            status = "✨ активен" if u['subscription_status'] == 'active' else "⚪ обычный"
            text += f"• {name}: {status} | донатов: {u['total_donations']}\n"
    
    if edit:
        await message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=admin_users_pagination_keyboard(page, total_pages)
        )
    else:
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=admin_users_pagination_keyboard(page, total_pages)
        )

@router.callback_query(F.data.startswith("admin_users_page_"))
async def admin_users_page(callback: CallbackQuery):
    """Пагинация пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    page = int(callback.data.split("_")[3])
    await show_users_page(callback.message, page)
    await callback.answer()

@router.callback_query(F.data == "admin_search")
async def admin_search(callback: CallbackQuery, state: FSMContext):
    """Поиск пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    await callback.message.edit_text(
        "🔍 *Поиск пользователя*\n\n"
        "Введите ID пользователя или @username:",
        parse_mode="Markdown",
        reply_markup=back_to_admin_keyboard()
    )
    await state.set_state(AdminSearchState.waiting_for_search)
    await callback.answer()

@router.message(AdminSearchState.waiting_for_search)
async def admin_search_result(message: Message, state: FSMContext):
    """Обработка поиска пользователя"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return
    
    search = message.text.strip()
    user = get_user_by_username_or_id(search)
    
    if not user:
        await message.answer(
            f"❌ Пользователь '{search}' не найден.",
            reply_markup=back_to_admin_keyboard()
        )
        await state.clear()
        return
    
    # Формируем информацию о пользователе
    name = user['first_name'] or user['username'] or str(user['user_id'])
    status = "✨ Активна" if user['subscription_status'] == 'active' else "⚪ Неактивна"
    sub_end = user['subscription_end'][:10] if user['subscription_end'] else "Нет"
    
    text = f"👤 *Информация о пользователе*\n\n"
    text += f"ID: `{user['user_id']}`\n"
    text += f"Имя: {name}\n"
    text += f"Username: @{user['username'] or 'Нет'}\n"
    text += f"Впервые: {user['first_seen'][:10] if user['first_seen'] else '?'}\n"
    text += f"Активен: {user['last_active'][:10] if user['last_active'] else '?'}\n"
    text += f"Подписка: {status}\n"
    text += f"До: {sub_end}\n"
    text += f"Всего донатов: {user['total_donations']} ед.\n"
    
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=user_actions_keyboard(user['user_id'])
    )
    await state.clear()

@router.callback_query(F.data.startswith("admin_user_payments_"))
async def admin_user_payments(callback: CallbackQuery):
    """История платежей пользователя"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    user_id = int(callback.data.split("_")[3])
    payments = get_user_payments(user_id, limit=20)
    
    if not payments:
        text = "📜 *Нет платежей от этого пользователя*"
    else:
        text = f"📜 *История платежей пользователя {user_id}*\n\n"
        for p in payments:
            method = "⭐ Stars" if p['payment_method'] == 'telegram_stars' else "💳 Карта"
            text += f"• {p['created_at'][:10]} | {p['amount']} {p['currency']} ({method})\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=user_actions_keyboard(user_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_extend_"))
async def admin_extend_subscription(callback: CallbackQuery):
    """Продление подписки администратором"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    user_id = int(callback.data.split("_")[2])
    
    new_end = manual_set_subscription(
        user_id=user_id,
        days=30,
        admin_id=callback.from_user.id
    )
    
    await callback.message.edit_text(
        f"✅ *Подписка продлена!*\n\n"
        f"Пользователь: {user_id}\n"
        f"Новая дата окончания: {new_end.strftime('%d.%m.%Y')}\n\n"
        f"*Действие записано в лог*",
        parse_mode="Markdown",
        reply_markup=back_to_admin_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "admin_export")
async def admin_export(callback: CallbackQuery):
    """Экспорт платежей в Excel/CSV"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа")
        return
    
    await callback.message.edit_text(
        "📤 *Подготавливаю отчет...*\n\n"
        "Пожалуйста, подождите.",
        parse_mode="Markdown"
    )
    
    payments = get_all_payments(limit=10000)
    
    # Создаем CSV файл
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', 'User ID', 'Username', 'Имя', 'Сумма', 'Валюта', 'Способ', 'Дата'])
    
    for p in payments:
        writer.writerow([
            p['id'],
            p['user_id'],
            p['username'] or '',
            p['first_name'] or '',
            p['amount'],
            p['currency'],
            p['payment_method'],
            p['created_at']
        ])
    
    output.seek(0)
    
    # Отправляем файл
    await callback.message.answer_document(
        document=('payments_export.csv', output.getvalue()),
        caption=f"📊 Отчет по платежам\nДата: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    
    await callback.message.edit_text(
        "✅ *Отчет готов!*\n\nФайл отправлен выше.",
        parse_mode="Markdown",
        reply_markup=back_to_admin_keyboard()
    )
    await callback.answer()