import os
from dotenv import load_dotenv

# Загружаем переменные из файла .env
load_dotenv()

# Сохраняем их в переменные, чтобы использовать в других файлах
BOT_TOKEN = os.getenv('BOT_TOKEN')
AI_API_KEY = os.getenv('AI_API_KEY')
AI_MODEL = os.getenv('AI_MODEL')