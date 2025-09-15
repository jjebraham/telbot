# services/price_service.py
import asyncio
import logging
import time
from typing import Any, Dict, Optional

import aiohttp

from services.proxy_manager import get_proxy
from config import WALLEX_API_KEY  # add WALLEX_API_KEY to your config/.env

log = logging.getLogger(__name__)

# ---------------- Caching ---------------- #
_cache: Dict[str, tuple[float, Optional[float]]] = {}
TTL = 600  # seconds

def _get_cache(key: str) -> Optional[float]:
    ts_val = _cache.get(key)
    if not ts_val:
        return None
    ts, val = ts_val
    if time.time() - ts <= TTL:
        return val
    return None

def _set_cache(key: str, val: Optional[float]) -> None:
    _cache[key] = (time.time(), val)

# --------------- HTTP Core --------------- #
DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=12, sock_connect=8, sock_read=8)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; KianiBot/1.0; +https://t.me/Kianiexchangebot)"
}

async def _get_json(url: str, headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """
    Try up to 5 different proxies from the pool for each request.
    If there is no proxy configured, we still try once (direct).
    """
    tries = 5
    for attempt in range(tries):
        proxy = get_proxy()
        hdrs = {**DEFAULT_HEADERS, **(headers or {})}
        try:
            async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT, trust_env=False) as sess:
                async with sess.get(url, headers=hdrs, proxy=proxy) as resp:
                    if resp.status != 200:
                        txt = await resp.text()
                        log.error("GET %s failed with %s: %s", url, resp.status, (txt[:200] if txt else ""))
                        continue
                    return await resp.json(content_type=None)
        except Exception as e:
            # include which proxy was attempted
            log.error("GET %s via %s failed: %s", url, proxy or "DIRECT", e)
            await asyncio.sleep(0.2)
    return None

# --------------- Parsers ----------------- #
def _parse_nobitex_v3_orderbook(data: Dict[str, Any]) -> Optional[float]:
    """
    https://apiv2.nobitex.ir/v3/orderbook/USDTIRT
    {'status':'ok','bids':[['price','volume',...],...], 'asks':[['price','volume',...],...]}
    We use mid = (best_ask + best_bid)/2  → IRR per USDT
    """
    try:
        if data.get("status") != "ok":
            return None
        bids = data.get("bids") or []
        asks = data.get("asks") or []
        best_bid = float(bids[0][0]) if bids and bids[0] else None
        best_ask = float(asks[0][0]) if asks and asks[0] else None
        if best_bid and best_ask:
            return (best_ask + best_bid) / 2.0
    except Exception:
        return None
    return None

def _parse_bitpin_prices(data: Dict[str, Any]) -> Optional[float]:
    """
    https://api.bitpin.org/v4/mkt/prices/?code=USDT_IRT
    Expect something like:
    {
      "results": {
        "USDT_IRT": {
          "price":"123456.0",
          ...
        }
      }
    }
    """
    try:
        res = data.get("results") or {}
        usdt = res.get("USDT_IRT") or {}
        price = float(usdt.get("price"))
        return price
    except Exception:
        return None

def _parse_wallex_coin_list(data: Dict[str, Any]) -> Optional[float]:
    """
    https://api.wallex.ir/v1/coin-market-list?keys=USDT
    price is usually in 'toman' for some endpoints. OP requested *10 (to Rial).
    Find coin with key 'USDT' and read 'price' field.
    """
    try:
        result = data.get("result") or {}
        coins = result.get("coins") or []
        for c in coins:
            if (c.get("key") or "").upper() == "USDT":
                price_tmn = float(c.get("price"))
                return price_tmn * 10.0
    except Exception:
        return None
    return None

def _parse_wallex_markets_usdttmn(data: Dict[str, Any]) -> Optional[float]:
    """
    https://api.wallex.ir/v1/markets  (requires X-API-KEY)
    result.symbols.USDTTMN.stats.lastPrice  (Toman) → *10 to Rial
    """
    try:
        result = data.get("result") or {}
        symbols = result.get("symbols") or {}
        usdttmn = symbols.get("USDTTMN") or {}
        stats = usdttmn.get("stats") or {}
        last_tmn = float(stats.get("lastPrice"))
        return last_tmn * 10.0
    except Exception:
        return None

# --------------- Public API --------------- #
async def get_usdt_irr() -> Optional[float]:
    """
    IRR per USDT (Rial).
    Order:
    1) Nobitex v3 orderbook (mid)
    2) Bitpin prices
    3) Wallex coin-market-list?keys=USDT  (*10)
    4) Wallex /markets (USDTTMN, needs API key)  (*10)
    """
    cached = _get_cache("USDT_IRR")
    if cached:
        return cached

    # 1) Nobitex
    try:
        d = await _get_json("https://apiv2.nobitex.ir/v3/orderbook/USDTIRT")
        price = _parse_nobitex_v3_orderbook(d or {})
        if price:
            _set_cache("USDT_IRR", price)
            return price
    except Exception as e:
        log.error("get_usdt_irr nobitex error: %s", e)

    # 2) Bitpin
    try:
        d = await _get_json("https://api.bitpin.org/v4/mkt/prices/?code=USDT_IRT")
        price = _parse_bitpin_prices(d or {})
        if price:
            _set_cache("USDT_IRR", price)
            return price
    except Exception as e:
        log.error("get_usdt_irr bitpin error: %s", e)

    # 3) Wallex coin list (public)
    try:
        d = await _get_json("https://api.wallex.ir/v1/coin-market-list?keys=USDT")
        price = _parse_wallex_coin_list(d or {})
        if price:
            _set_cache("USDT_IRR", price)
            return price
    except Exception as e:
        log.error("get_usdt_irr wallex-coinlist error: %s", e)

    # 4) Wallex markets (API key fallback)
    if WALLEX_API_KEY:
        try:
            d = await _get_json(
                "https://api.wallex.ir/v1/markets",
                headers={"X-API-KEY": WALLEX_API_KEY},
            )
            price = _parse_wallex_markets_usdttmn(d or {})
            if price:
                _set_cache("USDT_IRR", price)
                return price
        except Exception as e:
            log.error("get_usdt_irr wallex-markets error: %s", e)

    _set_cache("USDT_IRR", None)
    return None


async def get_usdt_try() -> Optional[float]:
    """
    TRY per USDT.
    Primary: BTCTurk public ticker
    Fallbacks can be added similarly if needed.
    """
    cached = _get_cache("USDT_TRY")
    if cached:
        return cached

    # BTCTurk
    try:
        d = await _get_json("https://api.btcturk.com/api/v2/ticker?pairSymbol=USDTTRY")
        arr = (d or {}).get("data") or []
        if arr:
            lastp = float(arr[0].get("last"))
            _set_cache("USDT_TRY", lastp)
            return lastp
    except Exception as e:
        log.error("get_usdt_try btcturk error: %s", e)

    _set_cache("USDT_TRY", None)
    return None


def round_to_nearest_10(x: float) -> int:
    return int(round(x / 10.0) * 10)


__all__ = [
    "get_usdt_irr",
    "get_usdt_try",
    "round_to_nearest_10",
]

