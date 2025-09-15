# -*- coding: utf-8 -*-
# handlers/registration.py
import asyncio
import logging
import random
from datetime import datetime

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from states import RegisterState
from keyboards import registration_navigation, share_phone_kb
from utils.form import get_form_structure, render_form
from utils.validators import (
    is_persian_name,
    is_valid_national_id,
    is_valid_card,
    parse_jalali_yyyymmdd,
    normalize_digits,
)
from services.scheduler import schedule_user_reminders, cancel_user_reminders
from services.ehraz import can_try, bump, match_card_national_dob
from services.admin_notify import send_registration_to_admin
from database import upsert_user, set_user_docs

router = Router()
log = logging.getLogger(__name__)

# ---------------- helper texts ----------------
def _ask_text(step: int) -> str:
    prompts = {
        1: "🟡 1/9 لطفاً نام کوچک خود را به فارسی (مطابق شناسنامه) وارد کنید.",
        2: "🟡 2/9 لطفاً نام خانوادگی خود را به فارسی (مطابق شناسنامه) وارد کنید.",
        3: "🟡 3/9 لطفاً شماره تلگرام ایران خود را فقط با دکمه زیر به اشتراک بگذارید.",
        4: "🟡 4/9 لطفاً کد ملی خود را وارد کنید (۱۰ رقم).",
        5: "🟡 5/9 لطفاً تاریخ تولد (شمسی) را وارد کنید. مثال: 1365/06/26 یا 26-06-1365",
        6: "🟡 6/9 لطفاً ۱۶ رقم کارت بانکی به نام خودتان را وارد کنید.",
        7: "🟡 7/9 قوانین و مقررات به صورت خطوط جداگانه ارسال می‌شود؛ در پایان عبارت «می‌پذیرم» را ارسال کنید.",
        8: "🟡 8/9 لطفاً تصویر روی کارت ملی را ارسال کنید.",
        9: "🟡 9/9 لطفاً تصویر پشت کارت ملی را ارسال کنید.",
    }
    return prompts.get(step, "")

RULES_LINES = [
    "1️⃣ کاربران موظفند قبل از ثبت‌نام تمامی مفاد این تعهدنامه را مطالعه کرده و در صورت پذیرش اقدام به ثبت‌نام نمایند.",
    "2️⃣ کلیه فعالیت‌های کاربران تحت قوانین جمهوری اسلامی ایران و ترکیه است.",
    "3️⃣ در اولین تراکنش، صرافی کیانی مجاز است مبلغ را تا 72 ساعت نگه‌داری کند تا از عدم وجود فعالیت مشکوک اطمینان حاصل شود.",
    "4️⃣ احراز هویت برای استفاده از خدمات الزامی است و مسئولیت هرگونه تخلف بر عهده فرد متخلف است.",
    "5️⃣ صرافی کیانی خود را ملزم به حفظ اطلاعات شخصی کاربران می‌داند.",
    "6️⃣ در صورت نیاز به تشخیص مدیریت جهت احراز هویت، تماس تصویری با تیم پشتیبانی انجام می‌شود.",
    "7️⃣ صرافی کیانی متعهد به حفظ دارایی‌های کاربران با استانداردهای امنیتی بالا است.",
    "8️⃣ کاربران موظفند از خدمات صرافی تنها برای خود استفاده نمایند.",
    "9️⃣ در برداشت ارزهای دیجیتال، مسئولیت ارائه آدرس صحیح کیف پول بر عهده کاربر است.",
    "🔟 واریز ریالی به حساب کاربران در اولین سیکل پایا انجام می‌شود؛ در تعطیلات به اولین روز کاری موکول می‌شود.",
    "⛔️ در صورت تشخیص تقلب، صرافی حق گزارش به مراجع قضایی را دارد.",
    "⚠️ کاربران موظفند هویت خود را به درستی تأیید کنند.",
]

def _terms_variants_ok(text: str) -> bool:
    t = normalize_digits((text or "").strip()).replace(" ", "")
    # پشتیبانی از برخی اشکال تایپی/نیم‌فاصله
    return t in {"می‌پذیرم", "میپذیرم", "می‌پذيرم", "میپذيرم", "می پذیرم", "مي‌پذيرم", "ميپذيرم"}

