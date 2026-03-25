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
    
    # Таблица платежей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            currency TEXT,
            payment_method TEXT,
            payment_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Таблица для админ-логов
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
    print("✅ База данных инициализирована")

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
            return {
                'active': False,
                'end_date': end_date,
                'status': 'expired',
                'days_left': 0
            }
    
    return {'active': False, 'end_date': None, 'status': 'inactive', 'days_left': 0}

def set_subscription(user_id: int, days: int, amount: int = None, payment_id: str = None) -> datetime:
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
            INSERT INTO payments (user_id, amount, currency, payment_method, payment_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, amount, 'XTR', 'telegram_stars', payment_id))
    
    conn.commit()
    conn.close()
    return new_end

def save_payment(user_id: int, amount: int, currency: str, payment_method: str, payment_id: str):
    """Сохраняет информацию о платеже"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO payments (user_id, amount, currency, payment_method, payment_id)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, amount, currency, payment_method, payment_id))
    conn.commit()
    conn.close()

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
    
    cursor.execute('''
        SELECT 
            COUNT(*) as total_count,
            SUM(amount) as total_amount,
            COUNT(DISTINCT user_id) as unique_users
        FROM payments
        WHERE created_at >= ?
    ''', (since,))
    
    total_stats = cursor.fetchone()
    
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
    
    if search.isdigit():
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (int(search),))
    else:
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

# Функции для рассылки
def get_all_users_for_mailing(only_subscribers: bool = False, only_donors: bool = False) -> List[int]:
    """Получает список пользователей для рассылки"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if only_subscribers:
        cursor.execute('''
            SELECT user_id FROM users 
            WHERE subscription_status = 'active' 
            AND subscription_end > datetime('now')
        ''')
    elif only_donors:
        cursor.execute('''
            SELECT user_id FROM users 
            WHERE total_donations > 0
        ''')
    else:
        cursor.execute('SELECT user_id FROM users')
    
    rows = cursor.fetchall()
    conn.close()
    
    return [row[0] for row in rows]

def get_users_count() -> Dict:
    """Получает статистику по пользователям"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    total = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM users 
        WHERE subscription_status = 'active' 
        AND subscription_end > datetime('now')
    ''')
    subscribers = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE total_donations > 0')
    donors = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total': total,
        'subscribers': subscribers,
        'donors': donors
    }

def save_mailing_log(admin_id: int, recipient_count: int, message_text: str, target_group: str):
    """Сохраняет лог рассылки"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO admin_logs (admin_id, action, details)
        VALUES (?, ?, ?)
    ''', (admin_id, 'mailing', f'Group: {target_group}, Recipients: {recipient_count}, Message: {message_text[:100]}'))
    
    conn.commit()
    conn.close()

def get_expiring_subscriptions(days: int = 3) -> List[tuple]:
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
    
    rows = cursor.fetchall()
    conn.close()
    
    return [(row[0], datetime.fromisoformat(row[1])) for row in rows]

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

def get_expired_subscriptions() -> List[int]:
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
    
    rows = cursor.fetchall()
    conn.close()
    
    return [row[0] for row in rows]

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
