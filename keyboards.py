# -*- coding: utf-8 -*-
# keyboards.py
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

# -------- Main menu (Persian) --------
def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [
                KeyboardButton(text="ثبت نام ✍️"),
                KeyboardButton(text="ورود 📥"),
            ],
            [
                KeyboardButton(text="تتر ➜ لیر"),
                KeyboardButton(text="لیر ➜ تتر"),
                KeyboardButton(text="تومان ➜ لیر"),
            ],
            [
                KeyboardButton(text="لیر ➜ تومان"),
                KeyboardButton(text="تومان ➜ تتر"),
                KeyboardButton(text="تتر ➜ تومان"),
            ],
            [
                KeyboardButton(text="قوانین و مقررات 📜"),
                KeyboardButton(text="سوالات متداول ❓"),
            ],
            [
                KeyboardButton(text="تماس با ما ☎️"),
                KeyboardButton(text="🏠 خانه"),
            ],
        ]
    )

# -------- Contact share for ورود --------
def share_phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[[KeyboardButton(text="📱 ارسال شماره تلفن من", request_contact=True)]]
    )

# -------- Registration navigation (if you still use it) --------
def registration_navigation() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ قبلی", callback_data="nav:prev"),
                InlineKeyboardButton(text="بررسی ✅", callback_data="nav:review"),
                InlineKeyboardButton(text="بعدی ➡️", callback_data="nav:next"),
            ],
            [
                InlineKeyboardButton(text="🏠 خانه", callback_data="jump:1"),
                InlineKeyboardButton(text="🚫 عدم یادآوری", callback_data="cancel_reminders"),
            ],
        ]
    )