async def _update_form_message(m: types.Message, state: FSMContext, current_step: int):
    """
    Safely render or update the sticky 'form' message.
    Recreates the form if user jumped here without starting the flow.
    """
    data = await state.get_data()
    form = data.get("form")
    if not form:
        form = get_form_structure()
        await state.update_data(form=form, current_step=1, form_msg_id=None)

    text = render_form(form, current_step)
    form_msg_id = (await state.get_data()).get("form_msg_id")

    if not form_msg_id:
        sent = await m.answer(text, reply_markup=registration_navigation())
        await state.update_data(form_msg_id=sent.message_id)
        return

    try:
        await m.bot.edit_message_text(
            text=text,
            chat_id=m.chat.id,
            message_id=form_msg_id,
            reply_markup=registration_navigation(),
        )
    except Exception:
        # message was deleted or cannot edit; send new one
        sent = await m.answer(text, reply_markup=registration_navigation())
        await state.update_data(form_msg_id=sent.message_id)

# ---------------- entry points ----------------
@router.message(F.text == "ثبت نام ✍️")
@router.message(Command("register"))
async def start_registration(message: types.Message, state: FSMContext):
    await state.clear()
    form = get_form_structure()
    await state.update_data(
        form=form,
        current_step=1,
        started_at=datetime.utcnow().isoformat(),
        user_id=message.from_user.id,
        form_msg_id=None,
    )

    # schedule gentle reminders (canceled if user proves non +98 phone)
    try:
        schedule_user_reminders(message.from_user.id)
    except Exception as e:
        log.warning("schedule reminders failed: %s", e)

    await message.answer("📋 لطفاً فرم ثبت‌نام را مرحله‌به‌مرحله تکمیل کنید.")
    await _update_form_message(message, state, current_step=1)
    await message.answer(_ask_text(1))
    await state.set_state(RegisterState.first_name)

# ---------------- navigation ----------------
@router.callback_query(F.data.startswith("jump:"))
async def jump_to_step(cb: types.CallbackQuery, state: FSMContext):
    step = int(cb.data.split(":")[1])
    await state.update_data(current_step=step)
    await _update_form_message(cb.message, state, current_step=step)
    if step == 3:
        await cb.message.answer(_ask_text(step), reply_markup=share_phone_kb())
    else:
        await cb.message.answer(_ask_text(step))
    await cb.answer()

