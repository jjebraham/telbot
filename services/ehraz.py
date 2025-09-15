# services/ehraz.py
import logging
from datetime import datetime
import aiohttp

from config import EHRAZ_TOKEN
from .proxy_manager import get_random_proxy

# In-memory attempts limiter (reset daily)
_attempts = {}  # {user_id: {"date": "YYYYMMDD", "count": int}}


def _today() -> str:
    return datetime.now().strftime("%Y%m%d")


def can_try(user_id: int, limit: int = 5) -> bool:
    """
    True if the user can attempt again today (<= limit per day).
    """
    rec = _attempts.get(user_id)
    if not rec or rec["date"] != _today():
        _attempts[user_id] = {"date": _today(), "count": 0}
        return True
    return rec["count"] < limit


def bump(user_id: int) -> None:
    rec = _attempts.get(user_id, {"date": _today(), "count": 0})
    if rec["date"] != _today():
        rec = {"date": _today(), "count": 0}
    rec["count"] += 1
    _attempts[user_id] = rec


async def match_card_national_dob(
    card_number: str,
    national_id: str,
    birthdate_yyyymmdd: str,
) -> bool:
    """
    Calls Ehraz: POST https://ehraz.io/api/v1/match/card-with-national
    JSON: { cardNumber, nationalCode, birthDate }  (birthDate like '13650626')
    Returns True if matched.
    """
    if not EHRAZ_TOKEN:
        logging.error("EHRAZ_TOKEN is missing; cannot call Ehraz.")
        return False

    url = "https://ehraz.io/api/v1/match/card-with-national"
    headers = {
        # EHRAZ_TOKEN must be the RAW token in .env; we add 'Token ' prefix here:
        "Authorization": f"Token {EHRAZ_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "cardNumber": card_number,
        "nationalCode": national_id,
        "birthDate": birthdate_yyyymmdd,
    }

    proxy = get_random_proxy()
    try:
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers, proxy=proxy) as resp:
                text = await resp.text()
                if resp.status != 200:
                    logging.error("Ehraz non-200 (%s): %s", resp.status, text)
                    return False
                data = await resp.json()
                return bool(data.get("matched"))
    except Exception as e:
        logging.error("Ehraz call failed: %s", e)
        return False

