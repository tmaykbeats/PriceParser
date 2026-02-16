import os

from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# Проверяем загрузку .env
if not os.path.exists(".env"):
    print("Error: .env file not found")
else:
    print(".env file found")

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("Error: BOT_TOKEN is not set in .env")
else:
    print(
        f"BOT_TOKEN loaded: {BOT_TOKEN[:10]}..."
    )  # Показываем первые 10 символов для безопасности

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
DATABASE_PATH = "prices.db"
SCRAPE_URL = "https://scrapeme.live/shop/"
