import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
NGROK_AUTHTOKEN = os.getenv("NGROK_AUTHTOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "").lstrip("@")
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook/telegram")
SERVER_PUBLIC_URL = os.getenv("SERVER_PUBLIC_URL", f"http://{SERVER_HOST}:{SERVER_PORT}").rstrip("/")

PIN_TTL_SECONDS = 120
PIN_LENGTH = 4