@router.callback_query(F.data == "nav:prev")
async def go_prev(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    step = max(1, int(data.get("current_step", 1)) - 1)
    await state.update_data(current_step=step)
    await _update_form_message(cb.message, state, current_step=step)
    if step == 3:
        await cb.message.answer(_ask_text(step), reply_markup=share_phone_kb())
    else:
        await cb.message.answer(_ask_text(step))
    await cb.answer()

@router.callback_query(F.data == "nav:next")
async def go_next(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    step = min(9, int(data.get("current_step", 1)) + 1)
    await state.update_data(current_step=step)
    await _update_form_message(cb.message, state, current_step=step)
    if step == 3:
        await cb.message.answer(_ask_text(step), reply_markup=share_phone_kb())
    else:
        await cb.message.answer(_ask_text(step))
    await cb.answer()

@router.callback_query(F.data == "nav:review")
async def review(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    step = int(data.get("current_step", 1))
    await _update_form_message(cb.message, state, current_step=step)
    await cb.answer("فرم به‌روز شد ✅")

@router.callback_query(F.data == "cancel_reminders")
async def cancel_rem(cb: types.CallbackQuery):
    cancel_user_reminders(cb.from_user.id)
    await cb.message.answer("✅ یادآوری‌ها لغو شد.")
    await cb.answer()

# ---------------- steps ----------------
@router.message(RegisterState.first_name)
async def step_first_name(m: types.Message, state: FSMContext):
    name = (m.text or "").strip()
    if not is_persian_name(name):
        await m.answer("لطفاً کیبورد را فارسی کنید و نام کوچک را به فارسی وارد کنید.")
        return

    data = await state.get_data()
    form = data["form"]
    form[1]["value"] = name
    await state.update_data(form=form, current_step=2)
    await _update_form_message(m, state, current_step=2)
    await m.answer(_ask_text(2))
    await state.set_state(RegisterState.last_name)

@router.message(RegisterState.last_name)
async def step_last_name(m: types.Message, state: FSMContext):
    name = (m.text or "").strip()
    if not is_persian_name(name):
        await m.answer("لطفاً کیبورد را فارسی کنید و نام خانوادگی را به فارسی وارد کنید.")
        return

    data = await state.get_data()
    form = data["form"]
    form[2]["value"] = name
    await state.update_data(form=form, current_step=3)
    await _update_form_message(m, state, current_step=3)
    await m.answer(_ask_text(3), reply_markup=share_phone_kb())
    await state.set_state(RegisterState.phone_number)

@router.message(RegisterState.phone_number, F.contact)
async def step_phone_ok(m: types.Message, state: FSMContext):
    phone = m.contact.phone_number or ""
    # normalize to +98...
    if phone.startswith("0098"):
        phone = "+" + phone[2:]
    elif phone.startswith("98") and not phone.startswith("+"):
        phone = "+" + phone

    if not phone.startswith("+98"):
        # Not an Iranian number → cancel reminders and abort
        cancel_user_reminders(m.from_user.id)
        await m.answer(
            "فقط با تلگرام با شماره ایران امکان ثبت‌نام وجود دارد.\n"
            "لطفاً با تلگرام ایران‌تان ربات را استارت و ثبت‌نام را دوباره شروع کنید."
        )
        return

    data = await state.get_data()
    form = data["form"]
    form[3]["value"] = phone
    await state.update_data(form=form, current_step=4)
    await _update_form_message(m, state, current_step=4)
    await m.answer(_ask_text(4))
    await state.set_state(RegisterState.national_id)

@router.message(RegisterState.phone_number, ~F.contact)
async def step_phone_wrong(m: types.Message, state: FSMContext):
    await m.answer(
        "لطفاً شماره را دستی ارسال نکنید؛ فقط با دکمه «ارسال شماره تلفن من».",
        reply_markup=share_phone_kb(),
    )

@router.message(RegisterState.national_id)
async def step_nid(m: types.Message, state: FSMContext):
    nid = (m.text or "").strip()
    if not is_valid_national_id(nid):
        await m.answer("کد ملی نامعتبر است. ۱۰ رقم صحیح وارد کنید.")
        return

    data = await state.get_data()
    form = data["form"]
    form[4]["value"] = normalize_digits(nid)
    await state.update_data(form=form, current_step=5)
    await _update_form_message(m, state, current_step=5)
    await m.answer(_ask_text(5))
    await state.set_state(RegisterState.dob)

@router.message(RegisterState.dob)
async def step_dob(m: types.Message, state: FSMContext):
    parsed = parse_jalali_yyyymmdd(m.text or "")
    if not parsed:
        await m.answer("تاریخ نامعتبر است. مثال: 1365/06/26 یا 26-06-1365")
        return

    data = await state.get_data()
    form = data["form"]
    form[5]["value"] = parsed  # store e.g. 13650626
    await state.update_data(form=form, current_step=6)
    await _update_form_message(m, state, current_step=6)
    await m.answer(_ask_text(6))
    await state.set_state(RegisterState.bank_card_number)

@router.message(RegisterState.bank_card_number)
async def step_card(m: types.Message, state: FSMContext):
    card = (m.text or "").strip()
    if not is_valid_card(card):
        await m.answer("شماره کارت نامعتبر است. لطفاً ۱۶ رقم صحیح وارد کنید.")
        return

    uid = m.from_user.id
    # Ehraz API try-limit
    if not can_try(uid):
        await m.answer("تعداد تلاش‌های امروز به حد نصاب رسیده است. لطفاً فردا دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.")
        return
    bump(uid)

    data = await state.get_data()
    form = data["form"]
    nid = form[4]["value"]
    dob = form[5]["value"]
    matched = await match_card_national_dob(normalize_digits(card), nid, dob)

    if not matched:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="اصلاح کد ملی", callback_data="edit:nid"),
                InlineKeyboardButton(text="اصلاح تاریخ تولد", callback_data="edit:dob"),
                InlineKeyboardButton(text="اصلاح کارت بانکی", callback_data="edit:card"),
            ]]
        )
        await m.answer("❌ تطبیق اطلاعات ناموفق بود. لطفاً یکی از موارد زیر را اصلاح کنید.", reply_markup=kb)
        return

    form[6]["value"] = normalize_digits(card)
    await state.update_data(form=form, current_step=7)
    await _update_form_message(m, state, current_step=7)

    # Send rules one-by-one
    for line in RULES_LINES:
        await m.answer(line)
        await asyncio.sleep(0.15)

    await m.answer("اگر موافقید، عبارت «می‌پذیرم» را ارسال کنید.")
    await state.set_state(RegisterState.terms)

