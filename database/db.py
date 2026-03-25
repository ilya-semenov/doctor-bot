import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'bot_database.db')

def init_db():
    """Создает таблицы если их нет"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            subscription_end TIMESTAMP,
            subscription_status TEXT DEFAULT 'inactive',
            notified_3days INTEGER DEFAULT 0,
            total_donations INTEGER DEFAULT 0
        )
    ''')
    
    # Таблица платежей (расширенная)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            currency TEXT,
            payment_method TEXT,
            payment_id TEXT,
            status TEXT DEFAULT 'completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Таблица для админ-логов (опционально)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            target_user_id INTEGER,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# ... (предыдущие функции get_or_create_user, update_last_active и т.д. остаются)

def get_all_payments(limit: int = 100, offset: int = 0) -> List[Dict]:
    """Получить все платежи с информацией о пользователях"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            p.id,
            p.user_id,
            u.username,
            u.first_name,
            u.last_name,
            p.amount,
            p.currency,
            p.payment_method,
            p.payment_id,
            p.created_at
        FROM payments p
        LEFT JOIN users u ON p.user_id = u.user_id
        ORDER BY p.created_at DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'id': row[0],
            'user_id': row[1],
            'username': row[2],
            'first_name': row[3],
            'last_name': row[4],
            'amount': row[5],
            'currency': row[6],
            'payment_method': row[7],
            'payment_id': row[8],
            'created_at': row[9]
        }
        for row in rows
    ]

def get_payments_stats(days: int = 30) -> Dict:
    """Получить статистику по платежам за N дней"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    since = (datetime.now() - timedelta(days=days)).isoformat()
    
    # Общая статистика
    cursor.execute('''
        SELECT 
            COUNT(*) as total_count,
            SUM(amount) as total_amount,
            COUNT(DISTINCT user_id) as unique_users
        FROM payments
        WHERE created_at >= ?
    ''', (since,))
    
    total_stats = cursor.fetchone()
    
    # Статистика по способам оплаты
    cursor.execute('''
        SELECT 
            payment_method,
            COUNT(*) as count,
            SUM(amount) as total
        FROM payments
        WHERE created_at >= ?
        GROUP BY payment_method
    ''', (since,))
    
    method_stats = cursor.fetchall()
    
    # Статистика по дням
    cursor.execute('''
        SELECT 
            DATE(created_at) as day,
            COUNT(*) as count,
            SUM(amount) as total
        FROM payments
        WHERE created_at >= ?
        GROUP BY DATE(created_at)
        ORDER BY day DESC
        LIMIT 14
    ''', (since,))
    
    daily_stats = cursor.fetchall()
    
    conn.close()
    
    return {
        'total_count': total_stats[0] or 0,
        'total_amount': total_stats[1] or 0,
        'unique_users': total_stats[2] or 0,
        'by_method': [{'method': row[0], 'count': row[1], 'total': row[2]} for row in method_stats],
        'by_day': [{'day': row[0], 'count': row[1], 'total': row[2]} for row in daily_stats]
    }

def get_top_donors(limit: int = 10) -> List[Dict]:
    """Получить топ донатеров"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            u.user_id,
            u.username,
            u.first_name,
            u.last_name,
            u.total_donations,
            COUNT(p.id) as donations_count,
            MAX(p.created_at) as last_donation
        FROM users u
        LEFT JOIN payments p ON u.user_id = p.user_id
        WHERE u.total_donations > 0
        GROUP BY u.user_id
        ORDER BY u.total_donations DESC
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'user_id': row[0],
            'username': row[1],
            'first_name': row[2],
            'last_name': row[3],
            'total_donations': row[4],
            'donations_count': row[5],
            'last_donation': row[6]
        }
        for row in rows
    ]

def get_user_payments(user_id: int, limit: int = 20) -> List[Dict]:
    """Получить платежи конкретного пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            amount,
            currency,
            payment_method,
            created_at
        FROM payments
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'amount': row[0],
            'currency': row[1],
            'payment_method': row[2],
            'created_at': row[3]
        }
        for row in rows
    ]

def add_admin_log(admin_id: int, action: str, target_user_id: int = None, details: str = None):
    """Добавить запись в лог администратора"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO admin_logs (admin_id, action, target_user_id, details)
        VALUES (?, ?, ?, ?)
    ''', (admin_id, action, target_user_id, details))
    conn.commit()
    conn.close()

def get_all_users(limit: int = 50, offset: int = 0) -> List[Dict]:
    """Получить список всех пользователей"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            user_id,
            username,
            first_name,
            last_name,
            first_seen,
            last_active,
            subscription_end,
            subscription_status,
            total_donations
        FROM users
        ORDER BY last_active DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'user_id': row[0],
            'username': row[1],
            'first_name': row[2],
            'last_name': row[3],
            'first_seen': row[4],
            'last_active': row[5],
            'subscription_end': row[6],
            'subscription_status': row[7],
            'total_donations': row[8]
        }
        for row in rows
    ]

def get_user_by_username_or_id(search: str) -> Optional[Dict]:
    """Найти пользователя по username или ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Пробуем найти по ID
    if search.isdigit():
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (int(search),))
    else:
        # Убираем @ если есть
        username = search.lstrip('@')
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            'user_id': row[0],
            'username': row[1],
            'first_name': row[2],
            'last_name': row[3],
            'first_seen': row[4],
            'last_active': row[5],
            'subscription_end': row[6],
            'subscription_status': row[7],
            'total_donations': row[8]
        }
    return None

def manual_set_subscription(user_id: int, days: int, admin_id: int = None) -> datetime:
    """Ручное продление подписки администратором"""
    new_end = set_subscription(user_id, days)
    
    if admin_id:
        add_admin_log(
            admin_id=admin_id,
            action='manual_subscription',
            target_user_id=user_id,
            details=f'Added {days} days'
        )
    
    return new_end