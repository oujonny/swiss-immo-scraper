from pymongo import MongoClient
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from app.scrapper import main as scrapper_main
from app.config import Config

async def callback_run_immo_listing(context: ContextTypes.DEFAULT_TYPE):
    config = Config()
    await scrapper_main.main(config, context= context, chat_id=context.job.chat_id)


# Conversation
ZIP, MIN_ROOMS, CONFIRM, CONFIRM_RESPONSE = range(4)

async def zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please enter the ZIP code's you are interested in (comma separated list)")
    return MIN_ROOMS

async def min_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["zip"] = update.message.text
    await update.message.reply_text("Please enter the minimum number of rooms you are interested in (0.5 is supported)")
    return CONFIRM

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["min_rooms"] = str(update.message.text)
    HTMLmessage = f"""
Please confirm your settings:
<b>PLZ:</b> {context.user_data["zip"]}
<b>MIN_ROOMS:</b> {context.user_data["min_rooms"]}

Should I save those settings ? (Confirm with 'Yes')
To start scraping immo listings, type /scrape
"""
    await update.message.reply_text(HTMLmessage, parse_mode="HTML")
    return CONFIRM_RESPONSE

async def confirmation_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "Yes":
        config = Config()
        mongo_uri = f"mongodb://{config.mongo_username}:{config.mongo_password}@{config.mongo_host}:{config.mongo_port}/"

        mongo_client = MongoClient(mongo_uri)
        db = mongo_client.immo_db
        settings_collection = db["settings"]

        zipList: list = context.user_data["zip"].split(",")

        # Store the collected data in MongoDB and overwrite existing settings
        if settings_collection.find_one({"chat_id": update.effective_chat.id}):
            settings_collection.delete_one({"chat_id": update.effective_chat.id})

        settings_collection.insert_one({
            "chat_id": update.effective_chat.id,
            "zip": zipList,
            "min_rooms": context.user_data["min_rooms"]
        })
        await update.message.reply_text("Settings confirmed and saved.")

        chat_id = update.effective_chat.id
        # TODO: seems like the stop never stops... the loop control should be here, not within the function
        context.job_queue.run_repeating(callback_run_immo_listing, interval=config.scraping_interval, first=2, chat_id=chat_id)

    else:
        await update.message.reply_text("Settings not confirmed. Please start over.")
    return ConversationHandler.END

async def setup_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the setup conversation."""
    await update.message.reply_text("Please enter the ZIP code's you are interested in (comma separated list)")
    return MIN_ROOMS

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End the conversation."""
    await update.message.reply_text("Setup cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END