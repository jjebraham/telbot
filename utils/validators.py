# utils/validators.py
import re

_PERSIAN_RE = re.compile(r"^[\u0600-\u06FF\u200c\s]+$")  # Persian letters + ZWNJ + space

def normalize_digits(s: str) -> str:
    mapping = {
        '۰': '0','۱': '1','۲': '2','۳': '3','۴': '4','۵': '5','۶': '6','۷': '7','۸': '8','۹': '9',
        '٠': '0','١': '1','٢': '2','٣': '3','٤': '4','٥': '5','٦': '6','٧': '7','٨': '8','٩': '9',
    }
    return "".join(mapping.get(c, c) for c in s)

def is_persian_name(s: str) -> bool:
    s = s.strip()
    return len(s) >= 2 and bool(_PERSIAN_RE.match(s))

def is_valid_national_id(nid: str) -> bool:
    nid = normalize_digits(nid).strip()
    if not re.fullmatch(r"\d{10}", nid):
        return False
    if len(set(nid)) == 1:
        return False
    # checksum
    check = int(nid[-1])
    s = sum(int(nid[i]) * (10 - i) for i in range(9)) % 11
    return (s < 2 and check == s) or (s >= 2 and check == 11 - s)

def is_valid_card(card: str) -> bool:
    card = re.sub(r"\s+", "", normalize_digits(card))
    if not re.fullmatch(r"\d{16}", card):
        return False
    # Luhn
    digits = [int(c) for c in card]
    s = 0
    for i, d in enumerate(digits):
        if i % 2 == 0:
            d2 = d * 2
            if d2 > 9: d2 -= 9
            s += d2
        else:
            s += d
    return s % 10 == 0

def parse_jalali_yyyymmdd(input_text: str) -> str | None:
    """
    Accepts: 1365 06 26, 26/06/1365, 1365-06-26, Persian/Arabic digits, dots, underscores etc.
    Returns: '13650626' or None
    """
    t = normalize_digits(input_text)
    parts = re.split(r"[^0-9]+", t)
    parts = [p for p in parts if p]
    if len(parts) == 1 and len(parts[0]) == 8:  # already yyyymmdd
        y, m, d = parts[0][:4], parts[0][4:6], parts[0][6:]
    elif len(parts) == 3:
        # detect which is year
        if len(parts[0]) == 4:
            y, m, d = parts[0], parts[1].zfill(2), parts[2].zfill(2)
        elif len(parts[2]) == 4:
            y, m, d = parts[2], parts[1].zfill(2), parts[0].zfill(2)
        else:
            return None
    else:
        return None

    if not (y.startswith(("13","14")) and 1 <= int(m) <= 12 and 1 <= int(d) <= 31):
        return None
    return f"{y}{m}{d}"
