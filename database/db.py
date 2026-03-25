import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'bot_database.db')

def init_db():
    """Создает таблицы если их нет"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица пользователей (если нет)
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
    
    # Таблица платежей (для истории)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            currency TEXT,
            payment_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_or_create_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> Dict:
    """Получает пользователя или создает нового"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, subscription_status)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, 'inactive'))
        conn.commit()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
    
    conn.close()
    
    return {
        'user_id': user[0],
        'username': user[1],
        'first_name': user[2],
        'last_name': user[3],
        'first_seen': user[4],
        'last_active': user[5],
        'subscription_end': user[6],
        'subscription_status': user[7],
        'notified_3days': user[8],
        'total_donations': user[9]
    }

def update_last_active(user_id: int):
    """Обновляет время последней активности"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?',
        (user_id,)
    )
    conn.commit()
    conn.close()

def get_subscription(user_id: int) -> Dict:
    """Получить информацию о подписке пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT subscription_end, subscription_status FROM users WHERE user_id = ?',
        (user_id,)
    )
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        end_date = datetime.fromisoformat(result[0])
        if end_date > datetime.now():
            return {
                'active': True,
                'end_date': end_date,
                'status': 'active',
                'days_left': (end_date - datetime.now()).days
            }
        else:
            # Обновляем статус если истекла
            if result[1] == 'active':
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE users SET subscription_status = ? WHERE user_id = ?',
                    ('expired', user_id)
                )
                conn.commit()
                conn.close()
            return {
                'active': False,
                'end_date': end_date,
                'status': 'expired',
                'days_left': 0
                }
    
    return {'active': False, 'end_date': None, 'status': 'inactive', 'days_left': 0}

def set_subscription(user_id: int, days: int, amount: int = None, payment_id: str = None):
    """Установить/продлить подписку на N дней"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем текущую дату окончания
    cursor.execute('SELECT subscription_end FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result and result[0]:
        current_end = datetime.fromisoformat(result[0])
        if current_end > datetime.now():
            new_end = current_end + timedelta(days=days)
        else:
            new_end = datetime.now() + timedelta(days=days)
    else:
        new_end = datetime.now() + timedelta(days=days)
    
    cursor.execute('''
        UPDATE users 
        SET subscription_end = ?, subscription_status = 'active', notified_3days = 0
        WHERE user_id = ?
    ''', (new_end.isoformat(), user_id))
    
    # Если есть сумма платежа, обновляем total_donations
    if amount:
        cursor.execute(
            'UPDATE users SET total_donations = total_donations + ? WHERE user_id = ?',
            (amount, user_id)
        )
    
    # Сохраняем платеж
    if payment_id and amount:
        cursor.execute('''
            INSERT INTO payments (user_id, amount, currency, payment_id)
            VALUES (?, ?, ?, ?)
        ''', (user_id, amount, 'XTR', payment_id))
    
    conn.commit()
    conn.close()
    return new_end

def save_payment(user_id: int, amount: int, currency: str, payment_id: str):
    """Сохраняет информацию о платеже"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO payments (user_id, amount, currency, payment_id)
        VALUES (?, ?, ?, ?)
    ''', (user_id, amount, currency, payment_id))
    conn.commit()
    conn.close()

def get_expiring_subscriptions(days: int = 3):
    """Получает пользователей с истекающей подпиской"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    three_days_later = (datetime.now() + timedelta(days=days)).isoformat()
    cursor.execute('''
        SELECT user_id, subscription_end 
        FROM users 
        WHERE subscription_end IS NOT NULL 
        AND subscription_end <= ? 
        AND subscription_end > ?
        AND notified_3days = 0
        AND subscription_status = 'active'
    ''', (three_days_later, datetime.now().isoformat()))
    
    result = cursor.fetchall()
    conn.close()
    
    return [(row[0], datetime.fromisoformat(row[1])) for row in result]

def mark_notified(user_id: int):
    """Отмечает, что уведомление отправлено"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE users SET notified_3days = 1 WHERE user_id = ?',
        (user_id,)
    )
    conn.commit()
    conn.close()

def get_expired_subscriptions():
    """Получает только что истекшие подписки"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id 
        FROM users 
        WHERE subscription_end IS NOT NULL 
        AND subscription_end <= ? 
        AND subscription_status = 'active'
    ''', (datetime.now().isoformat(),))
    
    result = cursor.fetchall()
    conn.close()
    
    return [row[0] for row in result]

def set_status_expired(user_id: int):
    """Устанавливает статус expired"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE users SET subscription_status = ? WHERE user_id = ?',
        ('expired', user_id)
    )
    conn.commit()
    conn.close()
