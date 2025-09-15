# -*- coding: utf-8 -*-
# handlers/menu.py
import logging
import re
from typing import Tuple

from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from keyboards import main_menu_kb, share_phone_kb
from services.price_service import get_usdt_irr, get_usdt_try, round_to_nearest_10
from database import get_user_by_phone  # used for ورود
from states import RegisterState

logger = logging.getLogger(__name__)
router = Router()


# ---------- Helpers ----------
ARROW_RE = re.compile(r"[>\-→➜➡️]+")  # accept multiple arrow styles

def _clean(s: str) -> str:
    return re.sub(r"\s+", "", s or "")

def _parse_pair(text: str) -> Tuple[str, str]:
    """
    Parse menu label like 'تومان ➜ لیر' into ('تومان', 'لیر').
    Returns ('', '') if unmatched.
    """
    if not text:
        return "", ""
    parts = ARROW_RE.split(text)
    if len(parts) != 2:
        return "", ""
    return parts[0].strip(), parts[1].strip()


def _fmt_irr(n: float) -> str:
    try:
        n = round_to_nearest_10(n)
    except Exception:
        pass
    return f"{n:,.0f}"


# ---------- /start + home/back ----------
@router.message(CommandStart())
async def on_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "به صرافی کیانی خوش آمدید 🌟\nاز منو گزینه مورد نظر را انتخاب کنید.",
        reply_markup=main_menu_kb()
    )


