import os
from dotenv import load_dotenv
from pytz import timezone

load_dotenv()

TOKEN = os.getenv('BOT_TOKEN')
USER_ID = os.getenv('USER_ID')
TZ = os.getenv('TZ', 'Europe/Moscow')
TIMEZONE = timezone(TZ)

if not TOKEN or not USER_ID:
    raise RuntimeError("Не заданы обязательные переменные окружения BOT_TOKEN или USER_ID")