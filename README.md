# Telegram Bot Project

A comprehensive Telegram bot for user registration, KYC verification, and financial services.

## Features

- User registration and authentication
- KYC (Know Your Customer) verification with ID card uploads
- Bank card management
- Currency exchange rates (USDT, TRY, IRR)
- Payment processing for external websites
- Admin notifications and logging
- Multi-language support (Persian/Farsi)

## Project Structure

```
├── bot.py                 # Main bot entry point
├── config.py             # Configuration settings
├── database.py           # Database operations
├── keyboards.py          # Telegram keyboard layouts
├── states.py             # FSM states for user interactions
├── handlers/             # Message and callback handlers
│   ├── menu.py          # Menu navigation handlers
│   └── registration.py  # User registration handlers
├── services/            # Business logic services
│   ├── admin_notify.py  # Admin notification service
│   ├── ehraz.py         # ID verification service
│   ├── idle_guard.py    # User session management
│   ├── price_service.py # Currency price fetching
│   ├── proxy_manager.py # Proxy management
│   └── scheduler.py     # Background task scheduler
└── utils/               # Utility functions
    ├── form.py          # Form handling utilities
    └── validators.py    # Input validation functions
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment variables in `.env`:
   ```
   BOT_TOKEN=your_bot_token
   ADMIN_BOT_TOKEN=your_admin_bot_token
   ADMIN_CHAT_ID=your_admin_chat_id
   ```

3. Run the bot:
   ```bash
   python bot.py
   ```

## Dependencies

- aiogram - Telegram Bot API framework
- aiohttp - HTTP client/server
- sqlite3 - Database
- asyncio - Asynchronous programming

## License

This project is private and proprietary.