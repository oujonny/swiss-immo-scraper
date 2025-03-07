import asyncio

from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler, \
    Application, JobQueue
from ptbcontrib.ptb_jobstores.mongodb import PTBMongoDBJobStore

from app import setup_custom_logger
from app.bot.listing import *
from app.bot.setup import *

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

async def start_scrape_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = Config()
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="Start sending immo listings")
    context.job_queue.run_repeating(callback_scrape_immo_listing, interval=config.scraping_interval, first=5, chat_id=chat_id, name=f"send_{chat_id}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="HELP I need somebody HELP not just anybody HELP you know I need someone HELP")

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="I will stop scraping immo listings")
    await callback_stop_scrape(context, chat_id)


def setup_bot(application: Application):
    start_handler = CommandHandler("start", start_command)
    help_handler = CommandHandler("help", help_command)
    stop_handler = CommandHandler("stop", stop_command)

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
    start_scrape_handler = CommandHandler("scrape", start_scrape_command)

    config = Config()
    application.job_queue.scheduler.add_jobstore(
        PTBMongoDBJobStore(
            application=application,
            host=f"mongodb://{config.mongo_username}:{config.mongo_password}@{config.mongo_host}:{config.mongo_port}/"
        )
    )

    application.add_handler(start_handler)
    application.add_handler(setup_handler)
    application.add_handler(start_scrape_handler)
    application.add_handler(help_handler)
    application.add_handler(stop_handler)

    job_queue = JobQueue()
    job_queue.set_application(application)

def start(token: str):
    logger.info("Setting up Telegram Bot")
    application = ApplicationBuilder().token(token).build()

    setup_bot(application)
    logger.info("Starting Telegram Bot")
    application.run_polling()


if __name__ == "__main__":
    token = "7479458841:AAELrFH76XPqQw5gNHawZx3Fqrnrwc9Sgak"
    start(token)