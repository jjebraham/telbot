# config.py
import os
from dotenv import load_dotenv

# Load .env
dotenv_path = "/home/kianirad2020/telbot/.env"
if os.path.exists(dotenv_path):
    print(f"✅ Forcing load of {dotenv_path}")
    load_dotenv(dotenv_path, override=True)
else:
    print(f"❌ .env not found at {dotenv_path}")

# Required tokens
MAIN_BOT_TOKEN  = os.getenv("MAIN_BOT_TOKEN")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
ADMIN_CHAT_ID   = int(os.getenv("ADMIN_CHAT_ID", "2043363119"))

# Ehraz: put ONLY the raw token in .env (no "Token " prefix here)
EHRAZ_TOKEN = os.getenv("EHRAZ_TOKEN", "").strip() or None

# Wallex API key (optional fallback for price)
WALLEX_API_KEY = os.getenv("WALLEX_API_KEY", "").strip() or None

# Database path
DB_PATH = os.getenv("DB_PATH", "users.db")

# Proxy configuration
PROXY_URL       = os.getenv("PROXY_URL", "").strip() or None
PROXY_URLS      = os.getenv("PROXY_URLS", "").strip() or None  # CSV list
PROXY_PATTERN   = os.getenv("PROXY_PATTERN", "").strip() or None
PROXY_POOL_SIZE = int(os.getenv("PROXY_POOL_SIZE", "0"))

print("MAIN_BOT_TOKEN from config.py:", MAIN_BOT_TOKEN)
if not EHRAZ_TOKEN:
    print("⚠️ EHRAZ_TOKEN is not set — Ehraz matching will fail until you add it to .env")
if WALLEX_API_KEY:
    print("🔑 WALLEX_API_KEY is set (will use /markets fallback if needed)")
if PROXY_URL:
    print(f"🌐 Using single proxy: {PROXY_URL}")
elif PROXY_URLS:
    print("🌐 Using proxy pool via PROXY_URLS")
elif PROXY_PATTERN and PROXY_POOL_SIZE:
    print(f"🌐 Using proxy pattern rotation: {PROXY_PATTERN} (size={PROXY_POOL_SIZE})")

