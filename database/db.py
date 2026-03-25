import sqlite3
import logging
from datetime import datetime, timedelta
from config import DATABASE_PATH

# Настройка логирования
logging.basicConfig(level=logging.INFO)

def get_db_connection():
    """Получение соединения с БД"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализация базы данных"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                subscription_end DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица платежей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                currency TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                payment_id TEXT UNIQUE,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица логов админа
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_user_id INTEGER,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logging.info("Database initialized successfully")
        
    except Exception as e:
        logging.error(f"Error initializing database: {e}")
        raise

def get_or_create_user(user_id, username=None, first_name=None, last_name=None):
    """Получение или создание пользователя"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Проверяем существование пользователя
        user = cursor.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        
        if not user:
            # Создаем нового пользователя
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name))
            conn.commit()
            
            # Получаем созданного пользователя
            user = cursor.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            logging.info(f"New user created: {user_id}")
        
        conn.close()
        return dict(user)
        
    except Exception as e:
        logging.error(f"Error in get_or_create_user: {e}")
        raise

def set_subscription(user_id, days, amount=None, payment_id=None):
    """Установка подписки пользователю"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Получаем текущую подписку
        current = cursor.execute(
            "SELECT subscription_end FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        
        if current and current['subscription_end']:
            current_end = datetime.strptime(current['subscription_end'], '%Y-%m-%d')
            if current_end > datetime.now():
                new_end = current_end + timedelta(days=days)
            else:
                new_end = datetime.now() + timedelta(days=days)
        else:
            new_end = datetime.now() + timedelta(days=days)
        
        # Обновляем подписку
        cursor.execute('''
            UPDATE users 
            SET subscription_end = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (new_end.strftime('%Y-%m-%d'), user_id))
        
        conn.commit()
        conn.close()
        
        logging.info(f"Subscription updated for user {user_id}: +{days} days")
        return new_end
        
    except Exception as e:
        logging.error(f"Error in set_subscription: {e}")
        raise

def get_subscription(user_id):
    """Получение информации о подписке"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        user = cursor.execute(
            "SELECT subscription_end FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        
        conn.close()
        
        if user and user['subscription_end']:
            end_date = datetime.strptime(user['subscription_end'], '%Y-%m-%d')
            active = end_date > datetime.now()
            return {'active': active, 'end_date': end_date}
        
        return {'active': False, 'end_date': None}
        
    except Exception as e:
        logging.error(f"Error in get_subscription: {e}")
        return {'active': False, 'end_date': None}

def save_payment(user_id, amount, currency, payment_method, payment_id):
    """Сохранение информации о платеже"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO payments (user_id, amount, currency, payment_method, payment_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, amount, currency, payment_method, payment_id))
        
        conn.commit()
        conn.close()
        
        logging.info(f"Payment saved: user={user_id}, amount={amount}, id={payment_id}")
        
    except Exception as e:
        logging.error(f"Error in save_payment: {e}")
        raise

def add_admin_log(admin_id, action, target_user_id=None, details=None):
    """Добавление лога админа"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO admin_logs (admin_id, action, target_user_id, details)
            VALUES (?, ?, ?, ?)
        ''', (admin_id, action, target_user_id, details))
        
        conn.commit()
        conn.close()
        
        logging.info(f"Admin log: {admin_id} - {action}")
        
    except Exception as e:
        logging.error(f"Error in add_admin_log: {e}")