@router.message(F.text.in_({"🏠 خانه", "⬅️ بازگشت"}))
async def go_home(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("منوی اصلی:", reply_markup=main_menu_kb())


# Optional: /home command
@router.message(Command("home"))
async def cmd_home(message: types.Message, state: FSMContext):
    await go_home(message, state)


# ---------- ورود ----------
@router.message(F.text == "ورود 📥")
async def ask_contact_for_login(message: types.Message, state: FSMContext):
    # If user is inside registration flow, let that flow handle contacts.
    cur = await state.get_state()
    if cur:
        await message.answer("در حال تکمیل فرم ثبت‌نام هستید. لطفاً مراحل را ادامه دهید.")
        return
    await message.answer(
        "برای ورود، لطفاً با دکمه زیر شماره تلگرام ایران خود را به اشتراک بگذارید:",
        reply_markup=share_phone_kb()
    )


@router.message(F.contact)
async def login_with_contact(message: types.Message, state: FSMContext):
    # If contact is for registration step, don't interfere
    cur = await state.get_state()
    if cur == RegisterState.phone_number.state:
        return  # registration handler will process it

    phone = message.contact.phone_number or ""
    if phone.startswith("0098"):
        phone = "+" + phone[2:]
    elif phone.startswith("98") and not phone.startswith("+"):
        phone = "+" + phone

    if not phone.startswith("+98"):
        await message.answer(
            "فقط شماره ایران (+98) قابل پذیرش است.\n"
            "در صورت نیاز با تلگرام ایران وارد شوید.",
            reply_markup=main_menu_kb()
        )
        return

    try:
        user = await get_user_by_phone(phone)
    except Exception as e:
        logger.exception("DB error in get_user_by_phone: %s", e)
        user = None

    if user:
        await message.answer("✅ ورود موفقیت‌آمیز بود.", reply_markup=main_menu_kb())
    else:
        await message.answer(
            "کاربری با این شماره یافت نشد. لطفاً ابتدا «ثبت نام ✍️» را انجام دهید.",
            reply_markup=main_menu_kb()
        )


# ---------- نرخ‌ها (۶ جهت) ----------
RATE_LABELS = {
    "تومان ➜ لیر",
    "لیر ➜ تومان",
    "تومان ➜ تتر",
    "تتر ➜ تومان",
    "لیر ➜ تتر",
    "تتر ➜ لیر",
}

@router.message(F.text.func(lambda t: isinstance(t, str) and any(k in t for k in ("تومان", "لیر", "تتر"))))
async def handle_rates_text(message: types.Message):
    # Only handle the 6 known combinations; ignore others
    left, right = _parse_pair(message.text)
    L, R = _clean(left), _clean(right)
    if not L or not R or (f"{left} ➜ {right}" not in RATE_LABELS and f"{left}>{right}" not in RATE_LABELS):
        # Not a known pair -> let other handlers try (fallback at bottom will catch)
        return

    # Fetch base quotes (via proxies if configured)
    usdt_irr = await get_usdt_irr()  # تومان per 1 USDT
    usdt_try = await get_usdt_try()  # لیر per 1 USDT

    if not usdt_irr or not usdt_try:
        await message.answer("❌ دریافت نرخ‌ها با خطا مواجه شد. لطفاً دوباره تلاش کنید.", reply_markup=main_menu_kb())
        return

    # Converters
    def irr_to_try(x: float) -> float:  # تومان -> لیر
        return (x / usdt_irr) * usdt_try

    def try_to_irr(x: float) -> float:  # لیر -> تومان
        return (x / usdt_try) * usdt_irr

    def irr_to_usdt(x: float) -> float:  # تومان -> تتر
        return x / usdt_irr

    def usdt_to_irr(x: float) -> float:  # تتر -> تومان
        return x * usdt_irr

    def try_to_usdt(x: float) -> float:  # لیر -> تتر
        return x / usdt_try

    def usdt_to_try(x: float) -> float:  # تتر -> لیر
        return x * usdt_try

    # Compose reply for 1 unit
    if L == "تومان" and R == "لیر":
        val = irr_to_try(1)
        txt = f"۱ تومان ≈ {val:,.6f} لیر"
    elif L == "لیر" and R == "تومان":
        val = try_to_irr(1)
        txt = f"۱ لیر ≈ {_fmt_irr(val)} تومان"
    elif L == "تومان" and R == "تتر":
        val = irr_to_usdt(1)
        txt = f"۱ تومان ≈ {val:,.8f} USDT"
    elif L == "تتر" and R == "تومان":
        val = usdt_to_irr(1)
        txt = f"۱ USDT ≈ {_fmt_irr(val)} تومان"
    elif L == "لیر" and R == "تتر":
        val = try_to_usdt(1)
        txt = f"۱ لیر ≈ {val:,.6f} USDT"
    elif L == "تتر" and R == "لیر":
        val = usdt_to_try(1)
        txt = f"۱ USDT ≈ {val:,.3f} لیر"
    else:
        return

    # Add snapshot of base quotes too
    base = (
        f"نرخ مرجع:\n"
        f"• ۱ USDT ≈ {_fmt_irr(usdt_irr)} تومان\n"
        f"• ۱ USDT ≈ {usdt_try:,.3f} لیر"
    )
    await message.answer(f"{txt}\n\n{base}")


# ---------- FAQ / Rules / Contact ----------
FAQ_QUESTIONS = [
    ("چطور ثبت نام کنم؟",
     "روی دکمه «ثبت نام ✍️» بزنید و نام، نام خانوادگی، کد ملی، تاریخ تولد، شماره تلگرام ایران و شماره کارت بانکی به نام خودتان را وارد کنید."),
    ("کدام شماره تلفن قابل قبول است؟",
     "تنها شماره ایران (+98) قابل قبول است و باید با دکمه «ارسال شماره تلفن من» در تلگرام به اشتراک گذاشته شود."),
    ("چطور کارت جدید ثبت کنم؟",
     "بعد از ورود، از «کارت‌های بانکی من» روی «اضافه کردن کارت جدید» بزنید و ۱۶ رقم کارت بانکی به نام خودتان را وارد کنید."),
    ("واریزهای ریالی چقدر زمان می‌برد؟",
     "واریزها در اولین سیکل پایا انجام می‌شود (۴، ۱۱، ۱۴، ۱۹). در تعطیلات به اولین روز کاری موکول می‌شود."),
    ("خرید تتر چه مدت طول می‌کشد؟",
     "اگر اولین واریز ریالی شما باشد، به دستور پلیس فتا ممکن است تا ۷۲ ساعت نزد ما امانت بماند. از خرید دوم به بعد معمولاً ظرف یک ساعت انجام می‌شود."),
]

RULES = [
    "1️⃣ کاربران موظفند قبل از ثبت‌نام تمامی مفاد را مطالعه و در صورت پذیرش ثبت‌نام کنند.",
    "2️⃣ کلیه فعالیت‌ها تحت قوانین جمهوری اسلامی ایران و ترکیه انجام می‌شود.",
    "3️⃣ در اولین تراکنش ممکن است مبلغ تا ۷۲ ساعت نزد ما امانت بماند.",
    "4️⃣ احراز هویت برای استفاده از خدمات الزامی است.",
    "5️⃣ صرافی کیانی متعهد به حفظ اطلاعات شخصی کاربران است.",
    "6️⃣ واریز/برداشت فقط از/به حساب بانکی به نام خود کاربر مجاز است.",
    "7️⃣ مسئولیت آدرس صحیح کیف پول در برداشت رمزارز با کاربر است.",
]

CONTACT_TEXT = (
    "☎️ تماس با ما:\n"
    "• پشتیبانی تلگرام: @KianiSupport\n"
    "• ایمیل: support@kianiexchange.example\n"
)

@router.message(F.text == "سوالات متداول ❓")
async def faqs(message: types.Message):
    parts = [f"❓ {q}\n{a}" for q, a in FAQ_QUESTIONS]
    await message.answer("\n\n".join(parts))

@router.message(F.text == "قوانین و مقررات 📜")
async def rules(message: types.Message):
    await message.answer("\n".join(RULES))

@router.message(F.text == "تماس با ما ☎️")
async def contact_us(message: types.Message):
    await message.answer(CONTACT_TEXT)


# ---------- Fallback (must be LAST) ----------
ALLOWED_LABELS = {
    "ثبت نام ✍️",
    "ورود ��",
    "تومان ➜ لیر", "لیر ➜ تومان",
    "تومان ➜ تتر", "تتر ➜ تومان",
    "لیر ➜ تتر", "تتر ➜ لیر",
    "سوالات متداول ❓",
    "قوانین و مقررات 📜",
    "تماس با ما ☎️",
    "🏠 خانه", "⬅️ بازگشت",
}

@router.message(F.text & ~F.text.in_(ALLOWED_LABELS))
async def fallback(message: types.Message):
    # Log what text reached fallback to debug future issues
    logger.info("Fallback for text=%r", message.text)
    await message.answer("لطفاً از منو انتخاب کنید.", reply_markup=main_menu_kb())

