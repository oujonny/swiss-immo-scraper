import asyncio

import threading

import telegram.ext
from pymongo import MongoClient

from app.scrapper import main as scrapper_main
from app.scrapper.manager import ImmoManager
from bot import main as telegram_bot
from config import Config

def main(config: Config):
    """Start TelegramBot"""
    # Initialize & start the Telegram Bot
    token = config.telegram_bot_token
    telegram_bot.start(token)

    # start scrapper in other threat
    t1 = threading.Thread(target=asyncio.run, args=(scrapper_main.main(config),))
    t1.start()

    telegram_bot.start_polling()





if __name__ == "__main__":
    # Load the ENV Variables into a config instance
    config = Config()

    main(config)