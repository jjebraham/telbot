import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# config.py reads the environment at import time; keep tests offline and
# pointed at a throwaway database.
os.environ.setdefault("DOTENV_PATH", str(ROOT / "tests" / "no.env"))
os.environ.setdefault("MAIN_BOT_TOKEN", "123456:TEST")
os.environ.setdefault("DB_PATH", str(ROOT / "tests" / ".pytest-users.db"))
