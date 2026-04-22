"""Run the Telegram bot in polling mode for local development.

Usage: cd api && python -m scripts.run_telegram_bot
"""

import asyncio
import sys
import os

# Add api/ to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.telegram_bot import create_bot_application


def main():
    app = create_bot_application()
    if not app:
        print("TELEGRAM_BOT_TOKEN not set. Add it to api/.env")
        sys.exit(1)

    print("Starting bot in polling mode (Ctrl+C to stop)...")
    print("Send /start to your bot in Telegram to begin.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
