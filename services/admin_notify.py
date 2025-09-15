# services/admin_notify.py
import logging
from aiogram import Bot
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_BOT_TOKEN, ADMIN_CHAT_ID, MAIN_BOT_TOKEN
from .proxy_manager import get_random_proxy

admin_bot = Bot(token=ADMIN_BOT_TOKEN)
main_bot  = Bot(token=MAIN_BOT_TOKEN)

async def send_registration_to_admin(user_id: int, data: dict):
    """
    data should include: first_name, last_name, phone_number, national_id, dob, bank_card_number,
                         reference_code, front_id (file_id), back_id (file_id)
    """
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{data['reference_code']}"),
        InlineKeyboardButton(text="❌ Reject",  callback_data=f"reject_{data['reference_code']}")
    ]])

    text = (
        f"New Registration:\n"
        f"User: {user_id}\n"
        f"Name: {data.get('first_name','')} {data.get('last_name','')}\n"
        f"Phone: {data.get('phone_number','')}\n"
        f"NID: {data.get('national_id','')}\n"
        f"DOB: {data.get('dob','')}\n"
        f"Card: {data.get('bank_card_number','')}\n"
        f"Ref: {data.get('reference_code','')}"
    )
    await admin_bot.send_message(ADMIN_CHAT_ID, text, reply_markup=kb)

    # photos
    for fld, cap in (("front_id", "Front ID"), ("back_id", "Back ID")):
        fid = data.get(fld)
        if not fid:
            continue
        try:
            file = await main_bot.get_file(fid)
            dl = await main_bot.download_file(file.file_path)
            buff = BufferedInputFile(dl.read(), filename=f"{fld}.jpg")
            await admin_bot.send_photo(ADMIN_CHAT_ID, buff, caption=cap)
        except Exception as e:
            logging.error(f"Admin photo send failed: {e}")
