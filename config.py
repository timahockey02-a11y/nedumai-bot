import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан. Заполни .env по образцу .env.example")
if not DEEPSEEK_API_KEY:
    raise RuntimeError("DEEPSEEK_API_KEY не задан. Заполни .env по образцу .env.example")
