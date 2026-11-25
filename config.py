import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "6577841902"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip().lstrip("@")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://YOUR-APP-DOMAIN.example").rstrip("/")
GROUP_USERNAME = os.getenv("GROUP_USERNAME", "@DigitalIncomeZone912")
GROUP_LINK = os.getenv("GROUP_LINK", "https://t.me/DigitalIncomeZone912")
GROUP_JOIN_REWARD = int(os.getenv("GROUP_JOIN_REWARD", "2"))
MIN_WITHDRAW = int(os.getenv("MIN_WITHDRAW", "100"))
DB_PATH = os.getenv("DB_PATH", "arman.db")
CURRENCY_LABEL = os.getenv("CURRENCY_LABEL", "টাকা")
