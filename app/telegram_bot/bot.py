import asyncio
from typing import Dict, Tuple

import aiohttp
import telegram
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from app import setup_custom_logger

from app.telegram_bot.listing_helper import download_images, generate_message
from immo.model import ImmoData

logger = setup_custom_logger(__name__)

class TelegramBot:

    def __init__(self, token: str) -> None:
        self.token = token
        self.application = ApplicationBuilder().token(token).build()

        self.chat_id = None
        self.context = ContextTypes.DEFAULT_TYPE

    # Commands
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id=chat_id, text="I'm a bot, please talk to me!")

        # Save chat_id and context to use later
        self.update = update
        self.context = context
        self.chat_id = chat_id

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=self.chat_id, text="HELP I need somebody HELP not just anybody HELP you know I need someone HELP")


    async def send_listing(self, immo_data: ImmoData, hostname: str, host_url: str, immo_distances: Dict[str, Tuple[str, str]]):
        message_content = await generate_message(immo_data, hostname, host_url, immo_distances)
        message = await self.context.bot.send_message(chat_id=self.chat_id, text=message_content, parse_mode="HTML", disable_web_page_preview=True)

        # Attach Images to message
        if immo_data.images:
            async with aiohttp.ClientSession() as session:
                downloaded_images = await download_images(immo_data.images, session)
                if len(downloaded_images) > 1:
                    for group in [downloaded_images[i:i + 10] for i in range(0, len(downloaded_images), 10)]:
                        await self.context.bot.send_media_group(self.chat_id, group, reply_to_message_id=message.id)
                else:
                    await self.context.bot.edit_message_media(downloaded_images[0], chat_id=self.chat_id, message_id=message.id)
    async def start(self):
        start_handler = CommandHandler("start", self.start_command)
        help_handler = CommandHandler("help", self.help_command)

        self.application.add_handler(start_handler)
        self.application.add_handler(help_handler)

        logger.info("Starting Telegram Bot")
        await self.application.run_polling()


if __name__ == "__main__":
    token = "7479458841:AAELrFH76XPqQw5gNHawZx3Fqrnrwc9Sgak"
    bot = TelegramBot(token)
    asyncio.run(bot.start())