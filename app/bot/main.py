import asyncio

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler, \
    Application

from app import setup_custom_logger
from app.bot.listing import *
from app.bot.setup import *

from app.scrapper.immo.model import ImmoData

telegram_app = None
logger = setup_custom_logger(__name__)

# Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Start response
    message_content = f"""
<b>Welcome to the Swiss Immo Bot!</b>
I can query apartment listing, send them to you and arrange a viewing.

To get started, type <i>/setup</i> and follow the instructions.
"""
    await context.bot.send_message(chat_id=chat_id, text=message_content, parse_mode="HTML")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="HELP I need somebody HELP not just anybody HELP you know I need someone HELP")

#
# SEND LISTING
#
async def send_listing(update: Update, context: ContextTypes.DEFAULT_TYPE, immo_data: ImmoData, hostname: str, host_url: str):
    chat_id = update.effective_chat.id
    message_content = await generate_message(immo_data, hostname, host_url)

    # Attach Images to message
    if immo_data.images:
        async with aiohttp.ClientSession() as session:
            downloaded_images = await prepare_message(immo_data.images, session, message_content)
            if len(downloaded_images) > 1:
                await context.bot.send_media_group(chat_id, downloaded_images)
                # for groups of 10 images
                # for group in list(divide_chunks(downloaded_images, 10)):
                #     # for first group
                #     await context.bot.send_media_group(chat_id, group)
            else:
                await context.bot.send_media(downloaded_images[0], chat_id=chat_id)

def setup_bot(application: Application):
    start_handler = CommandHandler("start", start_command)
    help_handler = CommandHandler("help", help_command)

    setup_handler = ConversationHandler(
        entry_points=[CommandHandler('setup', setup_conv)],
        states={
            ZIP: [MessageHandler(filters.TEXT, zip)],
            MIN_ROOMS: [MessageHandler(filters.TEXT, min_rooms)],
            CONFIRM: [MessageHandler(filters.TEXT, confirm)],
            CONFIRM_RESPONSE: [MessageHandler(filters.TEXT, confirmation_response)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(start_handler)
    application.add_handler(setup_handler)
    application.add_handler(help_handler)

def start(token: str):
    logger.info("Setting up Telegram Bot")
    global telegram_app
    telegram_app = ApplicationBuilder().token(token).build()
    telegram_app = ApplicationBuilder().token(token).build()
    setup_bot(telegram_app)
    logger.info("Starting Telegram Bot")

def start_polling():
    telegram_app.run_polling()


if __name__ == "__main__":
    token = "7479458841:AAELrFH76XPqQw5gNHawZx3Fqrnrwc9Sgak"
    start(token)