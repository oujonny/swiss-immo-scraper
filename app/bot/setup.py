from pymongo import MongoClient
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from app.config import Config

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
    context.user_data["min_rooms"] = float(update.message.text)
    HTMLmessage = f"""
Please confirm your settings:
<b>PLZ:</b> {context.user_data["zip"]}
<b>MIN_ROOMS:</b> {context.user_data["min_rooms"]}

Should I start scraping ? (Confirm with 'Yes')
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

        # Store the collected data in MongoDB
        settings_collection.insert_one({
            "chat_id": update.effective_chat.id,
            "zip": zipList,
            "min_rooms": context.user_data["min_rooms"]
        })
        await update.message.reply_text("Settings confirmed and saved.")
    else:
        await update.message.reply_text("Settings not confirmed. Please start over.")
    return ConversationHandler.END

async def setup_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the setup conversation."""
    await update.message.reply_text("Please enter the ZIP code's you are interested in (comma separated list)")
    return MIN_ROOMS

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    await update.message.reply_text("Bye! I hope we can talk again some day.")
    return ConversationHandler.END