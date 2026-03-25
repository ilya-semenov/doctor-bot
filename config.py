import os
from dotenv import load_dotenv

# Загружаем переменные из файла .env
load_dotenv()

# Сохраняем их в переменные, чтобы использовать в других файлах
BOT_TOKEN = os.getenv('BOT_TOKEN')
AI_API_KEY = os.getenv('AI_API_KEY')
AI_MODEL = os.getenv('AI_MODEL')

# Настройки подписки
SUBSCRIPTION_ENABLED = os.getenv('SUBSCRIPTION_ENABLED', 'False').lower() == 'true'
SUBSCRIPTION_PRICE_STARS = int(os.getenv('SUBSCRIPTION_PRICE_STARS', '100'))
SUBSCRIPTION_DAYS = int(os.getenv('SUBSCRIPTION_DAYS', '30'))

# ЮKassa
YOOKASSA_SHOP_ID = os.getenv('YOOKASSA_SHOP_ID')
YOOKASSA_SECRET_KEY = os.getenv('YOOKASSA_SECRET_KEY')

# ID администраторов (можно несколько, через запятую)
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]