@router.callback_query(F.data == "edit:nid")
async def edit_nid(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("کد ملی صحیح را وارد کنید:")
    await state.set_state(RegisterState.national_id)
    await cb.answer()

@router.callback_query(F.data == "edit:dob")
async def edit_dob(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("تاریخ تولد صحیح را وارد کنید (مثال: 1365/06/26):")
    await state.set_state(RegisterState.dob)
    await cb.answer()

@router.callback_query(F.data == "edit:card")
async def edit_card(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("شماره کارت صحیح را وارد کنید (۱۶ رقم):")
    await state.set_state(RegisterState.bank_card_number)
    await cb.answer()

@router.message(RegisterState.terms)
async def step_terms(m: types.Message, state: FSMContext):
    if not _terms_variants_ok(m.text or ""):
        await m.answer("برای ادامه باید عبارت «می‌پذیرم» را ارسال کنید.")
        return

    data = await state.get_data()
    form = data["form"]
    form[7]["value"] = "پذیرفته شد ✅"
    await state.update_data(form=form, current_step=8)
    await _update_form_message(m, state, current_step=8)
    await m.answer(_ask_text(8))
    await state.set_state(RegisterState.front_id)

@router.message(RegisterState.front_id, F.photo)
async def step_front(m: types.Message, state: FSMContext):
    fid = m.photo[-1].file_id
    data = await state.get_data()
    form = data["form"]
    form[8]["value"] = "✅"
    await state.update_data(form=form, current_step=9, front_id=fid)
    await _update_form_message(m, state, current_step=9)
    await m.answer(_ask_text(9))
    await state.set_state(RegisterState.back_id)

@router.message(RegisterState.front_id, ~F.photo)
async def step_front_wrong(m: types.Message):
    await m.answer("لطفاً <b>عکس</b> روی کارت ملی را ارسال کنید.", parse_mode="HTML")

@router.message(RegisterState.back_id, F.photo)
async def step_back(m: types.Message, state: FSMContext):
    bid = m.photo[-1].file_id
    data = await state.get_data()
    if bid == data.get("front_id"):
        await m.answer("تصاویر پشت و روی کارت ملی یکسان است. لطفاً تصویر پشت را مجدد ارسال کنید.")
        return

    form = data["form"]
    form[9]["value"] = "✅"
    await state.update_data(form=form, back_id=bid)
    await _update_form_message(m, state, current_step=9)

    # ----- finalize & persist -----
    uid = m.from_user.id
    ref = str(random.randint(1000, 9999))
    payload = {
        "id": uid,
        "first_name": form[1]["value"],
        "last_name": form[2]["value"],
        "phone_number": form[3]["value"],
        "national_id": form[4]["value"],
        "dob": form[5]["value"],
        "bank_card_number": form[6]["value"],
        "accepted_terms": 1,
        "front_id": data.get("front_id"),
        "back_id": data.get("back_id") or bid,
        "kyc_status": "Pending",
        "reference_code": ref,
        "kyc_notified": 0,
    }

    # Support both upsert_user styles (kwargs or dict)
    try:
        upsert_user(
            uid,
            first_name=payload["first_name"],
            last_name=payload["last_name"],
            phone_number=payload["phone_number"],
            kyc_status=payload["kyc_status"],
            reference_code=payload["reference_code"],
            bank_card_number=payload["bank_card_number"],
            front_id=payload["front_id"],
            back_id=payload["back_id"],
        )
    except TypeError:
        # Newer signature accepts a dict
        upsert_user(payload)

    # Save doc file_ids (if helper exists)
    try:
        set_user_docs(uid, payload["front_id"], payload["back_id"])
    except Exception as e:
        log.warning("set_user_docs failed: %s", e)

    # Notify admin
    try:
        await send_registration_to_admin(uid, payload)
    except Exception as e:
        log.warning("send_registration_to_admin failed: %s", e)

    # Stop reminders after completion
    cancel_user_reminders(uid)

    await m.answer("مدارک شما ارسال شد ✅\nلطفاً منتظر بررسی ادمین باشید.")
    await state.clear()

@router.message(RegisterState.back_id, ~F.photo)
async def step_back_wrong(m: types.Message):
    await m.answer("لطفاً <b>عکس</b> پشت کارت ملی را ارسال کنید.", parse_mode="HTML")

