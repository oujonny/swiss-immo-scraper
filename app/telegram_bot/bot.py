import asyncio

from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

from app import setup_custom_logger

logger = setup_custom_logger(__name__)

class TelegramBot:

    def __init__(self, token: str) -> None:
        self.token = token
        self.application = ApplicationBuilder().token(token).build()

    # Commands
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        await context.bot.send_message(chat_id=chat_id, text="I'm a bot, please talk to me!")

        # Save chat_id to use later
        self.chat_id = chat_id

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=self.chat_id, text="HELP I need somebody HELP not just anybody HELP you know I need someone HELP")

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