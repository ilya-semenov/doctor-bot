import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# API ключ DeepSeek
AI_API_KEY = os.getenv("DEEPSEEK_API_KEY", "YOUR_DEEPSEEK_KEY_HERE")

# Модель DeepSeek
AI_MODEL = os.getenv("AI_MODEL", "deepseek-chat")  # или "deepseek-coder"

# Для отладки
print(f"Конфигурация загружена:")
print(f"BOT_TOKEN: {BOT_TOKEN[:15]}..." if BOT_TOKEN != "YOUR_BOT_TOKEN_HERE" else "BOT_TOKEN не установлен!")
print(f"AI_API_KEY: {AI_API_KEY[:10]}..." if AI_API_KEY != "YOUR_DEEPSEEK_KEY_HERE" else "AI_API_KEY не установлен!")
print(f"AI_MODEL: {AI_MODEL}")
